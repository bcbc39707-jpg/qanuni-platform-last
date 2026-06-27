# -*- coding: utf-8 -*-
"""Compare medical law and civil code JSON sizes."""
import json, os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "legal_data" / "extracted_json" / "laws"
medical = BASE / "قانون_مزاولة_المهن_الطبية_والصيدلانية.json"
civil = BASE / "القانون_المدني_اليمني.json"

for name, path in [("Medical", medical), ("Civil", civil)]:
    size = os.path.getsize(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    arts = len(data["document"]["chapters"][0]["sections"][0]["articles"])
    first = data["document"]["chapters"][0]["sections"][0]["articles"][0]["article_text"][:80]
    last = data["document"]["chapters"][0]["sections"][0]["articles"][-1]["article_text"][:80]
    print(f"{name}: {size:,} bytes, {arts} articles")
    print(f"  First: {first}")
    print(f"  Last:  {last}")
    print()

# Check if medical law articles match civil code
with open(medical, "r", encoding="utf-8") as f:
    med = json.load(f)
with open(civil, "r", encoding="utf-8") as f:
    civ = json.load(f)

med_arts = med["document"]["chapters"][0]["sections"][0]["articles"]
civ_arts = civ["document"]["chapters"][0]["sections"][0]["articles"]

print(f"Medical: {len(med_arts)} articles, Civil: {len(civ_arts)} articles")
print(f"Medical first 5:")
for a in med_arts[:5]:
    print(f"  Art {a['article_number']}: {a['article_text'][:80]}")
print(f"\nMedical article numbers: {[a['article_number'] for a in med_arts[:10]]}...{[a['article_number'] for a in med_arts[-5:]]}")
