import asyncio
from sqlalchemy import text
from app.db.session import engine

async def fix():
    async with engine.begin() as conn:
        # Check all enum types
        for enum_name in ["userrole", "plantype", "subscriptionstatus", "casetype", "casestatus", "documenttype"]:
            result = await conn.execute(text(f"SELECT enum_range(NULL::{enum_name})"))
            for r in result:
                print(f"{enum_name}: {r[0]}")
        
        # Update subscription
        result = await conn.execute(text("UPDATE subscriptions SET analysis_quota=9999, search_quota=9999, drafting_quota=9999, plan='PROFESSIONAL'"))
        print(f"Updated {result.rowcount} rows")

asyncio.run(fix())
