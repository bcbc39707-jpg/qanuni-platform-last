# -*- coding: utf-8 -*-
"""
Full Pipeline: Import legal JSON → PostgreSQL → Qdrant indexing.

This is the master script that orchestrates the entire data ingestion pipeline.

Usage (inside backend container or local venv):
    python scripts/full_pipeline.py

Steps:
    1. Import all JSON files from legal_data_json/ into PostgreSQL
    2. Rebuild PostgreSQL GIN full-text search indexes
    3. Index all articles into Qdrant for semantic search
    4. Print summary statistics

Prerequisites:
    - PostgreSQL running and accessible via DATABASE_URL
    - Qdrant running and accessible via QDRANT_URL
    - Ollama or OpenAI configured for embeddings
"""

import os
import sys
import asyncio
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, func, select
from app.db.session import AsyncSessionLocal
from app.models.law import Law
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
from app.models.legal_division import LegalDivision
from app.models.legal_tree_node import LegalTreeNode

# Import our pipeline modules
import import_legal_json_to_postgres as importer
import index_qdrant as qdrant_indexer


async def rebuild_gin_indexes(db):
    """Rebuild PostgreSQL GIN full-text search indexes."""
    print("\n🔧 Rebuilding PostgreSQL GIN indexes...", flush=True)
    indexes = [
        ("idx_laws_full_text_tsv", "laws", "to_tsvector('arabic', COALESCE(full_text, ''))"),
        ("idx_laws_title_tsv", "laws", "to_tsvector('arabic', COALESCE(title, ''))"),
        ("idx_articles_content_tsv", "legal_articles", "to_tsvector('arabic', COALESCE(content, ''))"),
    ]
    for idx_name, table, expr in indexes:
        try:
            await db.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} USING GIN ({expr})"))
            await db.execute(text(f"REINDEX INDEX {idx_name}"))
            print(f"   ✅ {idx_name}", flush=True)
        except Exception as e:
            print(f"   ⚠️  {idx_name}: {e}", flush=True)
    await db.commit()
    print("✅  GIN indexes rebuilt.", flush=True)


async def verify_integrity(db):
    """Cross-check counts and orphan records."""
    print("\n🔍 Verifying database integrity...", flush=True)

    laws_count = (await db.execute(select(func.count()).select_from(Law))).scalar()
    parts_count = (await db.execute(select(func.count()).select_from(LegalPart))).scalar()
    ch_count = (await db.execute(select(func.count()).select_from(LegalChapter))).scalar()
    art_count = (await db.execute(select(func.count()).select_from(LegalArticle))).scalar()
    div_count = (await db.execute(select(func.count()).select_from(LegalDivision))).scalar()
    tree_count = (await db.execute(select(func.count()).select_from(LegalTreeNode))).scalar()

    # Orphan checks
    orphan_articles = (await db.execute(
        select(func.count()).select_from(LegalArticle).where(
            LegalArticle.law_id.notin_(select(Law.id))
        )
    )).scalar()

    orphan_chapters = (await db.execute(
        select(func.count()).select_from(LegalChapter).where(
            LegalChapter.law_id.notin_(select(Law.id))
        )
    )).scalar()

    laws_without_articles = (await db.execute(
        select(func.count()).select_from(Law).where(Law.total_articles_count == 0)
    )).scalar()

    print(f"   📜 Laws:            {laws_count}", flush=True)
    print(f"   📂 Parts:           {parts_count}", flush=True)
    print(f"   📖 Chapters:        {ch_count}", flush=True)
    print(f"   📄 Articles:        {art_count}", flush=True)
    print(f"   🏷️ Divisions:       {div_count}", flush=True)
    print(f"   🌳 TreeNodes:       {tree_count}", flush=True)
    print(f"   ⚠️ Orphan articles: {orphan_articles}", flush=True)
    print(f"   ⚠️ Orphan chapters: {orphan_chapters}", flush=True)
    print(f"   ⚠️ Laws w/o articles: {laws_without_articles}", flush=True)

    if orphan_articles > 0 or orphan_chapters > 0:
        print("   ❌ WARNING: Found orphan records!", flush=True)
    else:
        print("   ✅ No orphan records found.", flush=True)

    return {
        "laws": laws_count,
        "parts": parts_count,
        "chapters": ch_count,
        "articles": art_count,
        "divisions": div_count,
        "tree_nodes": tree_count,
        "orphan_articles": orphan_articles,
        "orphan_chapters": orphan_chapters,
        "laws_without_articles": laws_without_articles,
    }


async def main():
    print("=" * 70, flush=True)
    print("🏛️  FULL PIPELINE: JSON → PostgreSQL → Qdrant", flush=True)
    print("=" * 70, flush=True)

    # ─── Step 1: PostgreSQL Import ───
    try:
        print("\n📥 STEP 1/3: Importing JSON into PostgreSQL...", flush=True)
        await importer.main()
    except Exception as e:
        print(f"\n❌ STEP 1 FAILED: {e}", flush=True)
        traceback.print_exc()
        return

    # ─── Step 2: Rebuild GIN Indexes ───
    try:
        async with AsyncSessionLocal() as db:
            await rebuild_gin_indexes(db)
            stats = await verify_integrity(db)
    except Exception as e:
        print(f"\n❌ STEP 2 FAILED: {e}", flush=True)
        traceback.print_exc()
        return

    # ─── Step 3: Qdrant Indexing ───
    try:
        print("\n📥 STEP 3/3: Indexing articles into Qdrant...", flush=True)
        await qdrant_indexer.index_articles()
    except Exception as e:
        print(f"\n❌ STEP 3 FAILED: {e}", flush=True)
        traceback.print_exc()
        return

    # ─── Summary ───
    print("\n" + "=" * 70, flush=True)
    print("🎉 FULL PIPELINE COMPLETE!", flush=True)
    print(f"   📜 Laws:      {stats['laws']}", flush=True)
    print(f"   📂 Parts:     {stats['parts']}", flush=True)
    print(f"   📖 Chapters:  {stats['chapters']}", flush=True)
    print(f"   📄 Articles:  {stats['articles']}", flush=True)
    print(f"   🏷️ Divisions: {stats['divisions']}", flush=True)
    print(f"   🌳 TreeNodes: {stats['tree_nodes']}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
