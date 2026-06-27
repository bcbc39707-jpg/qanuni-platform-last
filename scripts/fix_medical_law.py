# -*- coding: utf-8 -*-
"""
Re-extract Medical Law from its PDF (which also contains civil code).
Only extract articles 1-43 (the actual medical law portion).
"""
import json, re, hashlib
from pathlib import Path
from datetime import datetime
import fitz

BASE = Path(__file__).resolve().parent.parent
PDF_PATH = BASE / "القوانين الرئيسية" / "قانون مزاولة المهن الطبية والصيدلانية اليمني PDF.pdf"
JSON_PATH = BASE / "legal_data" / "extracted_json" / "laws" / "قانون_مزاولة_المهن_الطبية_والصيدلانية.json"
CHUNKS_PATH = BASE / "legal_data" / "chunks" / "قانون_مزاولة_المهن_الطبية_والصيدلانية_chunks.json"
REPORT_PATH = BASE / "legal_data" / "extracted_json" / "validation_reports" / "قانون_مزاولة_المهن_الطبية_والصيدلانية_report.json"

doc = fitz.open(str(PDF_PATH))
full_text = ""
for i in range(len(doc)):
    full_text += doc.load_page(i).get_text("text") + "\n"
doc.close()

# Clean
text = re.sub(r'www\.yemenilaw\.com[^\n]*', '', full_text)
text = re.sub(r'\d+ :هاتف.*?الموقع', '', text)
text = re.sub(r'هدفنا.*', '', text)
text = re.sub(r'\d+/\d+/\d+[, ]+\d+:\d+[^\n]*', '', text)
text = re.sub(r'https?://[^\s]+', '', text)
text = re.sub(r'\n{3,}', '\n\n', text)

# Extract only medical law portion (articles 1-43, before civil code starts)
pat = re.compile(r':\)(\d+)\(\s*مادة')
matches = [(int(m.group(1)), m.start(), m) for m in pat.finditer(text)]

# Take only first 43 articles
medical_articles = [(n, pos, m) for n, pos, m in matches if n <= 43]
# Remove duplicates for first occurrence
seen = set()
unique_articles = []
for n, pos, m in medical_articles:
    if n not in seen:
        seen.add(n)
        unique_articles.append((n, pos, m))

unique_articles.sort(key=lambda x: x[1])

print(f"Medical law articles: {len(unique_articles)} (expected ~43)")

# Extract article texts using line-based approach (same as constitution)
marker_pat = re.compile(r':\)(\d+)\(\s*مادة')
lines = text.split('\n')
article_lines = []
for i, line in enumerate(lines):
    m = marker_pat.search(line)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 43:
            article_lines.append((i, n, m))

seen2 = set()
deduped = []
for i, n, m in article_lines:
    if n not in seen2:
        seen2.add(n)
        deduped.append((i, n, m))
article_lines = deduped
article_lines.sort(key=lambda x: x[1])

extracted = []
for idx, (line_i, num, match) in enumerate(article_lines):
    next_line_i = article_lines[idx + 1][0] if idx + 1 < len(article_lines) else len(lines)
    raw_lines = lines[line_i:next_line_i]
    raw_lines[0] = marker_pat.sub('', raw_lines[0])
    cleaned = '\n'.join(raw_lines)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    cleaned = re.sub(r'\n\d+\n', '\n', cleaned)
    cleaned = re.sub(r'^[:\)\.\s]+', '', cleaned)
    cleaned = re.sub(r'[\(\s]+$', '', cleaned)
    cleaned = cleaned.strip()
    if cleaned and len(cleaned) > 5:
        extracted.append({
            "article_number": str(num),
            "article_text": cleaned,
            "summary": cleaned[:150] + "..." if len(cleaned) > 150 else cleaned,
        })

extracted.sort(key=lambda a: int(a["article_number"]))
print(f"Extracted: {len(extracted)} articles")
print(f"Range: {extracted[0]['article_number']} - {extracted[-1]['article_number']}")

# Build document
doc_id = hashlib.md5("قانون مزاولة المهن الطبية والصيدلانية".encode("utf-8")).hexdigest()[:16]
chapters = [{
    "chapter_number": "1",
    "chapter_title": "قانون مزاولة المهن الطبية والصيدلانية",
    "sections": [{
        "section_number": "1",
        "section_title": "النصوص",
        "articles": [{
            "article_number": a["article_number"],
            "article_title": None,
            "article_text": a["article_text"],
            "page_number": None,
            "summary": a["summary"],
            "keywords": [],
            "legal_topics": ["مهنة طبية", "صيدلانية"],
            "legal_concepts": [],
            "rights": [], "obligations": [], "prohibitions": [],
            "permissions": [], "penalties": [], "exceptions": [],
            "procedures": [], "cross_references": [],
            "entities": ["المجلس", "الترخيص", "المهنة"]
        } for a in extracted]
    }]
}]
document = {
    "document": {
        "document_id": doc_id,
        "title": "قانون مزاولة المهن الطبية والصيدلانية",
        "country": "اليمن",
        "jurisdiction": "الجمهورية اليمنية",
        "document_type": "قانون",
        "law_number": "26",
        "issue_date": "2002",
        "effective_date": "2002",
        "source_file": "قانون مزاولة المهن الطبية والصيدلانية اليمني PDF.pdf",
        "language": "ar",
        "total_articles": len(extracted),
        "extraction_date": datetime.now().isoformat(),
        "table_of_contents": {"books": [], "chapters": []},
        "chapters": chapters
    }
}

# Chunks
chunks = []
for ch in document["document"]["chapters"]:
    for sec in ch["sections"]:
        for art in sec["articles"]:
            cid = f"{doc_id}_art{art['article_number']}_c1"
            chunks.append({
                "chunk_id": cid,
                "document_id": doc_id,
                "law_name": document["document"]["title"],
                "article_number": art["article_number"],
                "article_title": "",
                "chunk_index": 1,
                "total_chunks": 1,
                "text": art["article_text"],
                "summary": art.get("summary", ""),
                "keywords": [],
                "legal_topics": ["مهنة طبية", "صيدلانية"],
                "legal_concepts": [],
                "page_start": None,
                "page_end": None,
                "embedding_text": (
                    f"قانون: {document['document']['title']}\n"
                    f"المادة: ({art['article_number']})\n"
                    f"النص: {art['article_text']}\n"
                    f"الكلمات المفتاحية: \nالموضوعات: مهنة طبية, صيدلانية"
                )
            })

# Save
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(document, f, ensure_ascii=False, indent=2)
print(f"Saved JSON: {len(extracted)} articles")

with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)
print(f"Saved chunks: {len(chunks)}")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "law_name": "قانون مزاولة المهن الطبية والصيدلانية",
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(extracted),
        "total_chunks": len(chunks),
        "issues": [f"تم إعادة الاستخراج بنجاح: {len(extracted)} مادة (كان 1390 مادة مكررة)"],
        "status": "success"
    }, f, ensure_ascii=False, indent=2)

print("Done!")
