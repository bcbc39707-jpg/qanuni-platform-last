# -*- coding: utf-8 -*-
"""
Import structured legal JSON files (DOCX-converted) into PostgreSQL.

Reads JSON from: legal_data_json/
Inserts into: laws, legal_parts, legal_chapters, legal_articles, legal_divisions, legal_tree_nodes

Usage (inside backend container or local venv):
    python scripts/import_legal_json_to_postgres.py

Prerequisites:
    - PostgreSQL running (localhost or Docker)
    - DATABASE_URL env set or .env loaded
    - Alembic tables already created
"""

import os
import sys
import json
import uuid
import re
import asyncio
from pathlib import Path
from datetime import datetime

# Fix sys.path to resolve 'app' modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text, func, delete
from app.db.session import AsyncSessionLocal, engine
from app.models.law import Law
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
from app.models.legal_division import LegalDivision
from app.models.legal_tree_node import LegalTreeNode

# ─── Paths ───────────────────────────────────────────────────────────
# JSON_DIR: adjust for Docker vs local
if os.path.exists("/app/legal_data_json"):
    JSON_DIR = Path("/app/legal_data_json")
else:
    JSON_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "legal_data_json"

INDEX_PATH = JSON_DIR / "index.json"

# ─── Arabic Helpers ──────────────────────────────────────────────────

ARABIC_TO_WESTERN = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
}


def normalize_arabic_numbers(text: str) -> str:
    """Convert Arabic-Indic / Persian digits to Western digits."""
    if not text:
        return ""
    return "".join(ARABIC_TO_WESTERN.get(ch, ch) for ch in text)


def clean_text(text: str) -> str:
    """Clean Arabic legal text: remove kashida, zero-width chars, normalize spaces."""
    if not text:
        return ""
    text = text.replace('ـ', '')
    text = text.replace('\u00a0', ' ').replace('\u200b', '').replace('\u200c', '')
    text = text.replace('\u200d', '').replace('\u200e', '').replace('\u200f', '')
    text = text.replace('\ufeff', '').replace('\u2028', '\n').replace('\u2029', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def extract_year(year_str: str) -> int | None:
    """Extract 4-digit year from Arabic/Western string."""
    if not year_str:
        return None
    year_str = normalize_arabic_numbers(year_str)
    # Try to find 4-digit year
    match = re.search(r'\b(1\d{3}|20\d{2})\b', year_str)
    if match:
        y = int(match.group(1))
        if 1900 <= y <= 2100:
            return y
    return None


def make_slug(title: str) -> str:
    """Generate a URL-friendly slug from Arabic title."""
    slug = title.strip()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^\w\u0600-\u06FF-]', '', slug)
    return slug[:200]


# ─── Database Helpers ────────────────────────────────────────────────

async def clear_legal_data(db):
    """Delete existing legal data (keep users, payments, etc.)."""
    print("🗑️  Clearing existing legal data...", flush=True)
    await db.execute(text("DELETE FROM legal_articles"))
    await db.execute(text("DELETE FROM legal_chapters"))
    await db.execute(text("DELETE FROM legal_parts"))
    await db.execute(text("DELETE FROM legal_tree_nodes WHERE ref_table = 'laws' OR node_type = 'category'"))
    await db.execute(text("DELETE FROM legal_divisions"))
    await db.execute(text("DELETE FROM laws"))
    await db.commit()
    print("✅  Cleared old legal data.", flush=True)


async def build_classifications(db, classifications_map: dict):
    """
    Build LegalDivisions and LegalTreeNodes from the 13 source classifications.
    Returns: {classification_name: division_id}
    """
    print("\n🏗️  Building legal classifications tree...", flush=True)
    result = {}

    # 1. Create root node
    root_node = LegalTreeNode(
        id=str(uuid.uuid4()),
        name="الجمهورية اليمنية",
        slug="yemen-republic",
        description="الشجرة القانونية للجمهورية اليمنية",
        node_type="root",
        level=0,
        sort_order=0,
        icon="🇾🇪",
        color="level-0",
        is_active=True
    )
    db.add(root_node)
    await db.flush()

    # 2. Create LegalDivisions + LegalTreeNodes for each classification
    for idx, (cls_name, count) in enumerate(sorted(classifications_map.items(), key=lambda x: -x[1]), 1):
        # LegalDivision
        div = LegalDivision(
            id=str(uuid.uuid4()),
            name=cls_name,
            slug=make_slug(cls_name),
            description=f"التصنيف: {cls_name} — يحتوي على {count} قانون/وثيقة",
            level=1,
            sort_order=idx,
            icon="📁",
            color="tag-law",
            is_active=True
        )
        db.add(div)
        await db.flush()
        result[cls_name] = div.id

        # LegalTreeNode (category node under root)
        cat_node = LegalTreeNode(
            id=str(uuid.uuid4()),
            parent_id=root_node.id,
            name=cls_name,
            slug=make_slug(cls_name),
            description=f"التصنيف: {cls_name} — {count} وثيقة",
            node_type="category",
            level=1,
            sort_order=idx,
            icon="📁",
            color="level-1",
            is_active=True
        )
        db.add(cat_node)
        await db.flush()

    await db.commit()
    print(f"✅  Created {len(result)} classifications.", flush=True)
    return result


async def link_law_to_tree(db, law: Law, division_id: str, tree_nodes_map: dict):
    """Create a LegalTreeNode leaf for this law under its category."""
    # Find the category node for this law's classification
    category_node = tree_nodes_map.get(law.category)
    if not category_node:
        return

    leaf = LegalTreeNode(
        id=str(uuid.uuid4()),
        parent_id=category_node.id,
        name=law.title,
        slug=make_slug(law.title),
        description=f"{law.title} — رقم {law.law_number or '—'} لسنة {law.year or '—'}",
        node_type="law",
        level=2,
        sort_order=0,
        icon="📜",
        color="level-2",
        ref_table="laws",
        ref_id=law.id,
        is_active=True
    )
    db.add(leaf)
    await db.flush()

    # Also set the law's division_id
    law.division_id = division_id
    await db.flush()


# ─── Import Logic ────────────────────────────────────────────────────

async def import_single_law(db, json_path: Path, division_map: dict, tree_nodes_map: dict, law_idx: int):
    """Import one JSON file into the DB."""
    law_name = json_path.stem.replace("_", " ")
    print(f"\n📜 [{law_idx}] {law_name}", flush=True)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    title = clean_text(metadata.get("title", law_name))
    classification = metadata.get("classification", "")
    law_number = normalize_arabic_numbers(metadata.get("number", "")).strip()
    if len(law_number) > 100:
        law_number = law_number[:100]
    year = extract_year(metadata.get("year", ""))
    source_url = metadata.get("source_url", "")
    preamble = clean_text(metadata.get("preamble", ""))

    # Build full_text from preamble + articles
    full_text_parts = [preamble] if preamble else []

    # Create Law
    law = Law(
        id=str(uuid.uuid4()),
        title=title,
        law_number=law_number if law_number else None,
        year=year,
        category=classification if classification else "قانون",
        full_text="\n\n".join(full_text_parts),
        is_active=True,
        slug=make_slug(title),
        description=f"نص {title} الصادر في الجمهورية اليمنية"
    )
    db.add(law)
    await db.flush()

    # Maps for structural linking
    parts_map: dict[str, str] = {}      # part_number -> part_id
    chapters_map: dict[str, str] = {}    # chapter_number -> chapter_id
    # We don't map divisions/subdivisions as separate entities in DB

    part_sort = 0
    chapter_sort = 0
    total_articles = 0

    # ── Import Parts ──
    for part_data in data.get("parts", []):
        part_sort += 1
        part_num = str(part_data.get("number", part_sort))
        part_title = clean_text(part_data.get("title", f"الكتاب {part_num}"))

        part = LegalPart(
            id=str(uuid.uuid4()),
            law_id=law.id,
            part_number=part_num,
            title=part_title,
            sort_order=part_sort
        )
        db.add(part)
        await db.flush()
        parts_map[part_num] = part.id
        print(f"   📂 Part {part_sort}: {part_title[:60]}", flush=True)

        # ── Chapters under this part ──
        for ch_data in part_data.get("chapters", []):
            chapter_sort += 1
            ch_num = str(ch_data.get("number", chapter_sort))
            ch_title = clean_text(ch_data.get("title", f"الباب {ch_num}"))

            chapter = LegalChapter(
                id=str(uuid.uuid4()),
                part_id=part.id,
                law_id=law.id,
                chapter_number=ch_num,
                title=ch_title,
                sort_order=chapter_sort
            )
            db.add(chapter)
            await db.flush()
            chapters_map[ch_num] = chapter.id
            print(f"      📖 Chapter {chapter_sort}: {ch_title[:60]}", flush=True)

    # ── Orphan Chapters (not under any part) ──
    # These might appear in data["articles"] or in some edge cases
    # Actually, our JSON structure doesn't have orphan chapters outside parts.
    # But we handle articles directly under law if no parts exist.

    # ── Import Articles (flat_articles) ──
    article_sort = 0
    for art in data.get("flat_articles", []):
        article_sort += 1
        total_articles += 1

        art_num = str(art.get("number", ""))
        art_title = clean_text(art.get("title", ""))
        art_content = clean_text(art.get("content", ""))
        part_num = art.get("part_number")
        ch_num = art.get("chapter_number")
        div_num = art.get("division_number")
        sub_num = art.get("subdivision_number")

        # Resolve part_id
        part_id = parts_map.get(str(part_num)) if part_num is not None else None

        # Resolve chapter_id
        chapter_id = None
        if ch_num is not None:
            chapter_id = chapters_map.get(str(ch_num))
        elif div_num is not None and str(div_num) in chapters_map:
            chapter_id = chapters_map.get(str(div_num))
        elif sub_num is not None and str(sub_num) in chapters_map:
            chapter_id = chapters_map.get(str(sub_num))

        # If still not found, we might create orphan chapters on the fly
        # from subdivisions if we had mapped them. For now, we leave chapter_id=None.

        # Append article content to full_text for full-text search
        if art_content:
            full_text_parts.append(f"مادة ({art_num}):\n{art_content}")

        article = LegalArticle(
            id=str(uuid.uuid4()),
            law_id=law.id,
            part_id=part_id,
            chapter_id=chapter_id,
            article_number=art_num,
            title=art_title if art_title else None,
            content=art_content,
            is_active=True,
            sort_order=article_sort
        )
        db.add(article)

    # Update law metadata
    law.total_articles_count = total_articles
    if full_text_parts:
        law.full_text = "\n\n".join(full_text_parts)
    await db.flush()

    # Link to tree
    division_id = division_map.get(classification)
    if division_id:
        await link_law_to_tree(db, law, division_id, tree_nodes_map)

    print(f"   ✅ Imported {total_articles} articles for '{title}'", flush=True)
    return total_articles


# ─── Main ────────────────────────────────────────────────────────────

async def main():
    print("=" * 70, flush=True)
    print("🏛️  Yemeni Legal JSON → PostgreSQL Import", flush=True)
    print("=" * 70, flush=True)

    if not JSON_DIR.exists():
        print(f"❌ JSON directory not found: {JSON_DIR}", flush=True)
        return

    # Load index for classification counts
    index_data = {"laws": []}
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index_data = json.load(f)

    # Build classification histogram
    classifications = {}
    for law_meta in index_data.get("laws", []):
        cls = law_meta.get("classification", "")
        if cls:
            classifications[cls] = classifications.get(cls, 0) + 1

    # Gather JSON files (skip index and 00_الفهرس_الشامل)
    json_files = sorted([
        p for p in JSON_DIR.glob("*.json")
        if p.name not in ("index.json", "00_الفهرس_الشامل.json")
    ])
    print(f"📁 Found {len(json_files)} JSON files to import.", flush=True)

    async with AsyncSessionLocal() as db:
        # Step 1: Clear old data
        await clear_legal_data(db)

        # Step 2: Build classifications tree
        division_map = await build_classifications(db, classifications)

        # Fetch tree nodes for linking
        nodes_result = await db.execute(select(LegalTreeNode))
        tree_nodes = {n.name: n for n in nodes_result.scalars().all()}

        # Step 3: Import each law
        grand_total = 0
        for idx, json_path in enumerate(json_files, 1):
            try:
                count = await import_single_law(db, json_path, division_map, tree_nodes, idx)
                grand_total += count
            except Exception as e:
                print(f"   ❌ Error processing {json_path.stem}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                continue

        # Step 4: Final commit
        await db.commit()

        # Step 5: Summary stats
        laws_count = (await db.execute(select(func.count()).select_from(Law))).scalar()
        parts_count = (await db.execute(select(func.count()).select_from(LegalPart))).scalar()
        ch_count = (await db.execute(select(func.count()).select_from(LegalChapter))).scalar()
        art_count = (await db.execute(select(func.count()).select_from(LegalArticle))).scalar()
        div_count = (await db.execute(select(func.count()).select_from(LegalDivision))).scalar()
        tree_count = (await db.execute(select(func.count()).select_from(LegalTreeNode))).scalar()

        print(f"\n{'='*70}", flush=True)
        print(f"🎉 Import Complete!", flush=True)
        print(f"   📜 Laws:      {laws_count}", flush=True)
        print(f"   📂 Parts:     {parts_count}", flush=True)
        print(f"   📖 Chapters:  {ch_count}", flush=True)
        print(f"   📄 Articles:  {art_count}", flush=True)
        print(f"   🏷️ Divisions: {div_count}", flush=True)
        print(f"   🌳 TreeNodes: {tree_count}", flush=True)
        print(f"{'='*70}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
