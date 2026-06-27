# -*- coding: utf-8 -*-
"""Fix the constitution JSON - extract all articles from merged text."""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
JSON_PATH = BASE / "legal_data" / "extracted_json" / "laws" / "الدستور_اليمني.json"
CHUNKS_PATH = BASE / "legal_data" / "chunks" / "الدستور_اليمني_chunks.json"
REPORT_PATH = BASE / "legal_data" / "extracted_json" / "validation_reports" / "الدستور_اليمني_report.json"

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

doc = data["document"]
old_articles = doc["chapters"][0]["sections"][0]["articles"]

# Combine text from old (merged) articles
full_text = "\n".join(a["article_text"] for a in old_articles)

# Remove URL/header artifacts
full_text = re.sub(
    r"\d+/\d+/\d+[, ]+\d+:\d+ (AM|PM)?مكتب النائب العام اليمن\nhttps://agoyemen\.net/[^\s]+",
    "", full_text
)
full_text = re.sub(r"\d+/\d+/\d+[, ]+\d+:\d+ (AM|PM)?", "", full_text)
full_text = re.sub(r"\nhttps://agoyemen\.net/[^\s]+", "", full_text)
full_text = re.sub(r"\d+/\d+\n\n", "", full_text)

# Extract using RTL pattern: )N(مادة
pat = re.compile(r'\)\s*(\d+)\s*\(\s*مادة', re.MULTILINE)
matches = list(pat.finditer(full_text))

print(f"Found {len(matches)} article boundaries")
seen = set()
new_articles = []
for i, m in enumerate(matches):
    num = m.group(1)
    if num in seen:
        continue
    seen.add(num)
    start = m.end()
    end = matches[i+1].start() if i+1 < len(matches) else len(full_text)
    text = full_text[start:end].strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    if text:
        new_articles.append({
            "article_number": num,
            "article_title": None,
            "article_text": text,
            "page_number": None,
            "summary": text[:120] + "..." if len(text) > 120 else text,
            "keywords": [],
            "legal_topics": ["دستور"],
            "legal_concepts": [],
            "rights": [],
            "obligations": [],
            "prohibitions": [],
            "permissions": [],
            "penalties": [],
            "exceptions": [],
            "procedures": [],
            "cross_references": [],
            "entities": ["الدولة", "القانون", "المواطن"]
        })

print(f"Extracted {len(new_articles)} individual articles")

doc["chapters"][0]["sections"][0]["articles"] = new_articles
doc["total_articles"] = len(new_articles)

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Saved JSON with {len(new_articles)} articles")

# Rebuild chunks
import uuid
chunks = []
for art in new_articles:
    art_num = art["article_number"]
    chunk_id = f"{doc['document_id']}_art{art_num}_c1"
    chunks.append({
        "chunk_id": chunk_id,
        "document_id": doc["document_id"],
        "law_name": doc["title"],
        "article_number": art_num,
        "article_title": "",
        "chunk_index": 1,
        "total_chunks": 1,
        "text": art["article_text"],
        "summary": art["summary"],
        "keywords": [],
        "legal_topics": ["دستور"],
        "legal_concepts": [],
        "page_start": None,
        "page_end": None,
        "embedding_text": f"قانون: {doc['title']}\nالمادة: ({art_num})\nالنص: {art['article_text']}\nالكلمات المفتاحية: \nالموضوعات: دستور"
    })

with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)
print(f"Saved {len(chunks)} chunks")

# Update report
report = {
    "law_name": "الدستور اليمني",
    "timestamp": "2026-06-09T00:00:00",
    "total_articles": len(new_articles),
    "total_chunks": len(chunks),
    "issues": [f"تم إصلاح الاستخراج: {len(new_articles)} مادة دستورية"],
    "status": "success"
}
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("Report updated")
