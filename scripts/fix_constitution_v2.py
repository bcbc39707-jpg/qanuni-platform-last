# -*- coding: utf-8 -*-
"""
Re-extract the Yemeni Constitution from PDF with:
- Proper article detection via line-based marker parsing
- Chapter/section hierarchy (أبواب + فصول)
- OCR Arabic text corrections
"""
import json, re, hashlib
from pathlib import Path
from datetime import datetime
import fitz

BASE = Path(__file__).resolve().parent.parent
PDF_PATH = BASE / "القوانين الرئيسية" / "الدستور اليمني.pdf"
JSON_PATH = BASE / "legal_data" / "extracted_json" / "laws" / "الدستور_اليمني.json"
CHUNKS_PATH = BASE / "legal_data" / "chunks" / "الدستور_اليمني_chunks.json"
REPORT_PATH = BASE / "legal_data" / "extracted_json" / "validation_reports" / "الدستور_اليمني_report.json"

# ---------------------------------------------------------------------------
# OCR corrections
# ---------------------------------------------------------------------------
OCR_FIXES = {
    # Missing alef after definite article (hamzat wasl roots)
    "الستثمار": "الاستثمار",
    "الستثمارية": "الاستثمارية",
    "الستجواب": "الاستجواب",
    "الستراتيجية": "الاستراتيجية",
    "الستغالل": "الاستغلال",
    "الستفادة": "الاستفادة",
    "الستفتاء": "الاستفتاء",
    "الستقالة": "الاستقالة",
    "الستقالل": "الاستقلال",
    "الستقرار": "الاستقرار",
    "الستمرار": "الاستمرار",
    "النتخاب": "الانتخاب",
    "النتخابات": "الانتخابات",
    "النتماء": "الانتماء",
    "النتهاء": "الانتهاء",
    "القتصاد": "الاقتصاد",
    "القتصادي": "الاقتصادي",
    "القتصادية": "الاقتصادية",
    "الجراءات": "الإجراءات",
    "الجتماع": "الاجتماع",
    "الجتماعات": "الاجتماعات",
    "الجتماعي": "الاجتماعي",
    "الجتماعية": "الاجتماعية",
    "الحتجاز": "الاحتجاز",
    "الحتكار": "الاحتكار",
    "الحتياطي": "الاحتياطي",
    "الحتياجات": "الاحتياجات",
    "الختصاص": "الاختصاص",
    "الختصاصات": "الاختصاصات",
    "الختيار": "الاختيار",
    "الختراعات": "الاختراعات",
    "الدخار": "الادخار",
    "الرتباط": "الارتباط",
    "الشتراك": "الاشتراك",
    "العتراف": "الاعتراف",
    "العتبارية": "الاعتبارية",
    "القتراح": "الاقتراح",
    "القتراحات": "الاقتراحات",
    "القتراع": "الاقتراع",
    "المتداد": "الامتداد",
    "المتيازات": "الامتيازات",
    "المتناع": "الامتناع",
    "النحراف": "الانحراف",
    "النعقاد": "الانعقاد",
    "الستحقاق": "الاستحقاق",
    "الستثنى": "الاستثنى",
    "الستئناس": "الاستئناس",
    "الستئناف": "الاستئناف",
    "السباب": "الاسباب",
    "لإ": "لا",
    # Compound corruption (missing chars, merged words)
    "النتخالعامة": "الانتخابات العامة",
    "النخابات": "الانتخابات",
    "األحزوممارسة": "الأحزاب وممارسة",
    "الجمهوريةاليمنية": "الجمهورية اليمنية",
    # RTL ordering fix: اإل → الإ
    "اإلسالم": "الإسلام",
    "اإلسالمية": "الإسلامية",
    "اإلجراءات": "الإجراءات",
    "اإلدارة": "الإدارة",
    "اإلداري": "الإداري",
    "اإلدارية": "الإدارية",
    "اإلذن": "الإذن",
    "اإلشراف": "الإشراف",
    "اإلعالن": "الإعلان",
    "اإلعدام": "الإعدام",
    "اإلفراج": "الإفراج",
    "اإلنتاج": "الإنتاج",
    "اإلنسان": "الإنسان",
    "اإلنسانية": "الإنسانية",
    "اإليرادات": "الإيرادات",
    "اإلقليمية": "الإقليمية",
    "اإلخالل": "الإخلال",
    "اإلرث": "الإرث",
    "اإلبداع": "الإبداع",
    "واإلجراءات": "والإجراءات",
    "واإلدارات": "والإدارات",
    "واإلدارية": "والإدارية",
    "واإلسالمية": "والإسلامية",
    "واإلشراف": "والإشراف",
    "واإلعالن": "والإعلان",
    "واإلعانات": "والإعانات",
    "واإلعفاء": "والإعفاء",
    "واإلنجازات": "والإنجازات",
    "باإلدانة": "بالإدانة",
    "باإلشراف": "بالإشراف",
    "باإلصالح": "بالإصلاح",
}

def apply_ocr_fixes(text):
    for wrong, right in OCR_FIXES.items():
        text = text.replace(wrong, right)
    # النتخ → الانتخ (elections-related words missing alef)
    text = re.sub(r'النتخ(?=[\u0600-\u06FF])', r'الانتخ', text)
    return text

# ---------------------------------------------------------------------------
# Chapter / Section definitions (discovered from PDF analysis)
# ---------------------------------------------------------------------------
STRUCTURE = [
    # (chapter_num, chapter_title, section_num, section_title, first_art, last_art)
    ("1", "أسس الدولة", "1", "الأسس السياسية", 1, 6),
    ("1", "أسس الدولة", "2", "الأسس الاقتصادية", 7, 23),
    ("1", "أسس الدولة", "3", "الأسس الاجتماعية والثقافية", 24, 35),
    ("1", "أسس الدولة", "4", "أسس الدفاع الوطني", 36, 40),
    ("2", "حقوق وواجبات المواطنين", None, None, 41, 61),
    ("3", "تنظيم سلطات الدولة", "1", "السلطة التشريعية - مجلس النواب", 62, 104),
    ("3", "تنظيم سلطات الدولة", "2", "السلطة التنفيذية", 105, 148),
    ("3", "تنظيم سلطات الدولة", "3", "السلطة القضائية", 149, 154),
    ("4", "شعار الجمهورية وعلمها ونشيدها الوطني", None, None, 155, 157),
    ("5", "أصول تعديل الدستور وأحكام عامة", None, None, 158, 162),
]

# ---------------------------------------------------------------------------
# Header patterns to strip from article bodies
# ---------------------------------------------------------------------------
HEADER_PATTERNS = re.compile(
    r'^ةينميل\s+اةيورهمجلور\s+اتسد[\s\n]*'
    r'|[\s\n]*[بف]?(?:اب|صل)\s*\S+[\s\n]*'
    r'|[\s\n]*أسس\s+\S+[\s\n]*'
    r'|[\s\n]*الأسس\s+\S+[\s\n]*',
    re.UNICODE
)

FOOTER_PATTERNS = re.compile(
    r'[\n\s]*\d+\s+\d+\s+تحميل\s+القانون[\s\S]*'
    r'|[\n\s]*نبذه\s+عن\s+النيابة\s+العامة[\s\S]*'
    r'|[\n\s]*(?:Whatsapp|Twitter|Facebook|Instagram)[\s\S]*'
    r'|[\n\s]*موقع النيابة[\s\S]*',
    re.UNICODE
)

# ---------------------------------------------------------------------------
def extract_pdf_text(pdf_path):
    doc = fitz.open(str(pdf_path))
    texts = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        text = page.get_text("text")
        if text.strip():
            texts.append(text.strip())
    doc.close()
    return texts

def clean_text(text):
    text = re.sub(r'www\.yemenilaw\.com[^\n]*', '', text)
    text = re.sub(r'\d+ :هاتف \| \d+ :هاتف \| www\.yemenilaw\.com :الموقع', '', text)
    text = re.sub(r'هدفنا نرش الوعي القانوني[^\n]*', '', text)
    text = re.sub(r'الموقع القانوني اليمني[^\n]*', '', text)
    text = re.sub(r'\d+/\d+/\d+[, ]+\d+:\d+[^\n]*', '', text)
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_articles(text):
    marker_pat = re.compile(r'(\d+)\(\s*مادة')
    lines = text.split('\n')

    article_lines = []
    for i, line in enumerate(lines):
        m = marker_pat.search(line)
        if m:
            try:
                n = int(m.group(1))
                if 1 <= n <= 300:
                    article_lines.append((i, n, m))
            except ValueError:
                pass

    if not article_lines:
        return []

    seen = set()
    deduped = []
    for item in article_lines:
        if item[1] not in seen:
            seen.add(item[1])
            deduped.append(item)
    article_lines = deduped
    article_lines.sort(key=lambda x: x[1])

    articles = []
    for idx, (line_i, num, match) in enumerate(article_lines):
        next_line_i = article_lines[idx + 1][0] if idx + 1 < len(article_lines) else len(lines)
        raw_lines = lines[line_i:next_line_i]
        raw_lines[0] = marker_pat.sub('', raw_lines[0])
        cleaned = '\n'.join(raw_lines)

        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        cleaned = re.sub(r'\n\d+\n', '\n', cleaned)
        cleaned = cleaned.strip()

        # Strip embedded chapter/section headers from every article
        cleaned = HEADER_PATTERNS.sub('', cleaned)

        # Strip footer noise from last article
        if idx == len(article_lines) - 1:
            cleaned = FOOTER_PATTERNS.sub('', cleaned)

        # Clean leading/trailing punctuation and whitespace
        cleaned = re.sub(r'^[\)\.\,\s\-–—]+', '', cleaned)
        cleaned = re.sub(r'[\(\s\-–—]+$', '', cleaned)
        cleaned = cleaned.strip()

        # Apply OCR fixes
        cleaned = apply_ocr_fixes(cleaned)

        if cleaned and len(cleaned) > 10:
            articles.append({
                "article_number": str(num),
                "article_text": cleaned,
                "summary": cleaned[:150] + "..." if len(cleaned) > 150 else cleaned,
            })

    articles.sort(key=lambda a: int(a["article_number"]))
    return articles

def build_hierarchical_document(articles):
    doc_id = hashlib.md5("الدستور اليمني".encode("utf-8")).hexdigest()[:16]
    art_map = {int(a["article_number"]): a for a in articles}

    # Group chapters
    chapters_dict = {}
    for ch_num, ch_title, sec_num, sec_title, first_art, last_art in STRUCTURE:
        if ch_num not in chapters_dict:
            chapters_dict[ch_num] = {
                "chapter_number": ch_num,
                "chapter_title": ch_title,
                "sections": []
            }

        # Collect articles for this range
        section_articles = []
        for i in range(first_art, last_art + 1):
            if i in art_map:
                a = art_map[i]
                section_articles.append({
                    "article_number": a["article_number"],
                    "article_title": None,
                    "article_text": a["article_text"],
                    "page_number": None,
                    "summary": a["summary"],
                    "keywords": [],
                    "legal_topics": ["دستور"],
                    "legal_concepts": [],
                    "rights": [], "obligations": [], "prohibitions": [],
                    "permissions": [], "penalties": [], "exceptions": [],
                    "procedures": [], "cross_references": [],
                    "entities": ["الدولة", "المواطن", "القانون"]
                })

        if sec_title:
            chapters_dict[ch_num]["sections"].append({
                "section_number": sec_num,
                "section_title": sec_title,
                "articles": section_articles
            })
        else:
            chapters_dict[ch_num]["sections"].append({
                "section_number": "1",
                "section_title": ch_title,
                "articles": section_articles
            })

    return {
        "document": {
            "document_id": doc_id,
            "title": "الدستور اليمني",
            "country": "اليمن",
            "jurisdiction": "الجمهورية اليمنية",
            "document_type": "دستور",
            "law_number": None,
            "issue_date": "2001",
            "effective_date": "2001",
            "source_file": "الدستور اليمني.pdf",
            "language": "ar",
            "total_articles": len(articles),
            "extraction_date": datetime.now().isoformat(),
            "table_of_contents": {"books": [], "chapters": []},
            "chapters": [
                chapters_dict[k] for k in sorted(chapters_dict.keys(), key=int)
            ]
        }
    }

def build_chunks(doc):
    chunks = []
    doc_info = doc["document"]
    for ch in doc_info["chapters"]:
        for sec in ch["sections"]:
            for art in sec["articles"]:
                cid = f"{doc_info['document_id']}_art{art['article_number']}_c1"
                chunks.append({
                    "chunk_id": cid,
                    "document_id": doc_info["document_id"],
                    "law_name": doc_info["title"],
                    "article_number": art["article_number"],
                    "article_title": "",
                    "chunk_index": 1,
                    "total_chunks": 1,
                    "text": art["article_text"],
                    "summary": art.get("summary", ""),
                    "keywords": [],
                    "legal_topics": ["دستور"],
                    "legal_concepts": [],
                    "page_start": None,
                    "page_end": None,
                    "embedding_text": (
                        f"قانون: {doc_info['title']}\n"
                        f"المادة: ({art['article_number']})\n"
                        f"النص: {art['article_text']}\n"
                        f"الكلمات المفتاحية: \nالموضوعات: دستور"
                    )
                })
    return chunks

# ---------------------------------------------------------------------------
print("Reading PDF...")
pages = extract_pdf_text(PDF_PATH)
print(f"Found {len(pages)} pages")

full_text = clean_text("\n".join(pages))
print(f"Clean text: {len(full_text)} chars")

print("Extracting articles...")
articles = extract_articles(full_text)
print(f"Found {len(articles)} articles")

if not articles:
    print("ERROR: No articles found!")
    exit(1)

print(f"Article range: {articles[0]['article_number']} - {articles[-1]['article_number']}")

print("Building hierarchical document...")
doc = build_hierarchical_document(articles)

print("Building chunks...")
chunks = build_chunks(doc)

# Save JSON
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print(f"Saved JSON: {len(articles)} articles in {len(doc['document']['chapters'])} chapters")

# Save chunks
with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)
print(f"Saved chunks: {len(chunks)}")

# Save report
report = {
    "law_name": "الدستور اليمني",
    "timestamp": datetime.now().isoformat(),
    "total_articles": len(articles),
    "total_chunks": len(chunks),
    "structure": [
        {"chapter": ch["chapter_number"], "title": ch["chapter_title"],
         "sections": [s["section_title"] for s in ch["sections"]],
         "total_articles": sum(len(s["articles"]) for s in ch["sections"])}
        for ch in doc["document"]["chapters"]
    ],
    "issues": [f"تم إعادة الاستخراج بنجاح: {len(articles)} مادة في {len(doc['document']['chapters'])} أبواب"],
    "status": "success"
}
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("Done!")
