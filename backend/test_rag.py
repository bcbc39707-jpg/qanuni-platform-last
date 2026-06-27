import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import rag_service
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.law import Law

async def test_rag():
    print("Testing RAG Service...")
    # Initialize collection
    await rag_service.init_collection()
    
    # Test queries
    question = "ما هي حقوق المؤجر والمستأجر في القانون اليمني؟"
    print(f"\nQuestion: {question}")
    
    try:
        result = await rag_service.query(question, top_k=3)
        print("\n--- Answer ---")
        print(result["answer"])
        print("\n--- Sources ---")
        for src in result["sources"]:
            print(f"Doc: {src['title']}, Art: {src.get('article_number')}, Chunk: {src['chunk_index']}, Score: {src['score']:.4f}")
    except Exception as e:
        print(f"Error executing query: {e}")
        
    await rag_service.close()

if __name__ == "__main__":
    asyncio.run(test_rag())
