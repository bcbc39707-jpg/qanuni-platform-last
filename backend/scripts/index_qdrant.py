# -*- coding: utf-8 -*-
"""
Index legal articles from PostgreSQL into Qdrant for semantic search.

Usage:
    python scripts/index_qdrant.py

This script:
    1. Recreates (or clears) the Qdrant collection
    2. Loads all articles from PostgreSQL (with their law titles)
    3. Generates embeddings via Ollama or OpenAI
    4. Upserts points into Qdrant in batches

Prerequisites:
    - Qdrant running (Docker or local)
    - Ollama with nomic-embed-text OR OpenAI API key
    - PostgreSQL populated with legal articles
"""

import os
import sys
import uuid
import asyncio
import httpx
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.legal_article import LegalArticle
from app.models.law import Law
from app.core.config import settings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

MAX_CONCURRENT_EMBEDDINGS = 15
semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDINGS)


def clean_text_for_embedding(text: str) -> str:
    """Light cleanup for embedding input (keep article numbers intact)."""
    if not text:
        return ""
    text = text.replace('ـ', '')
    text = text.replace('\u00a0', ' ').replace('\u200b', '').replace('\u200c', '')
    text = text.replace('\u200d', '').replace('\ufeff', '')
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    return text


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to break at a sentence boundary
        if end < len(text):
            # Look for the last period, newline, or space within the last 100 chars
            search_start = max(start, end - 100)
            break_point = max(
                text.rfind('.', search_start, end),
                text.rfind('\n', search_start, end),
                text.rfind(' ', search_start, end)
            )
            if break_point > search_start:
                end = break_point + 1
        chunks.append(text[start:end].strip())
        start += max(1, end - start - overlap)
    return chunks


async def recreate_qdrant_collection(qdrant_client: AsyncQdrantClient):
    print("🗑️  Skipping Qdrant collection recreation (using existing collection)...", flush=True)
    # Collection already exists from curl, just proceed


async def get_embedding(text: str, http_client: httpx.AsyncClient) -> list[float]:
    truncated = text[:1500]

    if settings.AI_PROVIDER == "ollama":
        ollama_base = settings.OLLAMA_BASE_URL.rstrip("/")
        input_text = truncated
        if "nomic" in settings.OLLAMA_EMBEDDING_MODEL:
            input_text = f"search_document: {truncated}"

        resp = await http_client.post(
            f"{ollama_base}/api/embed",
            json={"model": settings.OLLAMA_EMBEDDING_MODEL, "input": input_text},
            timeout=180.0
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"][0]
    else:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        resp = await http_client.post(
            "https://api.openai.com/v1/embeddings",
            json={"model": settings.OPENAI_EMBEDDING_MODEL, "input": truncated},
            headers=headers,
            timeout=60.0
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def get_embedding_with_semaphore(text: str, http_client: httpx.AsyncClient) -> list[float]:
    async with semaphore:
        for attempt in range(3):
            try:
                return await get_embedding(text, http_client)
            except Exception as e:
                if attempt == 2:
                    raise e
                await asyncio.sleep(1.0)


async def index_articles():
    qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    await recreate_qdrant_collection(qdrant)

    print("📖 Fetching articles from PostgreSQL...", flush=True)
    async with AsyncSessionLocal() as db:
        stmt = select(
            LegalArticle.id,
            LegalArticle.article_number,
            LegalArticle.title,
            LegalArticle.content,
            LegalArticle.keywords,
            LegalArticle.legal_topics,
            Law.id.label("law_id"),
            Law.title.label("law_title")
        ).join(Law, LegalArticle.law_id == Law.id)
        result = await db.execute(stmt)
        rows = result.all()

    total_articles = len(rows)
    print(f"✅  Loaded {total_articles} articles from Postgres.", flush=True)

    if total_articles == 0:
        print("No articles to index. Exiting.")
        return

    # Process in batches
    batch_size = 100
    total_points = 0
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=10)

    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0), limits=limits) as http:
        for idx in range(0, total_articles, batch_size):
            batch = rows[idx:idx + batch_size]
            tasks = []

            for row in batch:
                art_id, art_num, art_title, art_content, keywords, legal_topics, law_id, law_title = row
                content = art_content or ""
                if not content.strip():
                    continue

                # Build embedding text
                embedding_text = clean_text_for_embedding(
                    f"من {law_title}، المادة {art_num}:\n{content}"
                )

                # Chunk content if too long
                chunks = chunk_text(content)
                for c_idx, chunk in enumerate(chunks):
                    display_text = f"من {law_title} (المادة {art_num}):\n{chunk}"

                    async def process(
                        c=chunk, dt=display_text, et=embedding_text,
                        a_id=art_id, a_num=art_num, a_title=art_title,
                        l_id=law_id, l_title=law_title, ci=c_idx
                    ):
                        try:
                            # For multi-chunk articles, use chunk-specific embedding text
                            if len(chunks) > 1:
                                et = clean_text_for_embedding(
                                    f"من {law_title}، المادة {art_num}، جزء {ci + 1}:\n{chunk}"
                                )
                            vec = await get_embedding_with_semaphore(et, http)
                            point_id = str(uuid.uuid4())
                            return PointStruct(
                                id=point_id,
                                vector=vec,
                                payload={
                                    "article_id": a_id,
                                    "doc_id": l_id,
                                    "title": l_title,
                                    "article_number": a_num,
                                    "article_title": a_title or "",
                                    "chunk_index": ci,
                                    "text": dt,
                                    "keywords": keywords or "",
                                    "legal_topics": legal_topics or "",
                                    "type": "law"
                                }
                            )
                        except Exception as e:
                            print(f"   ❌ Error embedding article {a_num} of {l_title}: {e}", flush=True)
                            return None

                    tasks.append(process())

            results = await asyncio.gather(*tasks)
            valid_points = [r for r in results if r is not None]

            if valid_points:
                await qdrant.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=valid_points
                )
                total_points += len(valid_points)

            progress = min(idx + batch_size, total_articles)
            print(f"⚡  Progress: {progress}/{total_articles} articles ({total_points} total chunks)", flush=True)

    await qdrant.close()
    print(f"\n🎉 Qdrant Indexing Complete! Total points: {total_points}")


if __name__ == "__main__":
    asyncio.run(index_articles())
