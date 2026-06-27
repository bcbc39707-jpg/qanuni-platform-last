# -*- coding: utf-8 -*-
"""
Generic re-extraction script for Yemeni laws.
Handles line-based article detection, hierarchy building, and OCR fixes.
"""
import json, re, hashlib
from pathlib import Path
from datetime import datetime
import fitz

# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
LAW_NAME = "القانون المدني اليمني"
LAW_SLUG = "القانون_المدني_اليمني"
PDF_PATH = BASE / "القوانين الرئيسية" / "القانون المدني اليمني PDF.PDF"
JSON_PATH = BASE / "legal_data" / "extracted_json" / "laws" / f"{LAW_SLUG}.json"
CHUNKS_PATH = BASE / "legal_data" / "chunks" / f"{LAW_SLUG}_chunks.json"
REPORT_PATH = BASE / "legal_data" / "extracted_json" / "validation_reports" / f"{LAW_SLUG}_report.json"

# ---------------------------------------------------------------------------
# OCR corrections (same as constitution)
# ---------------------------------------------------------------------------
OCR_FIXES = {
    "الستثمار": "الاستثمار", "الستثمارية": "الاستثمارية",
    "الستجواب": "الاستجواب", "الستراتيجية": "الاستراتيجية",
    "الستغالل": "الاستغلال", "الستفادة": "الاستفادة",
    "الستفتاء": "الاستفتاء", "الستقالة": "الاستقالة",
    "الستقالل": "الاستقلال", "الستقرار": "الاستقرار",
    "الستمرار": "الاستمرار", "الستحقاق": "الاستحقاق",
    "النتخاب": "الانتخاب", "النتخابات": "الانتخابات",
    "النتماء": "الانتماء", "النتهاء": "الانتهاء",
    "القتصاد": "الاقتصاد", "القتصادي": "الاقتصادي",
    "القتصادية": "الاقتصادية",
    "الجراءات": "الإجراءات",
    "الجتماع": "الاجتماع", "الجتماعات": "الاجتماعات",
    "الجتماعي": "الاجتماعي", "الجتماعية": "الاجتماعية",
    "الحتجاز": "الاحتجاز", "الحتكار": "الاحتكار",
    "الحتياطي": "الاحتياطي", "الحتياجات": "الاحتياجات",
    "الختصاص": "الاختصاص", "الختصاصات": "الاختصاصات",
    "الختيار": "الاختيار", "الختراعات": "الاختراعات",
    "الدخار": "الادخار", "الرتباط": "الارتباط",
    "الشتراك": "الاشتراك", "العتراف": "الاعتراف",
    "العتبارية": "الاعتبارية", "القتراح": "الاقتراح",
    "القتراحات": "الاقتراحات", "القتراع": "الاقتراع",
    "المتداد": "الامتداد", "المتيازات": "الامتيازات",
    "المتناع": "الامتناع", "النحراف": "الانحراف",
    "النعقاد": "الانعقاد", "السباب": "الاسباب", "لإ": "لا",
    "النتخالعامة": "الانتخابات العامة",
    "النخابات": "الانتخابات",
    "األحزوممارسة": "الأحزاب وممارسة",
    # RTL ordering: اإل → الإ
    "اإلسالم": "الإسلام", "اإلسالمية": "الإسلامية",
    "اإلجراءات": "الإجراءات", "اإلدارة": "الإدارة",
    "اإلداري": "الإداري", "اإلدارية": "الإدارية",
    "اإلذن": "الإذن", "اإلشراف": "الإشراف",
    "اإلعالن": "الإعلان", "اإلعدام": "الإعدام",
    "اإلفراج": "الإفراج", "اإلنتاج": "الإنتاج",
    "اإلنسان": "الإنسان", "اإلنسانية": "الإنسانية",
    "اإليرادات": "الإيرادات", "اإلقليمية": "الإقليمية",
    "اإلخالل": "الإخلال", "اإلرث": "الإرث",
    "اإلبداع": "الإبداع",
    "واإلجراءات": "والإجراءات", "واإلدارات": "والإدارات",
    "واإلدارية": "والإدارية", "واإلسالمية": "والإسلامية",
    "واإلشراف": "والإشراف", "واإلعالن": "والإعلان",
    "واإلعانات": "والإعانات", "واإلعفاء": "والإعفاء",
    "واإلنجازات": "والإنجازات",
    "باإلدانة": "بالإدانة", "باإلشراف": "بالإشراف",
    "باإلصالح": "بالإصلاح",
    "الجمورية": "الجمهورية",
}

def fix_ocr(text):
    for w, r in OCR_FIXES.items():
        text = text.replace(w, r)
    # عىل → على (alif maqsura → ya) — 956 instances
    text = re.sub(r'عىل', 'على', text)
    # رش → ش in specific known-bad words only
    rsh_words = {
        'الرشكاء': 'الشركاء', 'الرشكة': 'الشركة', 'الرشط': 'الشرط',
        'الرشيك': 'الشريك', 'الرشوط': 'الشروط', 'الرشيعة': 'الشريعة',
        'الرشاء': 'الشراء', 'الرشعية': 'الشرعية', 'الرشعي': 'الشرعي',
        'الرشع': 'الشرع', 'الرشكات': 'الشركات', 'الرشيكني': 'الشريكين',
        'الرشب': 'الشرب', 'الرشف': 'الشرف', 'الرشاف': 'الشراف',
        'الرشاكة': 'الشراكة',  # partnership
        'رشعا': 'شرعا', 'بالرشاء': 'بالشراء',
    }
    for w, r in rsh_words.items():
        text = text.replace(w, r)
    # Also handle vocative يا with alif maqsura
    text = re.sub(r'يى', 'يا', text)
    # اللتزام fixes
    text = re.sub(r'اللزتام', 'الالتزام', text)
    text = re.sub(r'اللزام', 'الالتزام', text)
    # فاذا → فإذا
    text = re.sub(r'فاذا', 'فإذا', text)
    # القايض → القاضي
    text = re.sub(r'القايض', 'القاضي', text)
    # مقتىض → مقتضى
    text = re.sub(r'مقتىض', 'مقتضى', text)
    # الئش → الشيء (OCR split of sheen)
    text = re.sub(r'الئش', 'الشيء', text)
    text = re.sub(r'الئ', 'إلى', text)
    # التاويل → التأويل
    text = re.sub(r'التاويل', 'التأويل', text)
    # الرتجيح → الترجيح
    text = re.sub(r'الرتجيح', 'الترجيح', text)
    # بام → بأم 
    text = re.sub(r'بام', 'بأم', text)
    # القوا ني → القوانين (space inside word)
    text = re.sub(r'القوا ني', 'القوانين', text)
    # التية → التالية
    text = re.sub(r'التية', 'التالية', text)
    # لالحوال → للأحوال (prefix issue: ل+الحوال → ل+ل+أحوال)
    text = text.replace('لالحوال', 'للأحوال')
    # الحوال → الأحوال (not when part of الحوالة)
    text = re.sub(r'الحوال(?!ة)', 'الأحوال', text)
    # اللغاء → الإلغاء
    text = re.sub(r'اللغاء', 'الإلغاء', text)
    # اىل → إلى
    text = text.replace('اىل', 'إلى')
    # اذا → إذا (standalone word only, not inside ماذا etc.)
    text = re.sub(r'\bاذا\b', 'إذا', text)
    # واذا → وإذا (prefix و + اذا)
    text = text.replace('واذا', 'وإذا')
    # رصيحا → صريحا (رص→صر)
    text = re.sub(r'رصيحا', 'صريحا', text)
    text = re.sub(r'رصيحة', 'صريحة', text)
    # More general: رص → صر 
    text = re.sub(r'برص', 'بصر', text)
    # السالمية → الإسلامية
    text = text.replace('السالمية', 'الإسلامية')
    text = text.replace('السالمي', 'الإسلامي')
    # Fix common ر/ي swap in words (تفعيل pattern: ت+letters+ير became ت+letters+ري)
    swap_words = {
        'تفسري': 'تفسير', 'تدبري': 'تدبير', 'تعبري': 'تعبير',
        'تغيري': 'تغيير', 'تخيري': 'تخيير', 'تيسري': 'تيسير',
        'تقدري': 'تقدير', 'تقصري': 'تقصير',
    }
    for w, r in swap_words.items():
        text = text.replace(w, r)
    # Also fix تأ forms with ر/ي swap
    text = text.replace('تاشري', 'تأشير')
    text = text.replace('تاخري', 'تأخير')
    text = text.replace('تاثري', 'تأثير')
    # النتخ fixes
    text = re.sub(r'النتخ(?=[\u0600-\u06FF])', 'الانتخ', text)
    # التيسري → التيسير
    text = re.sub(r'التيسري', 'التيسير', text)
    # معامالت → معاملات (missing alef before last ta)
    text = text.replace('معامالت', 'معاملات')
    # غري → غير (swap of ر and ي — universal, always an OCR error)
    text = text.replace('غري', 'غير')
    # المشرتي → المشتري (swap of ر and ت)
    text = text.replace('المشرتي', 'المشتري')
    text = text.replace('مشرتي', 'مشتري')
    text = text.replace('بالمشرتي', 'بالمشتري')
    # العني → العيني
    text = text.replace('العني', 'العيني')
    # يرصف → يصرف (swap of ر and ص)
    text = text.replace('يرصف', 'يصرف')
    # مؤجال → مؤجلا (swap of ا and ل at end - tanwin alif)
    text = text.replace('مؤجال', 'مؤجلا')
    # الجل → الأجل (missing hamza - legal term for deadline)
    text = re.sub(r'الجل(?![أ-ي])', 'الأجل', text)
    return text

FOOTER_PAT = re.compile(
    r'[\n\s]*\d+\s+\d+\s+تحميل\s+القانون[\s\S]*'
    r'|[\n\s]*نبذه\s+عن\s+النيابة\s+العامة[\s\S]*'
    r'|[\n\s]*(?:Whatsapp|Twitter|Facebook|Instagram)[\s\S]*'
    r'|[\n\s]*موقع النيابة[\s\S]*', re.UNICODE
)

# ---------------------------------------------------------------------------
# Article extraction (line-based, same as constitution)
# ---------------------------------------------------------------------------
def extract_articles(text):
    marker = re.compile(r'\)?(\d+)\(\s*مادة')
    lines = text.split('\n')

    art_lines = []
    for i, line in enumerate(lines):
        m = marker.search(line)
        if m:
            try:
                n = int(m.group(1))
                if 1 <= n <= 2000:
                    art_lines.append((i, n, m))
            except ValueError:
                pass

    # Group all marker occurrences by article number
    occ_groups = {}
    for item in art_lines:
        occ_groups.setdefault(item[1], []).append(item)

    def extract_at(num, occ_list, lines):
        """Try each occurrence; return (cleaned, next_line) or None."""
        for cand_idx, (line_i, _, _) in enumerate(occ_list):
            # Find the soonest next marker (any other number) after line_i
            next_line = len(lines)
            for nxt_num, nxt_items in occ_groups.items():
                if nxt_num == num:
                    continue
                for nl, _, _ in nxt_items:
                    if nl > line_i and nl < next_line:
                        next_line = nl
                        break
            if next_line <= line_i:
                next_line = line_i + 1
            raw = lines[line_i:next_line]
            if not raw:
                continue
            if marker.search(raw[0]):
                raw[0] = marker.sub('', raw[0])
            cleaned = '\n'.join(raw)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            cleaned = re.sub(r' {2,}', ' ', cleaned)
            cleaned = re.sub(r'\n\d+\n', '\n', cleaned)
            cleaned = cleaned.strip()
            cleaned = re.sub(r'^[\)\.\,\s\-–—:]+', '', cleaned)
            cleaned = re.sub(r'[\(\s\-–—]+$', '', cleaned)
            cleaned = cleaned.strip()
            if cand_idx == len(occ_list) - 1:
                cleaned = FOOTER_PAT.sub('', cleaned).strip()
            cleaned = fix_ocr(cleaned)
            if cleaned and len(cleaned) > 10:
                return cleaned
        return None

    articles = []
    for num, occ_list in occ_groups.items():
        cleaned = extract_at(num, occ_list, lines)
        if cleaned:
            articles.append({
                "article_number": str(num), "article_text": cleaned,
                "summary": cleaned[:150] + "..." if len(cleaned) > 150 else cleaned,
            })
    articles.sort(key=lambda a: int(a["article_number"]))
    return articles

# ---------------------------------------------------------------------------
# Structure detection
# ---------------------------------------------------------------------------
LEVEL_KEYS = [
    (re.compile(r'^القسم\s+\S+'), 0),
    (re.compile(r'^الباب\s+\S+'), 1),
    (re.compile(r'^الفصل\s+\S+'), 2),
    (re.compile(r'^الفرع\s+\S+'), 3),
]

def build_structure_map(text):
    """Build [(ch_num, ch_title, sec_num, sec_title, first_art, last_art), ...]"""
    lines = text.split('\n')
    # Find all headers
    headers = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or len(s) > 60:
            continue
        if re.search(r'\d+\(\s*مادة', s):
            continue
        level = None
        for pat, lvl in LEVEL_KEYS:
            if pat.search(s):
                level = lvl
                break
        if level is None:
            continue
        next_art = None
        for j in range(i, min(i+5, len(lines))):
            m = re.search(r'(\d+)\(\s*مادة', lines[j])
            if m:
                next_art = int(m.group(1))
                break
        title = s
        for j in range(i+1, min(i+3, len(lines))):
            t = lines[j].strip()
            if t and len(t) < 100 and not re.search(r'[\d]\(\s*مادة', t):
                is_h = any(pat.search(t) for pat, _ in LEVEL_KEYS)
                if not is_h and not t.startswith('http'):
                    title = t
                    break
        headers.append((level, title, next_art, i))

    # Debug log
    print(f"  Found {len(headers)} structural headers")

    # Build section structure (level 0 → chapters, level 1 → sections)
    # Articles are assigned to their parent chapter/section
    struct = []
    
    # Group by books + chapters
    for i, (lvl, title, art, _) in enumerate(headers):
        if lvl > 1:
            continue  # Skip الفصل and الفرع for simplified structure
        
        # Find the next header at same level to determine article range
        next_art = 2000
        for j in range(i + 1, len(headers)):
            if headers[j][0] <= lvl and headers[j][2] is not None:
                next_art = headers[j][2]
                break
        
        if art is None:
            # Header has no direct article, infer from next header
            for j in range(i + 1, len(headers)):
                if headers[j][0] <= lvl:
                    if headers[j][2] is not None:
                        art = headers[j][2]
                    break
                if headers[j][2] is not None and lvl == 0 and headers[j][0] == 1:
                    # For books, take the first article of the first chapter
                    art = headers[j][2]
                    break
        
        if art is not None:
            struct.append((lvl, title, art, next_art))
    
    return struct

def make_art_entry(a):
    return {
        "article_number": a["article_number"], "article_title": None,
        "article_text": a["article_text"], "page_number": None,
        "summary": a["summary"],
        "keywords": [], "legal_topics": ["قانون مدني"], "legal_concepts": [],
        "rights": [], "obligations": [], "prohibitions": [],
        "permissions": [], "penalties": [], "exceptions": [],
        "procedures": [], "cross_references": [], "entities": []
    }

def build_hierarchy(articles, struct_lines):
    """Build hierarchical JSON from flat article list and structure definition."""
    doc_id = hashlib.md5(LAW_NAME.encode("utf-8")).hexdigest()[:16]
    art_map = {int(a["article_number"]): a for a in articles}
    max_art = max(art_map.keys())
    
    def clean_title(t):
        t = re.sub(r'[.\s]*www.*', '', t).strip()
        t = re.sub(r'[.\s]*\d+ :هاتف.*', '', t).strip()
        return fix_ocr(t)
    
    def collect_arts(start, end):
        end = min(end, max_art + 1)
        result = []
        for i in range(start, end):
            if i in art_map:
                result.append(make_art_entry(art_map[i]))
        return result

    chapters = []
    ch_entries = [(s[0], s[1], s[2], s[3]) for s in struct_lines if s[0] == 0]
    sec_entries = [s for s in struct_lines if s[0] == 1]
    
    # Compute non-overlapping chapter boundaries
    for ci in range(len(ch_entries)):
        _, _, start, end = ch_entries[ci]
        if ci + 1 < len(ch_entries):
            nxt_start = ch_entries[ci + 1][2]
            if end > nxt_start:
                end = nxt_start
        ch_entries[ci] = (0, ch_entries[ci][1], start, end)
    
    sec_idx = 0
    for ci, (_, ch_title, ch_start, ch_end) in enumerate(ch_entries):
        ch_title = clean_title(ch_title)
        ch_end = min(ch_end, max_art + 1)
        
        ch_sections = []
        while sec_idx < len(sec_entries):
            lvl, sec_title, sec_start, sec_end = sec_entries[sec_idx]
            if sec_start >= ch_end:
                break
            sec_title = clean_title(sec_title)
            sec_end = min(sec_end, max_art + 1)
            sec_idx += 1
            
            if sec_start >= sec_end:
                continue
            
            arts = collect_arts(sec_start, sec_end)
            ch_sections.append({
                "section_number": str(len(ch_sections) + 1),
                "section_title": sec_title,
                "articles": arts
            })
        
        # Include book-header articles (from ch_start up to first section's start)
        if ch_sections:
            first_sec_start = None
            for s in struct_lines:
                if s[0] == 1 and s[2] >= ch_start and s[2] < ch_end:
                    first_sec_start = s[2]
                    break
            if first_sec_start and first_sec_start > ch_start:
                header_arts = collect_arts(ch_start, first_sec_start)
                if header_arts:
                    ch_sections.insert(0, {
                        "section_number": "0",
                        "section_title": "أحكام تمهيدية",
                        "articles": header_arts
                    })
        else:
            # Book with no explicit sections -> create implicit one
            arts = collect_arts(ch_start, ch_end)
            ch_sections.append({
                "section_number": "1",
                "section_title": "أحكام عامة",
                "articles": arts
            })
        
        chapters.append({
            "chapter_number": str(ci + 1),
            "chapter_title": ch_title,
            "sections": ch_sections
        })
    
    # Catch any remaining articles not assigned
    assigned = set()
    for ch in chapters:
        for s in ch["sections"]:
            for a in s["articles"]:
                assigned.add(int(a["article_number"]))
    missing = sorted(set(art_map.keys()) - assigned)
    if missing:
        chapters[-1]["sections"].append({
            "section_number": str(len(chapters[-1]["sections"]) + 1),
            "section_title": "أحكام متفرقة",
            "articles": [make_art_entry(art_map[n]) for n in missing]
        })
    
    return {
        "document": {
            "document_id": doc_id,
            "title": LAW_NAME,
            "country": "اليمن",
            "jurisdiction": "الجمهورية اليمنية",
            "document_type": "قانون",
            "law_number": "14",
            "issue_date": "2002",
            "effective_date": "2002",
            "source_file": "القانون المدني اليمني PDF.PDF",
            "language": "ar",
            "total_articles": len(articles),
            "extraction_date": datetime.now().isoformat(),
            "table_of_contents": {"books": [], "chapters": []},
            "chapters": chapters
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
                    "chunk_id": cid, "document_id": doc_info["document_id"],
                    "law_name": doc_info["title"],
                    "article_number": art["article_number"], "article_title": "",
                    "chunk_index": 1, "total_chunks": 1,
                    "text": art["article_text"],
                    "summary": art.get("summary", ""),
                    "keywords": [], "legal_topics": ["قانون مدني"],
                    "legal_concepts": [], "page_start": None, "page_end": None,
                    "embedding_text": (
                        f"قانون: {doc_info['title']}\n"
                        f"المادة: ({art['article_number']})\n"
                        f"النص: {art['article_text']}\n"
                        f"الكلمات المفتاحية: \nالموضوعات: قانون مدني"
                    )
                })
    return chunks

# ---------------------------------------------------------------------------
print("Reading PDF...")
doc = fitz.open(str(PDF_PATH))
full_text = "\n".join(doc.load_page(i).get_text("text") for i in range(len(doc)))
doc.close()

# Clean
clean = re.sub(r'www\.yemenilaw\.com[^\n]*', '', full_text)
clean = re.sub(r'\d+ :هاتف[^\n]*', '', clean)
clean = re.sub(r'هدفنا[^\n]*', '', clean)
clean = re.sub(r'\d+/\d+/\d+[, ]+\d+:\d+[^\n]*', '', clean)
clean = re.sub(r'https?://[^\s]+', '', clean)
clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
print(f"Clean text: {len(clean)} chars")

print("Building structure map...")
struct = build_structure_map(clean)
level0 = [s for s in struct if s[0] == 0]
level1 = [s for s in struct if s[0] == 1]
print(f"  Books: {len(level0)}, Chapters: {len(level1)}")
for s in struct:
    print(f"  L{s[0]}: {s[1][:40]} arts {s[2]}-{s[3]-1}")

print("\nExtracting articles...")
articles = extract_articles(clean)
print(f"Found {len(articles)} articles")
if not articles:
    exit(1)
print(f"Range: {articles[0]['article_number']} - {articles[-1]['article_number']}")

print("Building hierarchical document...")
doc = build_hierarchy(articles, struct)

print("Building chunks...")
chunks = build_chunks(doc)

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print(f"Saved JSON: {len(articles)} articles in {len(doc['document']['chapters'])} chapters")

with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)
print(f"Saved chunks: {len(chunks)}")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    json.dump({
        "law_name": LAW_NAME,
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(articles),
        "total_chunks": len(chunks),
        "structure": [{"chapter": ch["chapter_number"], "title": ch["chapter_title"],
          "sections": [s["section_title"] for s in ch["sections"]],
          "total_articles": sum(len(s["articles"]) for s in ch["sections"])}
          for ch in doc["document"]["chapters"]],
        "status": "success"
    }, f, ensure_ascii=False, indent=2)
print("Done!")
