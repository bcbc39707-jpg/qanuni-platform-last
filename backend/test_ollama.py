import httpx, asyncio

async def test():
    async with httpx.AsyncClient() as c:
        r = await c.get("http://host.docker.internal:11434/api/tags")
        print(r.status_code, len(r.json()["models"]), "models")

asyncio.run(test())
