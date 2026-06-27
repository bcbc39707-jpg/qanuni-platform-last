# -*- coding: utf-8 -*-
"""Check medical law data duplication details."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "legal_data" / "extracted_json" / "laws"
medical = BASE / "قانون_مزاولة_المهن_الطبية_والصيدلانية.json"
civil = BASE / "القانون_المدني_اليمني.json"

with open(medical, "r", encoding="utf-8") as f:
    med = json.load(f)
with open(civil, "r", encoding="utf-8") as f:
    civ = json.load(f)

med_arts = med["document"]["chapters"][0]["sections"][0]["articles"]
civ_arts = civ["document"]["chapters"][0]["sections"][0]["articles"]

# Check where medical law diverges from civil code
divergence = None
for i, (ma, ca) in enumerate(zip(med_arts, civ_arts)):
    if ma["article_text"] != ca["article_text"]:
        divergence = i
        break

if divergence is not None:
    print(f"First divergence at article index {divergence}")
    print(f"Medical art #{med_arts[divergence]['article_number']}: {med_arts[divergence]['article_text'][:80]}")
    print(f"Civil art #{civ_arts[divergence]['article_number']}: {civ_arts[divergence]['article_text'][:80]}")
else:
    print("All articles are identical!")

# Check if medical law has extra articles beyond civil code
if len(med_arts) > len(civ_arts):
    print(f"\nMedical has {len(med_arts) - len(civ_arts)} more articles than civil")
    print(f"Extra articles: {med_arts[len(civ_arts):][:3]}")
elif len(civ_arts) > len(med_arts):
    print(f"\nCivil has {len(civ_arts) - len(med_arts)} more articles than medical")

# Check the actual content of medical law
print(f"\n--- Medical law actual PDF check ---")
print(f"PDF page count: need to check")
print(f"Estimated real articles: ~50 (based on PDF text length)")
print(f"Current JSON articles: {len(med_arts)}")
print(f"Article range: {med_arts[0]['article_number']} - {med_arts[-1]['article_number']}")

# Check at what point articles become identical 
identical_count = 0
for i, (ma, ca) in enumerate(zip(med_arts, civ_arts)):
    if ma["article_text"] == ca["article_text"]:
        identical_count += 1

print(f"\nIdentical articles: {identical_count} out of {min(len(med_arts), len(civ_arts))}")
