import requests
from bs4 import BeautifulSoup
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = "https://agoyemen.net"
session = requests.Session()
session.verify = False

categories = [
    {"name": "القوانين المتعلقة بتنظيم مهام النيابة", "url": "/ntopicsslist.php?id=22"},
    {"name": "الدستور والقوانين الإجرائية", "url": "/ntopicsslist.php?id=1"},
    {"name": "القوانين واللوائح المتضمنة نصوص عقابية", "url": "/ntopicsslist.php?id=2"},
    {"name": "القوانين واللوائح المتعلقة بسلطات الدولة", "url": "/ntopicsslist.php?id=4"},
    {"name": "القانون المدني والأحوال الشخصيه", "url": "/ntopicsslist.php?id=5"},
    {"name": "الاتفاقيات الدولية والاقليمية", "url": "/ntopicsslist.php?id=6"},
    {"name": "الاتفاقيات الثنائية والعربية", "url": "/ntopicsslisttamem.php?id=21"},
    {"name": "المواثيق والإعلانات والمبادئ العالمية", "url": "/ntopicsslist.php?id=23"},
    {"name": "القواعد القانونية والقضائية الجزائية", "url": "/ntopicsslist.php?id=27"},
    {"name": "القواعدالقانونية والقضائية مدني و تجاري", "url": "/ntopicsslist.php?lng=arabic&cid=28"},
]

all_laws = []

for cat in categories:
    print(f"Scraping category: {cat['name']}")
    url = base_url + cat['url']
    page = 1
    while True:
        target_url = f"{url}&page={page}" if page > 1 else url
        print(f"  Fetching: {target_url}")
        try:
            resp = session.get(target_url, timeout=15)
            if resp.status_code != 200:
                print(f"    Failed status: {resp.status_code}")
                break
            
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # Find all links to lib_details.php
            links = soup.find_all("a", href=re.compile(r"lib_details\.php\?id=\d+"))
            if not links:
                print("    No links found on this page.")
                break
                
            found_on_page = 0
            for link in links:
                href = link['href']
                law_id = re.search(r"id=(\d+)", href).group(1)
                title = link.get_text(strip=True)
                # Avoid duplicates
                if not any(x['id'] == law_id for x in all_laws):
                    all_laws.append({
                        "id": law_id,
                        "title": title,
                        "category": cat['name'],
                        "href": href
                    })
                    found_on_page += 1
            
            print(f"    Found {found_on_page} unique laws on page {page}")
            if found_on_page == 0:
                # If no new unique laws, stop pagination
                break
                
            # Check if there is pagination
            pagination = soup.find(class_="pagination")
            if not pagination:
                break
                
            # Check if page number page+1 exists in pagination links
            next_page_str = str(page + 1)
            has_next = False
            for p_link in pagination.find_all("a"):
                if next_page_str in p_link.get_text() or f"page={next_page_str}" in p_link.get('href', ''):
                    has_next = True
                    break
            if not has_next:
                break
            page += 1
        except Exception as e:
            print(f"    Error: {e}")
            break

print(f"\nTotal laws found: {len(all_laws)}")
for idx, law in enumerate(all_laws, 1):
    print(f"{idx}. ID: {law['id']} | Title: {law['title']} | Category: {law['category']}")
