import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import AsyncSessionLocal
from sqlalchemy import select, func
from app.models.legal_article import LegalArticle
from app.models.law import Law

async def main():
    db = AsyncSessionLocal()
    art_cnt = (await db.execute(select(func.count(LegalArticle.id)))).scalar()
    law_cnt = (await db.execute(select(func.count(Law.id)))).scalar()
    print(f"Articles in postgres: {art_cnt}")
    print(f"Laws in postgres: {law_cnt}")
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
