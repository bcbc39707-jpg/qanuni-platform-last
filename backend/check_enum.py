import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT enum_range(NULL::plantype)"))
        for r in result:
            print("Enum values:", r[0])
        
        result2 = await conn.execute(text("SELECT id, plan FROM subscriptions"))
        for r in result2:
            print(f"Sub {r[0]}: plan={r[1]}")

asyncio.run(check())
