# -*- coding: utf-8 -*-
"""Analyze constitution text for article patterns."""
import json, re
from pathlib import Path

fpath = Path(__file__).resolve().parent.parent / "legal_data" / "extracted_json" / "laws" / "الدستور_اليمني.json"
with open(fpath, "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [a["article_text"] for a in data["document"]["chapters"][0]["sections"][0]["articles"]]
full = "\n".join(texts)

print(f"Total text length: {len(full)} chars")

# The pattern is: NNN(مادة
pat = re.compile(r"(\d+)\(\s*مادة")
matches = list(pat.finditer(full))
print(f"Pattern N(مادة: {len(matches)} matches")
for m in matches[:10]:
    print(f"  Article {m.group(1)} at {m.start()}")

# Also check for the opposite order
pat2 = re.compile(r"مادة\s*\((\d+)\)")
matches2 = list(pat2.finditer(full))
print(f"\nPattern مادة(عدد): {len(matches2)} matches")
for m in matches2[:10]:
    print(f"  Article {m.group(1)} at {m.start()}")

# Plain: مادة عدد
pat3 = re.compile(r"مادة\s+(\d+)")
matches3 = list(pat3.finditer(full))
print(f"\nPattern مادة عدد: {len(matches3)} matches")
for m in matches3[:10]:
    print(f"  Article {m.group(1)} at {m.start()}")

# Try to extract articles properly
print("\n--- Attempting full extraction ---")
all_articles = []
seen = set()

for m in sorted(matches + matches2, key=lambda x: x.start()):
    num = m.group(1)
    if num in seen:
        continue
    try:
        n = int(num)
        if n < 1 or n > 200:
            continue
    except ValueError:
        continue
    seen.add(num)
    all_articles.append((m.start(), num))

print(f"Total unique articles: {len(all_articles)}")
print(f"Article numbers: {sorted([int(a[1]) for a in all_articles])}")
