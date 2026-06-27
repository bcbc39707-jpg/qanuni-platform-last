# -*- coding: utf-8 -*-
"""Verify constitution extraction quality."""
import json
from pathlib import Path

fpath = Path(__file__).resolve().parent.parent / "legal_data" / "extracted_json" / "laws" / "الدستور_اليمني.json"
with open(fpath, "r", encoding="utf-8") as f:
    doc = json.load(f)

arts = doc["document"]["chapters"][0]["sections"][0]["articles"]
print(f"Total articles: {len(arts)}")
nums = [int(a["article_number"]) for a in arts]
print(f"Range: {nums[0]} - {nums[-1]}")

expected = set(range(1, nums[-1] + 1))
missing = sorted(expected - set(nums))
print(f"Missing: {missing}")

duplicates = [n for n in nums if nums.count(n) > 1]
print(f"Duplicates: {set(duplicates) if duplicates else 'None'}")

print(f"\n--- Article 1 ---")
print(repr(arts[0]["article_text"][:150]))
print(f"\n--- Article 2 ---")
print(repr(arts[1]["article_text"][:150]))
print(f"\n--- Article 3 ---")
print(repr(arts[2]["article_text"][:150]))
print(f"\n--- Article 4 ---")
print(repr(arts[3]["article_text"][:150]))
print(f"\n--- Last article ({arts[-1]['article_number']}) ---")
print(repr(arts[-1]["article_text"][:200]))
