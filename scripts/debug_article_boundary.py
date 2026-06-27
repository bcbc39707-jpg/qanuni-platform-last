# -*- coding: utf-8 -*-
"""Debug the article boundary issue."""
import re, json
from pathlib import Path

with open(Path(__file__).resolve().parent.parent / "legal_data" / "extracted_json" / "laws" / "الدستور_اليمني.json", "r", encoding="utf-8") as f:
    doc = json.load(f)

arts = doc["document"]["chapters"][0]["sections"][0]["articles"]

# Check first 5 articles for completeness
for a in arts[:5]:
    print(f"=== Article {a['article_number']} ===")
    print(a["article_text"][:200])
    print()

# Check if article 1 is missing its first sentence
expected_first = "الجمهورية اليمنية دولة عربية إسالمية مستقلة ذات سيادة"
if expected_first in arts[0]["article_text"]:
    print("Article 1 has correct start!")
else:
    print("Article 1 MISSING first sentence!")
