import httpx
import asyncio
import time

async def test_search():
    print("Testing Search API Endpoint with unique user...")
    query = "حقوق المؤجر"
    
    # Generate unique email and phone based on timestamp
    ts = int(time.time())
    email = f"test_{ts}@qanuni.ai"
    phone = f"96777{str(ts)[-6:]}"
    
    async with httpx.AsyncClient() as client:
        # Check health
        res = await client.get("http://localhost:8000/health")
        print(f"Health check status: {res.status_code}, body: {res.json()}")
        
        print(f"\nRegistering user with email '{email}' and phone '{phone}'...")
        reg_payload = {
            "email": email,
            "password": "strongpassword123",
            "full_name": "باحث تجريبي",
            "phone": phone,
            "role": "client"
        }
        
        reg_res = await client.post("http://localhost:8000/api/v1/auth/register", json=reg_payload)
        print(f"Registration response status: {reg_res.status_code}")
        if reg_res.status_code != 200:
            print("Registration failed. Error:", reg_res.text)
            return
        
        # Login
        print("\nLogging in...")
        login_payload = {
            "email": email,
            "password": "strongpassword123"
        }
        login_res = await client.post("http://localhost:8000/api/v1/auth/login", json=login_payload)
        print(f"Login response status: {login_res.status_code}")
        
        if login_res.status_code != 200:
            print("Failed to login. Error:", login_res.text)
            return
            
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Now run the search
        print(f"\nSearching for '{query}' with authorization...")
        search_res = await client.get(
            f"http://localhost:8000/api/v1/search/?q={query}&doc_type=law",
            headers=headers
        )
        print(f"Search status: {search_res.status_code}")
        if search_res.status_code == 200:
            data = search_res.json()
            print(f"Total results: {data['total']}")
            for idx, r in enumerate(data['results'][:3], 1):
                print(f"  {idx}. Title: {r['title']} (Score: {r['score']})")
                print(f"     Snippet: {r['snippet'][:150]}...")
        else:
            print("Search failed. Error:", search_res.text)

if __name__ == "__main__":
    asyncio.run(test_search())
