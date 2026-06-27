# -*- coding: utf-8 -*-
"""Final validation of all fixes."""
import json
from pathlib import Path

LAWS_DIR = Path(__file__).resolve().parent.parent / "legal_data" / "extracted_json" / "laws"
CHUNKS_DIR = Path(__file__).resolve().parent.parent / "legal_data" / "chunks"

results = []
for fpath in sorted(LAWS_DIR.glob("*.json")):
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    arts = data["document"]["chapters"][0]["sections"][0]["articles"]
    title = data["document"]["title"]
    num = len(arts)
    
    # Check chunk exists
    cpath = CHUNKS_DIR / f"{fpath.stem}_chunks.json"
    ccount = 0
    if cpath.exists():
        with open(cpath, "r", encoding="utf-8") as f:
            cdata = json.load(f)
        ccount = len(cdata)
    
    # Flag issues
    issues = []
    if num > 100 and title != "القانون المدني اليمني":
        issues.append(f"Many articles ({num})")
    if ccount == 0:
        issues.append("No chunks")
    if num == 0:
        issues.append("Empty")
    
    status = "OK" if not issues else "; ".join(issues)
    print(f"{num:>4} arts | {ccount:>4} chunks | {status} | {title}")

print("\n--- Summary ---")
all_arts = sum(json.load(open(p, "r", encoding="utf-8"))["document"]["chapters"][0]["sections"][0]["articles"] for p in sorted(LAWS_DIR.glob("*.json")))
print(f"Total articles across all laws: {all_arts}")
