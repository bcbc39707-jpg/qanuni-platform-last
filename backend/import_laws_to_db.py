import os
import json
import uuid
import httpx
import asyncio
from pathlib import Path
# Fix sys.path to resolve app modules
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from sqlalchemy import select, delete
from app.models.law import Law
from app.models.legal_part import LegalPart
from app.models.legal_chapter import LegalChapter
from app.models.legal_article import LegalArticle
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

LEGAL_DATA_DIR = Path("/app/legal_data")
EXTRACTED_JSON_DIR = LEGAL_DATA_DIR / "extracted_json" / "laws"
CHUNKS_DIR = LEGAL_DATA_DIR / "chunks"

# Concurrency limit for embedding requests
MAX_CONCURRENT_EMBEDDINGS = 15
semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDINGS)

async def check_or_create_qdrant_collection(qdrant_client: AsyncQdrantClient):
    collections = await qdrant_client.get_collections()
    exists = any(c.name == settings.QDRANT_COLLECTION for c in collections.collections)
    
    # Determine embedding dimension
    dim = 768 if settings.AI_PROVIDER == "ollama" else 3072
    
    if not exists:
        await qdrant_client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
        )
        print(f"Created Qdrant collection: {settings.QDRANT_COLLECTION} with dimension {dim}", flush=True)
    else:
        print(f"Qdrant collection: {settings.QDRANT_COLLECTION} already exists (dimension {dim})", flush=True)

async def get_embedding(text: str, http_client: httpx.AsyncClient) -> list[float]:
    # Truncate to avoid 400 Bad Request for extremely long texts
    truncated_text = text[:1500]
    
    if settings.AI_PROVIDER == "ollama":
        ollama_base = settings.OLLAMA_BASE_URL.rstrip("/")
        resp = await http_client.post(
            f"{ollama_base}/api/embed",
            json={"model": settings.OLLAMA_EMBEDDING_MODEL, "input": truncated_text},
            timeout=180.0
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embeddings"][0]
    else:
        # OpenAI or other API provider fallback
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
        return await get_embedding(text, http_client)

async def import_laws():
    qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
    await check_or_create_qdrant_collection(qdrant)

    json_files = sorted(list(EXTRACTED_JSON_DIR.glob("*.json")))
    print(f"Found {len(json_files)} extracted law JSON files.", flush=True)

    async with AsyncSessionLocal() as db:
        async with httpx.AsyncClient() as http:
            for json_path in json_files:
                law_name = json_path.stem.replace("_", " ")
                print(f"\nProcessing {law_name}...", flush=True)

                # 1. Load document JSON
                with open(json_path, "r", encoding="utf-8") as f:
                    doc_data = json.load(f)

                doc_info = doc_data["document"]
                doc_id = doc_info["document_id"]
                title = doc_info["title"]
                law_number = doc_info.get("law_number")
                year = None
                try:
                    if doc_info.get("issue_date"):
                        year = int(doc_info["issue_date"])
                except ValueError:
                    pass

                # Check if law already exists in PostgreSQL
                stmt = select(Law).where(Law.title == title)
                result = await db.execute(stmt)
                existing_law = result.scalar_one_or_none()

                # Collect all articles from chapters
                articles_list = []
                for ch in doc_info["chapters"]:
                    for sec in ch.get("sections", []):
                        for art in sec.get("articles", []):
                            articles_list.append(art)

                # Reconstruct full text
                full_text_parts = [f"قانون: {title}"]
                if law_number:
                    full_text_parts.append(f"رقم القانون: {law_number}")
                if year:
                    full_text_parts.append(f"سنة الإصدار: {year}")
                
                # Append all articles
                for art in articles_list:
                    art_text = art["article_text"]
                    art_num = art["article_number"]
                    full_text_parts.append(f"\nالمادة ({art_num}):\n{art_text}")

                full_text = "\n".join(full_text_parts)

                if existing_law:
                    print(f"Law '{title}' already exists in PostgreSQL (ID: {existing_law.id}). Updating metadata, full text, and articles...", flush=True)
                    existing_law.full_text = full_text
                    existing_law.articles = doc_info
                    existing_law.category = doc_info.get("document_type", "قانون")
                    existing_law.law_number = law_number
                    existing_law.year = year
                    db_id = existing_law.id
                else:
                    new_law = Law(
                        id=str(uuid.uuid4()),
                        title=title,
                        law_number=law_number,
                        year=year,
                        category=doc_info.get("document_type", "قانون"),
                        full_text=full_text,
                        articles=doc_info,
                        is_active=True
                    )
                    db.add(new_law)
                    db_id = new_law.id
                    print(f"Added '{title}' to PostgreSQL (DB ID: {db_id})", flush=True)

                await db.commit()

                # Check if we already have chunks for this law in Qdrant
                try:
                    count_res = await qdrant.count(
                        collection_name=settings.QDRANT_COLLECTION,
                        count_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="doc_id",
                                    match=MatchValue(value=db_id)
                                )
                            ]
                        )
                    )
                    if count_res.count > 0:
                        print(f"Law '{title}' already has {count_res.count} chunks in Qdrant. Skipping chunk ingestion.", flush=True)
                        continue
                except Exception as e:
                    print(f"Failed to check Qdrant count: {e}", flush=True)

                # 2. Ingest Chunks to Qdrant
                chunks_file = CHUNKS_DIR / f"{json_path.stem}_chunks.json"
                if not chunks_file.exists():
                    print(f"Chunks file not found for {title}: {chunks_file.name}", flush=True)
                    continue

                with open(chunks_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)

                print(f"Ingesting {len(chunks)} chunks to Qdrant in parallel...", flush=True)
                
                # Prepare parallel tasks
                tasks = []
                for chunk in chunks:
                    chunk_text = chunk["text"]
                    embedding_text = chunk.get("embedding_text") or chunk_text
                    
                    async def process_chunk(ch=chunk, et=embedding_text):
                        try:
                            vector = await get_embedding_with_semaphore(et, http)
                            point_id = str(uuid.uuid4())
                            return PointStruct(
                                id=point_id,
                                vector=vector,
                                payload={
                                    "doc_id": db_id,
                                    "title": title,
                                    "chunk_index": ch["chunk_index"],
                                    "text": ch["text"],
                                    "article_number": ch["article_number"],
                                    "article_title": ch.get("article_title") or "",
                                    "summary": ch.get("summary") or "",
                                    "keywords": ch.get("keywords") or [],
                                    "legal_topics": ch.get("legal_topics") or [],
                                    "legal_concepts": ch.get("legal_concepts") or [],
                                    "page_start": ch.get("page_start"),
                                    "page_end": ch.get("page_end"),
                                    "type": "law"
                                }
                            )
                        except Exception as e:
                            print(f"Failed to embed chunk {ch['chunk_id']}: {e}", flush=True)
                            return None
                    
                    tasks.append(process_chunk())

                results = await asyncio.gather(*tasks)
                points = [p for p in results if p is not None]
                print(f"Embedded {len(points)}/{len(chunks)} chunks successfully. Uploading to Qdrant...", flush=True)

                # Upsert in batches of 100
                batch_size = 100
                for offset in range(0, len(points), batch_size):
                    batch = points[offset:offset + batch_size]
                    await qdrant.upsert(collection_name=settings.QDRANT_COLLECTION, points=batch)
                    print(f"Uploaded chunks {offset} to {offset + len(batch)} for {title}", flush=True)

                print(f"Successfully processed {title}: {len(points)}/{len(chunks)} chunks ingested.", flush=True)

    await qdrant.close()
    print("\nAll laws imported and indexed successfully! 🎉", flush=True)

if __name__ == "__main__":
    asyncio.run(import_laws())
