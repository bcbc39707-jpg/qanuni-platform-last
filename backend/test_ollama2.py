import httpx, asyncio, json

async def test():
    async with httpx.AsyncClient(timeout=120.0) as c:
        # Check available models
        r = await c.get("http://host.docker.internal:11434/api/tags")
        models = r.json()["models"]
        print("Available models:")
        for m in models:
            print(f"  {m['name']}")
        
        # Try embed
        embed = await c.post("http://host.docker.internal:11434/api/embed", json={"model": "nomic-embed-text:latest", "input": "test"})
        print(f"\nEmbed status: {embed.status_code}")
        embed_data = embed.json()
        print(f"Embeddings len: {len(embed_data['embeddings'][0])}")
        
        # Try chat
        chat = await c.post("http://host.docker.internal:11434/api/chat", json={
            "model": "aya:8b",
            "messages": [{"role": "user", "content": "Say hello in Arabic."}],
            "options": {"temperature": 0.1}
        })
        print(f"\nChat status: {chat.status_code}")
        chat_data = chat.json()
        content = chat_data["message"]["content"]
        print(f"Chat response: {content[:200]}")

asyncio.run(test())
