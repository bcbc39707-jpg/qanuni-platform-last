"""
Import structured legal hierarchy (Parts → Chapters → Articles) from cleaned JSON files
into the PostgreSQL database tables: legal_parts, legal_chapters, legal_articles.

Also updates the Law record with total_articles_count, slug, and description.

Run inside the backend container:
    python import_structured_laws.py
"""
import os
import sys
import json
import uuid
import re
import asyncio
from pathlib import Path

# Fix sys.path to resolve app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, delete, text, func
from app.db.session import AsyncSessionLocal, engine
from app.models.law import Law
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
from app.models.legal_division import LegalDivision
from app.models.legal_tree_node import LegalTreeNode

EXTRACTED_JSON_DIR = Path("/app/legal_data/extracted_json/laws")


def make_slug(title: str) -> str:
    """Generate a URL-friendly slug from Arabic title."""
    slug = title.strip()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^\w\u0600-\u06FF-]', '', slug)
    return slug[:200]


def extract_article_sort_key(art_num_str: str) -> int:
    """Extract a numeric sort key from an article number string."""
    match = re.search(r'(\d+)', str(art_num_str))
    return int(match.group(1)) if match else 0


async def clear_structured_data(db):
    """Clear all existing structured data (articles, chapters, parts) to allow re-import."""
    print("🗑️ Clearing existing structured data (articles → chapters → parts)...", flush=True)
    await db.execute(text("DELETE FROM legal_articles"))
    await db.execute(text("DELETE FROM legal_chapters"))
    await db.execute(text("DELETE FROM legal_parts"))
    await db.commit()
    print("✅ Cleared all structured data.", flush=True)


async def import_single_law(db, json_path: Path, law_index: int):
    """Import structured hierarchy for a single law JSON file."""
    law_name = json_path.stem.replace("_", " ")
    print(f"\n{'='*60}", flush=True)
    print(f"📜 [{law_index}] Processing: {law_name}", flush=True)
    print(f"{'='*60}", flush=True)

    with open(json_path, "r", encoding="utf-8") as f:
        doc_data = json.load(f)

    doc_info = doc_data.get("document", doc_data)
    title = doc_info.get("title", law_name)
    
    # Find corresponding Law record in database
    stmt = select(Law).where(Law.title == title)
    result = await db.execute(stmt)
    law = result.scalar_one_or_none()

    if not law:
        # Try fuzzy match
        stmt2 = select(Law).where(Law.title.like(f"%{title[:30]}%"))
        result2 = await db.execute(stmt2)
        law = result2.scalars().first()

    if not law:
        print(f"⚠️ Law '{title}' not found in database. Creating new Law record...", flush=True)
        law_number = doc_info.get("law_number")
        year = None
        try:
            if doc_info.get("issue_date"):
                year = int(doc_info["issue_date"])
        except (ValueError, TypeError):
            pass

        law = Law(
            id=str(uuid.uuid4()),
            title=title,
            law_number=law_number,
            year=year,
            category=doc_info.get("document_type", "قانون"),
            is_active=True,
            slug=make_slug(title),
        )
        db.add(law)
        await db.flush()
        print(f"   ✅ Created new Law: '{title}' (ID: {law.id})", flush=True)

    law_id = law.id

    # Update law metadata
    law.slug = make_slug(title)
    law.description = doc_info.get("description") or f"نص {title} الصادر في الجمهورية اليمنية"

    # Get JSON chapters
    chapters = doc_info.get("chapters", [])
    if not chapters:
        print(f"   ⚠️ No chapters found in JSON for '{title}'. Skipping structural import.", flush=True)
        return 0

    total_articles = 0
    global_article_sort = 0

    # Detect structure: some laws have "باب" (books/parts) wrapping chapters
    # Check if chapter titles contain "الباب" or "الكتاب" patterns
    has_parts = False
    part_pattern = re.compile(r'^(الكتاب|الباب)\s+')
    for ch in chapters:
        ch_title = ch.get("chapter_title", "")
        if part_pattern.match(ch_title):
            has_parts = True
            break

    if has_parts:
        # Laws with "books" or "parts" (الكتاب/الباب) as top-level, chapters as sub-level
        current_part = None
        part_sort = 0
        chapter_sort = 0

        for ch_idx, ch in enumerate(chapters):
            ch_title = ch.get("chapter_title", f"الفصل {ch.get('chapter_number', ch_idx + 1)}")
            ch_number = ch.get("chapter_number", str(ch_idx + 1))
            sections = ch.get("sections", [])

            if part_pattern.match(ch_title):
                # This is a Part (الكتاب/الباب)
                part_sort += 1
                chapter_sort = 0
                current_part = LegalPart(
                    id=str(uuid.uuid4()),
                    law_id=law_id,
                    part_number=ch_number,
                    title=ch_title,
                    description=None,
                    sort_order=part_sort
                )
                db.add(current_part)
                await db.flush()
                print(f"   📂 Part {part_sort}: {ch_title}", flush=True)

                # Import sections as chapters under this part
                for sec_idx, sec in enumerate(sections):
                    chapter_sort += 1
                    sec_title = sec.get("section_title", f"الفصل {sec.get('section_number', sec_idx + 1)}")
                    sec_number = sec.get("section_number", str(sec_idx + 1))

                    chapter = LegalChapter(
                        id=str(uuid.uuid4()),
                        part_id=current_part.id,
                        law_id=law_id,
                        chapter_number=sec_number,
                        title=sec_title,
                        description=None,
                        sort_order=chapter_sort
                    )
                    db.add(chapter)
                    await db.flush()
                    print(f"      📖 Chapter {chapter_sort}: {sec_title}", flush=True)

                    # Import articles
                    for art in sec.get("articles", []):
                        global_article_sort += 1
                        total_articles += 1
                        article = LegalArticle(
                            id=str(uuid.uuid4()),
                            law_id=law_id,
                            part_id=current_part.id,
                            chapter_id=chapter.id,
                            article_number=str(art.get("article_number", "")),
                            title=art.get("article_title"),
                            content=art.get("article_text", ""),
                            summary=art.get("summary"),
                            keywords=json.dumps(art.get("keywords", []), ensure_ascii=False) if art.get("keywords") else None,
                            legal_topics=json.dumps(art.get("legal_topics", []), ensure_ascii=False) if art.get("legal_topics") else None,
                            is_active=True,
                            sort_order=global_article_sort
                        )
                        db.add(article)

                # Also handle articles directly under the part (no section)
                for art in ch.get("articles", []):
                    global_article_sort += 1
                    total_articles += 1
                    article = LegalArticle(
                        id=str(uuid.uuid4()),
                        law_id=law_id,
                        part_id=current_part.id,
                        chapter_id=None,
                        article_number=str(art.get("article_number", "")),
                        title=art.get("article_title"),
                        content=art.get("article_text", ""),
                        summary=art.get("summary"),
                        keywords=json.dumps(art.get("keywords", []), ensure_ascii=False) if art.get("keywords") else None,
                        legal_topics=json.dumps(art.get("legal_topics", []), ensure_ascii=False) if art.get("legal_topics") else None,
                        is_active=True,
                        sort_order=global_article_sort
                    )
                    db.add(article)
            else:
                # This is a regular chapter under the current part
                chapter_sort += 1
                chapter = LegalChapter(
                    id=str(uuid.uuid4()),
                    part_id=current_part.id if current_part else None,
                    law_id=law_id,
                    chapter_number=ch_number,
                    title=ch_title,
                    description=None,
                    sort_order=chapter_sort
                )
                db.add(chapter)
                await db.flush()
                print(f"      📖 Chapter {chapter_sort}: {ch_title}", flush=True)

                # Import sections' articles
                for sec in sections:
                    for art in sec.get("articles", []):
                        global_article_sort += 1
                        total_articles += 1
                        article = LegalArticle(
                            id=str(uuid.uuid4()),
                            law_id=law_id,
                            part_id=current_part.id if current_part else None,
                            chapter_id=chapter.id,
                            article_number=str(art.get("article_number", "")),
                            title=art.get("article_title"),
                            content=art.get("article_text", ""),
                            summary=art.get("summary"),
                            keywords=json.dumps(art.get("keywords", []), ensure_ascii=False) if art.get("keywords") else None,
                            legal_topics=json.dumps(art.get("legal_topics", []), ensure_ascii=False) if art.get("legal_topics") else None,
                            is_active=True,
                            sort_order=global_article_sort
                        )
                        db.add(article)

                # Articles directly in the chapter
                for art in ch.get("articles", []):
                    global_article_sort += 1
                    total_articles += 1
                    article = LegalArticle(
                        id=str(uuid.uuid4()),
                        law_id=law_id,
                        part_id=current_part.id if current_part else None,
                        chapter_id=chapter.id,
                        article_number=str(art.get("article_number", "")),
                        title=art.get("article_title"),
                        content=art.get("article_text", ""),
                        summary=art.get("summary"),
                        keywords=json.dumps(art.get("keywords", []), ensure_ascii=False) if art.get("keywords") else None,
                        legal_topics=json.dumps(art.get("legal_topics", []), ensure_ascii=False) if art.get("legal_topics") else None,
                        is_active=True,
                        sort_order=global_article_sort
                    )
                    db.add(article)

    else:
        # Flat structure: chapters → sections → articles (no parts/books)
        for ch_idx, ch in enumerate(chapters):
            ch_title = ch.get("chapter_title", f"الفصل {ch.get('chapter_number', ch_idx + 1)}")
            ch_number = ch.get("chapter_number", str(ch_idx + 1))
            sections = ch.get("sections", [])

            chapter = LegalChapter(
                id=str(uuid.uuid4()),
                part_id=None,
                law_id=law_id,
                chapter_number=ch_number,
                title=ch_title,
                description=None,
                sort_order=ch_idx + 1
            )
            db.add(chapter)
            await db.flush()
            print(f"   📖 Chapter {ch_idx + 1}: {ch_title}", flush=True)

            # Import sections' articles
            for sec in sections:
                for art in sec.get("articles", []):
                    global_article_sort += 1
                    total_articles += 1
                    article = LegalArticle(
                        id=str(uuid.uuid4()),
                        law_id=law_id,
                        part_id=None,
                        chapter_id=chapter.id,
                        article_number=str(art.get("article_number", "")),
                        title=art.get("article_title"),
                        content=art.get("article_text", ""),
                        summary=art.get("summary"),
                        keywords=json.dumps(art.get("keywords", []), ensure_ascii=False) if art.get("keywords") else None,
                        legal_topics=json.dumps(art.get("legal_topics", []), ensure_ascii=False) if art.get("legal_topics") else None,
                        is_active=True,
                        sort_order=global_article_sort
                    )
                    db.add(article)

            # Articles directly in the chapter (no sections)
            for art in ch.get("articles", []):
                global_article_sort += 1
                total_articles += 1
                article = LegalArticle(
                    id=str(uuid.uuid4()),
                    law_id=law_id,
                    part_id=None,
                    chapter_id=chapter.id,
                    article_number=str(art.get("article_number", "")),
                    title=art.get("article_title"),
                    content=art.get("article_text", ""),
                    summary=art.get("summary"),
                    keywords=json.dumps(art.get("keywords", []), ensure_ascii=False) if art.get("keywords") else None,
                    legal_topics=json.dumps(art.get("legal_topics", []), ensure_ascii=False) if art.get("legal_topics") else None,
                    is_active=True,
                    sort_order=global_article_sort
                )
                db.add(article)

    # Update law's total article count
    law.total_articles_count = total_articles
    await db.flush()

    print(f"   ✅ Imported {total_articles} articles for '{title}'", flush=True)
    return total_articles


async def link_laws_to_divisions(db):
    """Link laws to their correct legal_divisions based on legal_tree_nodes."""
    print("\n🔗 Linking laws to divisions via legal_tree_nodes...", flush=True)
    
    # Get all laws
    laws_result = await db.execute(select(Law))
    laws = laws_result.scalars().all()
    
    # Get all tree nodes
    nodes_result = await db.execute(select(LegalTreeNode))
    all_nodes = nodes_result.scalars().all()
    nodes_map = {n.id: n for n in all_nodes}
    
    linked = 0
    for law in laws:
        # Find tree node that references this law
        node = next((n for n in all_nodes if n.ref_id == law.id and n.ref_table == "laws"), None)
        
        if node and not law.division_id:
            # Walk up to find the level-1 ancestor (division)
            current = node
            while current and current.parent_id:
                parent = nodes_map.get(current.parent_id)
                if parent and parent.level == 1:
                    law.division_id = parent.id
                    linked += 1
                    print(f"   ✅ Linked '{law.title}' → Division '{parent.name}'", flush=True)
                    break
                current = parent
    
    await db.flush()
    print(f"🔗 Linked {linked} laws to divisions.", flush=True)


async def main():
    print("=" * 70, flush=True)
    print("🏛️  Structured Law Import — Parts, Chapters, Articles", flush=True)
    print("=" * 70, flush=True)

    json_files = sorted(list(EXTRACTED_JSON_DIR.glob("*.json")))
    print(f"📁 Found {len(json_files)} JSON files to process.", flush=True)

    if not json_files:
        print("❌ No JSON files found. Check the path.", flush=True)
        return

    async with AsyncSessionLocal() as db:
        # Step 1: Clear existing structured data
        await clear_structured_data(db)

        # Step 2: Import each law's structured hierarchy
        grand_total = 0
        for idx, json_path in enumerate(json_files, 1):
            try:
                count = await import_single_law(db, json_path, idx)
                grand_total += count
            except Exception as e:
                print(f"   ❌ Error processing {json_path.stem}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                continue

        # Step 3: Commit all changes
        await db.commit()
        
        # Step 4: Link laws to divisions
        await link_laws_to_divisions(db)
        await db.commit()

        # Step 5: Print summary
        parts_count = (await db.execute(select(func.count()).select_from(LegalPart))).scalar()
        chapters_count = (await db.execute(select(func.count()).select_from(LegalChapter))).scalar()
        articles_count = (await db.execute(select(func.count()).select_from(LegalArticle))).scalar()

        print(f"\n{'='*70}", flush=True)
        print(f"🎉 Import Complete!", flush=True)
        print(f"   📂 Parts:     {parts_count}", flush=True)
        print(f"   📖 Chapters:  {chapters_count}", flush=True)
        print(f"   📄 Articles:  {articles_count}", flush=True)
        print(f"   📊 Total:     {grand_total} articles across {len(json_files)} laws", flush=True)
        print(f"{'='*70}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
