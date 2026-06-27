import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT category, COUNT(*) FROM laws GROUP BY category"))
        print("Law Categories:")
        for r in result:
            print(f"  {r[0]}: {r[1]}")

        result2 = await conn.execute(text("SELECT COUNT(*) FROM rulings"))
        print(f"Rulings Count: {result2.scalar()}")

asyncio.run(check())
