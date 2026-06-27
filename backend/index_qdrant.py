import asyncio
import os
import sys
import uuid
import httpx
from typing import List, Dict

# Fix sys.path to resolve app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.law import Law
from app.models.legal_article import LegalArticle
from sqlalchemy import select
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Concurrency limit for embedding requests
MAX_CONCURRENT_EMBEDDINGS = 15
semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDINGS)

async def recreate_qdrant_collection(qdrant_client: AsyncQdrantClient):
    print("🗑️ Re-creating Qdrant collection to clear old vectors...", flush=True)
    try:
        await qdrant_client.delete_collection(settings.QDRANT_COLLECTION)
    except Exception:
        pass
        
    dim = 768 if settings.AI_PROVIDER == "ollama" else 3072
    await qdrant_client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
    )
    print(f"✅ Created clean Qdrant collection: {settings.QDRANT_COLLECTION} (dim={dim})", flush=True)

async def get_embedding(text: str, http_client: httpx.AsyncClient) -> list[float]:
    # Truncate text to avoid 400 Bad Request on Ollama or OpenAI for extremely long inputs
    truncated_text = text[:1500]
    
    if settings.AI_PROVIDER == "ollama":
        ollama_base = settings.OLLAMA_BASE_URL.rstrip("/")
        # If using nomic-embed-text, prefix with search_document:
        input_text = truncated_text
        if "nomic" in settings.OLLAMA_EMBEDDING_MODEL:
            input_text = f"search_document: {truncated_text}"
            
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
            json={"model": settings.OPENAI_EMBEDDING_MODEL, "input": truncated_text},
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

async def chunk_text(text: str, max_chars=1000, overlap=200) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start += (max_chars - overlap)
    return chunks

async def index_articles():
    qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    await recreate_qdrant_collection(qdrant)

    print("📖 Fetching articles from PostgreSQL...", flush=True)
    async with AsyncSessionLocal() as db:
        # Load only necessary columns to avoid loading massive full_text columns of Law into memory
        stmt = select(
            LegalArticle.article_number,
            LegalArticle.content,
            Law.id,
            Law.title
        ).join(Law, LegalArticle.law_id == Law.id)
        result = await db.execute(stmt)
        articles_and_laws = result.all()

    total_articles = len(articles_and_laws)
    print(f"✅ Loaded {total_articles} articles from Postgres.", flush=True)
    
    if total_articles == 0:
        print("No articles to index. Exiting.")
        return

    # Ingest in batches to manage memory and network
    batch_size = 100
    points_to_upsert = []
    
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=10)
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0), limits=limits) as http:
        for idx in range(0, total_articles, batch_size):
            batch = articles_and_laws[idx:idx+batch_size]
            tasks = []
            
            for art_num, art_content, law_id, law_title in batch:
                content = art_content or ""
                # Chunk content
                chunks = await chunk_text(content)
                for c_idx, chunk in enumerate(chunks):
                    # For Qdrant format
                    title = f"من {law_title} (المادة {art_num}):\n{chunk}"
                    
                    async def process(c=chunk, t=title, a_num=art_num, l_id=law_id, l_title=law_title, ci=c_idx):
                        try:
                            vec = await get_embedding_with_semaphore(t, http)
                            point_id = str(uuid.uuid4())
                            return PointStruct(
                                id=point_id,
                                vector=vec,
                                payload={
                                    "doc_id": l_id,
                                    "title": l_title,
                                    "chunk_index": ci,
                                    "text": t,
                                    "article_number": a_num
                                }
                            )
                        except Exception as e:
                            print(f"❌ Error embedding article {a_num} of {l_title}: {e}", flush=True)
                            return None
                    
                    tasks.append(process())
            
            results = await asyncio.gather(*tasks)
            valid_points = [r for r in results if r is not None]
            
            if valid_points:
                await qdrant.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=valid_points
                )
                
            progress = min(idx + batch_size, total_articles)
            print(f"⚡ Indexed progress: {progress}/{total_articles} articles ({len(valid_points)} chunks)", flush=True)

    await qdrant.close()
    print("🎉 Qdrant Indexing Complete!")

if __name__ == "__main__":
    asyncio.run(index_articles())

