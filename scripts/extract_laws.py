# -*- coding: utf-8 -*-
"""
محرك الاستخراج القانوني المتعدد المراحل
===========================================
يقرأ ملفات PDF القوانين اليمنية ويحولها إلى بيانات JSON منظمة.

المراحل:
  1. قراءة المستند وتحديد بنيته
  2. استخراج النص القانوني الخام لكل مادة
  3. تحويل إلى JSON منظم
  5. تقسيم إلى Chunks
  6. إنشاء embedding_text
  7. التحقق من سلامة المخرجات
"""

import json
import re
import os
import sys
import uuid
import hashlib
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    print("خطأ: مكتبة PyMuPDF غير مثبتة. قم بتثبيتها: pip install PyMuPDF")
    sys.exit(1)

# ─── المسارات ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAWS_DIR = PROJECT_ROOT / "laws"
OUTPUT_JSON_DIR = PROJECT_ROOT / "legal_data" / "extracted_json" / "laws"
OUTPUT_CHUNKS_DIR = PROJECT_ROOT / "legal_data" / "chunks"
OUTPUT_REPORTS_DIR = PROJECT_ROOT / "legal_data" / "extracted_json" / "validation_reports"

for d in [OUTPUT_JSON_DIR, OUTPUT_CHUNKS_DIR, OUTPUT_REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── بيانات القوانين الوصفية ──────────────────────────────
# خريطة تربط اسم الملف بالبيانات الوصفية الرسمية
LAW_METADATA = {
    "الدستور اليمني": {
        "law_number": None,
        "document_type": "دستور",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2001",
        "effective_date": "2001",
    },
    "القانون المدني اليمني": {
        "law_number": "14",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2002",
        "effective_date": "2002",
    },
    "قانون الإثبات اليمني": {
        "law_number": "21",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1992",
        "effective_date": "1992",
    },
    "قانون المرافعات والتنفيذ المدني اليمني": {
        "law_number": "40",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2002",
        "effective_date": "2002",
    },
    "قانون تنظيم العلاقة بين المؤجر والمستأجر اليمني": {
        "law_number": "22",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2006",
        "effective_date": "2006",
    },
    "قانون الأحوال الشخصية اليمني": {
        "law_number": "20",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1992",
        "effective_date": "1992",
    },
    "قانون الوقف الشرعي اليمني": {
        "law_number": "23",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1992",
        "effective_date": "1992",
    },
    "قانون الجرائم والعقوبات اليمني": {
        "law_number": "12",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1994",
        "effective_date": "1994",
    },
    "قانون الإجراءات الجزائية اليمني": {
        "law_number": "13",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1994",
        "effective_date": "1994",
    },
    "القانون التجاري اليمني": {
        "law_number": "32",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1991",
        "effective_date": "1991",
    },
    "قانون الشركات التجارية اليمني": {
        "law_number": "22",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1997",
        "effective_date": "1997",
    },
    "قانون التجارة الداخلية اليمني": {
        "law_number": "5",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2007",
        "effective_date": "2007",
    },
    "قانون أنظمة الدفع والعمليات المالية والمصرفية الإلكترونية": {
        "law_number": "40",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2006",
        "effective_date": "2006",
    },
    "قانون مكافحة غسل الأموال": {
        "law_number": "35",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2003",
        "effective_date": "2003",
    },
    "قانون العمل اليمني": {
        "law_number": "5",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1995",
        "effective_date": "1995",
    },
    "قانون نظام الوظائف والأجور والمرتبات": {
        "law_number": "43",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2005",
        "effective_date": "2005",
    },
    "قانون الإذاعة والتلفزيون": {
        "law_number": "32",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2003",
        "effective_date": "2003",
    },
    "قانون الأراضي وعقارات الدولة": {
        "law_number": "21",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1995",
        "effective_date": "1995",
    },
    "قانون الإسكان والتخطيط الحضري": {
        "law_number": "19",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2002",
        "effective_date": "2002",
    },
    "قانون التخطيط الحضري": {
        "law_number": "20",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1995",
        "effective_date": "1995",
    },
    "قانون المرور": {
        "law_number": "46",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1991",
        "effective_date": "1991",
    },
    "قانون النقل البري": {
        "law_number": "33",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2003",
        "effective_date": "2003",
    },
    "قانون الموانئ البحرية": {
        "law_number": "23",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2013",
        "effective_date": "2013",
    },
    "قانون المناجم والمحاجر": {
        "law_number": "24",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2002",
        "effective_date": "2002",
    },
    "قانون المياه": {
        "law_number": "33",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2002",
        "effective_date": "2002",
    },
    "قانون مزاولة المهن الطبية والصيدلانية": {
        "law_number": "26",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "2002",
        "effective_date": "2002",
    },
    "قانون الزكاة": {
        "law_number": "2",
        "document_type": "قانون",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1999",
        "effective_date": "1999",
    },
    "اللائحة التنفيذية لقانون أراضي وعقارات الدولة": {
        "law_number": "21",
        "document_type": "لائحة تنفيذية",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": "1995",
        "effective_date": "1995",
    },
    "اللائحة التنفيذية لقانون هيئة الشرطة": {
        "law_number": None,
        "document_type": "لائحة تنفيذية",
        "jurisdiction": "الجمهورية اليمنية",
        "issue_date": None,
        "effective_date": None,
    },
}


# ═══════════════════════════════════════════════════════════
#  المرحلة 1: قراءة المستند وتحديد بنيته
# ═══════════════════════════════════════════════════════════

def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """استخراج النص من كل صفحة في ملف PDF."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if text.strip():
            pages.append({
                "page_number": page_num + 1,
                "text": text.strip()
            })
    doc.close()
    return pages


def join_all_text(pages: list[dict]) -> str:
    """دمج نصوص جميع الصفحات في نص واحد مع الحفاظ على أرقام الصفحات."""
    parts = []
    for p in pages:
        parts.append(f"<<PAGE:{p['page_number']}>>")
        parts.append(p["text"])
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
#  المرحلة 2: استخراج النص القانوني الخام لكل مادة
# ═══════════════════════════════════════════════════════════

# نصوص موقع yemenilaw.com المتكررة (watermark/header) التي يجب تنظيفها
WATERMARK_PATTERNS = [
    re.compile(r'www\.yemenilaw\.com \| \d+ \| \d+تم تحميل هذا المحرر من'),
    re.compile(r'الموقع القانوني اليم[نيين]+'),
    re.compile(r'هدفنا نرش الوعي القانوني وتعزيز الوصول إىل المعلومة القانونية'),
    re.compile(r'\d+ :هاتف \| \d+ :هاتف \| www\.yemenilaw\.com :الموقع'),
]

def clean_watermarks(text: str) -> str:
    """إزالة العلامات المائية والترويسات المتكررة من النص."""
    for pat in WATERMARK_PATTERNS:
        text = pat.sub('', text)
    return text

# أنماط regex للتعرف على هياكل القانون العربي
RE_BOOK = re.compile(
    r'(?:^|\n)\s*(?:الكتاب|الباب)\s+'
    r'(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر'
    r'|الحادي عشر|الثاني عشر|الثالث عشر|الرابع عشر|الخامس عشر'
    r'|أول|ثاني|ثالث|رابع|خامس|سادس|سابع|ثامن|تاسع|عاشر'
    r'|\d+)'
    r'\s*[:\-–—]?\s*(.*)',
    re.MULTILINE
)

RE_CHAPTER = re.compile(
    r'(?:^|\n)\s*(?:الفصل|الفرع)\s+'
    r'(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر'
    r'|الحادي عشر|الثاني عشر|الثالث عشر|الرابع عشر|الخامس عشر'
    r'|أول|ثاني|ثالث|رابع|خامس|سادس|سابع|ثامن|تاسع|عاشر'
    r'|\d+)'
    r'\s*[:\-–—]?\s*(.*)',
    re.MULTILINE
)

# أنماط متعددة للتعرف على المواد القانونية
# النمط 1: الشكل المعياري LTR — مادة (3): أو مادة 3:
RE_ARTICLE_STD = re.compile(
    r'(?:^|\n)\s*(?:مادة|الماد[ةه])\s*'
    r'[\(\[\{]\s*(\d+)\s*[\)\]\}]'
    r'\s*[:\-–—]?\s*',
    re.MULTILINE
)

# النمط 2: الشكل RTL من PDF — :)3( مادة (الأقواس معكوسة في النص المستخرج)
RE_ARTICLE_RTL = re.compile(
    r'[:\-–—]?\s*\)\s*(\d+)\s*\(\s*مادة',
    re.MULTILINE
)

# النمط 3: مادة بدون أقواس — مادة 3 -
RE_ARTICLE_PLAIN = re.compile(
    r'(?:^|\n)\s*(?:مادة|الماد[ةه])\s+'
    r'(\d+)\s*[:\-–—]\s*',
    re.MULTILINE
)

# النمط 4: م(3) أو م 3
RE_ARTICLE_SHORT = re.compile(
    r'(?:^|\n)\s*م\s*[\(\[\{]\s*(\d+)\s*[\)\]\}]'
    r'\s*[:\-–—]?\s*',
    re.MULTILINE
)


def find_page_for_position(full_text: str, pos: int) -> int | None:
    """تحديد رقم الصفحة لموقع معين في النص المدمج."""
    page_markers = list(re.finditer(r'<<PAGE:(\d+)>>', full_text))
    current_page = None
    for marker in page_markers:
        if marker.start() <= pos:
            current_page = int(marker.group(1))
        else:
            break
    return current_page


def is_valid_article_number(num_str: str) -> bool:
    """فحص ما إذا كان الرقم يمثل مادة قانونية حقيقية وليس سنة ميلادية أو رقم صفحة."""
    try:
        num = int(num_str)
        # استبعاد السنوات الميلادية (1900-2100)
        if 1900 <= num <= 2100:
            return False
        # استبعاد الأرقام السالبة أو الصفر
        if num <= 0:
            return False
        # أرقام المواد عادة لا تتجاوز 2000
        if num > 2000:
            return False
        return True
    except ValueError:
        return False


def analyze_article_text(text: str) -> dict:
    """استخراج حقول التحليل القانوني من نص المادة كما هو صراحة في النص."""
    # تقسيم النص إلى جمل
    sentences = re.split(r'[.؛]\s*', text)
    first_sentence = sentences[0].strip() if sentences else ""
    summary = first_sentence[:120] + ("..." if len(first_sentence) > 120 else "")

    # الكلمات المفتاحية
    stopwords = {
        "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "أو", "أم", "أن", "إن", "كان", "يكون", "كانت",
        "تم", "تمت", "التي", "الذي", "الذين", "كل", "بعض", "أو", "ثم", "بل", "لكن", "لا", "ما", "لم", "لن", "إلا",
        "غير", "دون", "بين", "تحت", "فوق", "عند", "قبل", "بعد", "أثنا", "خلال", "حيث", "إذا", "لو", "إذاً", "إذ",
        "حتى", "كذلك", "أيضاً", "وقد", "فقد", "بشأن", "بموجب", "وفق", "وفقاً", "طبقاً", "حسب", "تبعاً", "بناءً",
        "سواء", "سواءً", "بواسطة", "عبر", "من خلال", "منذ", "منها", "عنها", "فيها", "إليها", "عليها", "له", "لها",
        "لهم", "به", "بها", "بهم", "عليهم", "إليهم", "عنهم", "منهم", "فيه", "كلما", "أية", "أي", "كما", "لكونه",
        "بذلك"
    }
    words = re.findall(r'\b[\u0600-\u06FF\w]{4,}\b', text)
    keywords = []
    seen_keywords = set()
    for w in words:
        if w not in stopwords and w not in seen_keywords and not w.isdigit():
            seen_keywords.add(w)
            keywords.append(w)
    keywords = keywords[:10]

    # الموضوعات القانونية
    topics_map = {
        "عقوبة": "عقوبات جزائية",
        "حبس": "عقوبات جزائية",
        "سجن": "عقوبات جزائية",
        "غرامة": "عقوبات جزائية",
        "إعدام": "عقوبات جزائية",
        "إيجار": "المعاملات المدنية - الإيجار",
        "مؤجر": "المعاملات المدنية - الإيجار",
        "مستأجر": "المعاملات المدنية - الإيجار",
        "بيع": "المعاملات المدنية - البيع",
        "مشتري": "المعاملات المدنية - البيع",
        "بائع": "المعاملات المدنية - البيع",
        "وقف": "الأحوال الشخصية - الوقف",
        "وصية": "الأحوال الشخصية - الوصية",
        "ميراث": "الأحوال الشخصية - الميراث",
        "زواج": "الأحوال الشخصية - الزواج",
        "طلاق": "الأحوال الشخصية - الطلاق",
        "عقد": "الالتزامات والعقود",
        "التزام": "الالتزامات والعقود",
        "شركة": "القانون التجاري - الشركات",
        "شريك": "القانون التجاري - الشركات",
        "تأمين": "القانون التجاري - التأمين",
        "شيك": "الأوراق التجارية",
        "سفتجة": "الأوراق التجارية",
        "كمبيالة": "الأوراق التجارية",
        "شرطة": "الأمن وهيئة الشرطة",
        "وظيفة": "الوظيفة العامة والأجور",
        "أجر": "قانون العمل",
        "عامل": "قانون العمل",
        "صاحب عمل": "قانون العمل",
        "مياه": "قانون المياه والثروات",
        "أرض": "العقارات وأراضي الدولة",
        "ملك": "الملكية العقارية",
    }
    legal_topics = []
    for key, topic in topics_map.items():
        if key in text:
            if topic not in legal_topics:
                legal_topics.append(topic)
    if not legal_topics:
        legal_topics.append("أحكام عامة")

    # المفاهيم القانونية
    concepts_map = {
        "تعريفات": "التعريفات والمصطلحات",
        "إثبات": "قواعد الإثبات",
        "شهادة": "الشهادة كدليل إثبات",
        "يمين": "اليمين الحاسمة أو المتممة",
        "كتابة": "الإثبات بالكتابة",
        "قرينة": "القرائن القانونية",
        "اعتراف": "الإقرار والاعتراف",
        "معاينة": "المعاينة والخبرة",
        "استئناف": "طرق الطعن - الاستئناف",
        "طعن": "طرق الطعن القضائي",
        "مرافعة": "إجراءات المرافعة",
        "دعوى": "شروط وإجراءات الدعوى",
        "تنفيذ": "التنفيذ الجبري للأحكام",
        "حكم": "الأحكام القضائية",
        "مسؤولية": "المسؤولية التقصيرية أو العقدية",
        "ضرر": "التعويض والضرر",
        "فسخ": "انقضاء العقد بالفسخ",
        "بطلان": "البطلان وموجباته",
    }
    legal_concepts = []
    for key, concept in concepts_map.items():
        if key in text:
            if concept not in legal_concepts:
                legal_concepts.append(concept)

    rights = []
    obligations = []
    prohibitions = []
    permissions = []
    penalties = []
    exceptions = []
    procedures = []

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        
        # حقوق
        if any(w in s for w in ["يحق", "يستحق", "له الحق", "له أن", "يملك"]):
            rights.append(s)
            
        # التزامات
        if any(w in s for w in ["يجب", "يلتزم", "على", "يتعين", "فرض عليه", "مكلف"]):
            if "يجب" in s or "يلتزم" in s or "يتعين" in s or "على ال" in s or "على كل" in s:
                obligations.append(s)
                
        # محظورات
        if any(w in s for w in ["يحظر", "لا يجوز", "يمنع", "ليس له", "لا يعتد"]):
            prohibitions.append(s)
            
        # صلاحيات / إباحات
        if any(w in s for w in ["يجوز", "يمكن", "يباح", "يسمح", "يرخص"]):
            if "لا يجوز" not in s:
                permissions.append(s)
                
        # عقوبات
        if any(w in s for w in ["يعاقب", "عقوبة", "حبس", "سجن", "غرامة", "أشغال", "جلد", "دية", "قصاص"]):
            penalties.append(s)
            
        # استثناءات
        if any(w in s for w in ["إلا إذا", "باستثناء", "إلا في", "ما لم", "خلافا"]):
            exceptions.append(s)
            
        # إجراءات
        if any(w in s for w in ["إجراء", "يقدم الطلب", "يتخذ", "يبلغ", "يرسل", "يحرر"]):
            procedures.append(s)

    # إحالات مرجعية
    cross_references = []
    ref_matches = re.finditer(r'(?:المادة|مادة|المادتين|المواد)\s*\(?(\d+)\)?', text)
    for rm in ref_matches:
        num = rm.group(1)
        ref_str = f"المادة ({num})"
        if ref_str not in cross_references:
            cross_references.append(ref_str)

    # كيانات
    entities_keywords = [
        "المحكمة", "القاضي", "الوزير", "الوزارة", "الحكومة", "النيابة", "مأمور", "ضابط",
        "المؤجر", "المستأجر", "البائع", "المشتري", "الشريك", "الشركة", "العامل", "صاحب العمل",
        "المرخص له", "الهيئة", "اللجنة", "المدير", "الرئيس", "الأمين", "المستفيد", "الواقف",
        "الناظر"
    ]
    entities = []
    for ent in entities_keywords:
        if ent in text:
            entities.append(ent)

    return {
        "summary": summary,
        "keywords": keywords,
        "legal_topics": legal_topics,
        "legal_concepts": legal_concepts,
        "rights": rights,
        "obligations": obligations,
        "prohibitions": prohibitions,
        "permissions": permissions,
        "penalties": penalties,
        "exceptions": exceptions,
        "procedures": procedures,
        "cross_references": cross_references,
        "entities": entities
    }


def extract_structure(full_text: str) -> dict:
    """
    المرحلة 1+2: تحديد بنية المستند واستخراج المواد مع تحليلها القانوني.
    يعيد قاموساً يحتوي على الأبواب والفصول والمواد مع حقول التحليل.
    """
    # تنظيف العلامات المائية أولاً
    cleaned_text = clean_watermarks(full_text)

    # تجربة جميع أنماط المواد واختيار الأفضل
    all_pattern_results = []
    for pattern_name, pattern in [
        ("STD", RE_ARTICLE_STD),
        ("RTL", RE_ARTICLE_RTL),
        ("PLAIN", RE_ARTICLE_PLAIN),
        ("SHORT", RE_ARTICLE_SHORT),
    ]:
        matches = list(pattern.finditer(cleaned_text))
        # تصفية: استبعاد أرقام السنوات والأرقام غير الصالحة
        valid_matches = [m for m in matches if is_valid_article_number(m.group(1))]
        all_pattern_results.append((pattern_name, valid_matches))

    # اختيار النمط الذي أعطى أكثر نتائج صالحة
    best_name, best_matches = max(all_pattern_results, key=lambda x: len(x[1]))

    # البحث عن جميع المواد
    articles = []
    seen_numbers = set()  # لمنع التكرار

    for i, match in enumerate(best_matches):
        article_number = match.group(1)

        # تجاهل المواد المكررة (نفس الرقم)
        if article_number in seen_numbers:
            continue
        seen_numbers.add(article_number)

        start_pos = match.end()

        # نهاية المادة = بداية المادة التالية أو نهاية النص
        # البحث عن أول مادة تالية (غير مكررة)
        end_pos = len(cleaned_text)
        for j in range(i + 1, len(best_matches)):
            next_num = best_matches[j].group(1)
            if next_num != article_number:
                end_pos = best_matches[j].start()
                break

        # استخراج نص المادة
        raw_text = cleaned_text[start_pos:end_pos].strip()
        # تنظيف علامات الصفحات من النص
        raw_text = re.sub(r'<<PAGE:\d+>>', '', raw_text).strip()
        # إزالة أسطر فارغة متكررة
        raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)

        page = find_page_for_position(full_text, match.start())

        if raw_text:  # فقط إضافة مواد بنص غير فارغ
            analysis = analyze_article_text(raw_text)
            articles.append({
                "article_number": article_number,
                "article_title": None,
                "article_text": raw_text,
                "page_number": page,
                **analysis
            })

    # البحث عن الأبواب والفصول
    books = []
    for m in RE_BOOK.finditer(cleaned_text):
        title_text = re.sub(r'<<PAGE:\d+>>', '', m.group(2)).strip()
        books.append({
            "number": m.group(1),
            "title": title_text,
            "position": m.start(),
        })

    chapters = []
    for m in RE_CHAPTER.finditer(cleaned_text):
        title_text = re.sub(r'<<PAGE:\d+>>', '', m.group(2)).strip()
        chapters.append({
            "number": m.group(1),
            "title": title_text,
            "position": m.start(),
        })

    return {
        "books": books,
        "chapters": chapters,
        "articles": articles,
        "_pattern_used": best_name,
        "_pattern_stats": {name: len(ms) for name, ms in all_pattern_results},
    }


# ═══════════════════════════════════════════════════════════
#  المرحلة 3: تحويل إلى JSON منظم
# ═══════════════════════════════════════════════════════════

def build_document_json(
    law_name: str,
    pdf_filename: str,
    structure: dict,
    metadata: dict | None
) -> dict:
    """بناء هيكل JSON المنظم حسب المخطط المحدد في prompot.md."""

    doc_id = hashlib.md5(law_name.encode("utf-8")).hexdigest()[:16]

    meta = metadata or {}

    # بناء هيكل مسطح — كل المواد في قسم واحد لتجنب التكرار
    # المعلومات عن الأبواب والفصول تُحفظ كبيانات وصفية
    all_articles = structure["articles"]

    # إضافة معلومات الباب والفصل لكل مادة بناءً على الموقع
    books = sorted(structure.get("books", []), key=lambda b: b.get("position", 0))
    chapters = sorted(structure.get("chapters", []), key=lambda c: c.get("position", 0))

    chapters_json = [{
        "chapter_number": "1",
        "chapter_title": law_name,
        "sections": [{
            "section_number": "1",
            "section_title": "جميع المواد",
            "articles": all_articles,
        }],
    }]

    # حفظ قائمة الأبواب والفصول كبيانات وصفية إضافية
    books_list = [{"number": b["number"], "title": b["title"]} for b in books]
    chapters_list = [{"number": c["number"], "title": c["title"]} for c in chapters]

    document = {
        "document": {
            "document_id": doc_id,
            "title": law_name,
            "country": "اليمن",
            "jurisdiction": meta.get("jurisdiction", "الجمهورية اليمنية"),
            "document_type": meta.get("document_type", "قانون"),
            "law_number": meta.get("law_number"),
            "issue_date": meta.get("issue_date"),
            "effective_date": meta.get("effective_date"),
            "source_file": pdf_filename,
            "language": "ar",
            "total_articles": len(all_articles),
            "extraction_date": datetime.now().isoformat(),
            "table_of_contents": {
                "books": books_list,
                "chapters": chapters_list,
            },
            "chapters": chapters_json,
        }
    }

    return document


# ═══════════════════════════════════════════════════════════
#  المرحلة 5: تقسيم إلى Chunks
# ═══════════════════════════════════════════════════════════

MAX_CHUNK_SIZE = 800  # أحرف


def build_chunks(document: dict) -> list[dict]:
    """تقسيم المواد إلى chunks منطقية للفهرسة والاسترجاع حسب prompot.md."""
    chunks = []
    doc_info = document["document"]
    doc_id = doc_info["document_id"]
    law_name = doc_info["title"]

    # تجميع كل المواد من كل الفصول
    all_articles = []
    for ch in doc_info["chapters"]:
        for sec in ch.get("sections", []):
            for art in sec.get("articles", []):
                all_articles.append(art)

    for art in all_articles:
        text = art["article_text"]
        art_num = art["article_number"]
        art_title = art.get("article_title") or ""
        art_summary = art.get("summary") or ""
        art_keywords = art.get("keywords") or []
        art_topics = art.get("legal_topics") or []
        art_concepts = art.get("legal_concepts") or []

        if len(text) <= MAX_CHUNK_SIZE:
            # مادة قصيرة = chunk واحد
            chunk_id = f"{doc_id}_art{art_num}_c1"
            chunks.append({
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "law_name": law_name,
                "article_number": art_num,
                "article_title": art_title,
                "chunk_index": 1,
                "total_chunks": 1,
                "text": text,
                "summary": art_summary,
                "keywords": art_keywords,
                "legal_topics": art_topics,
                "legal_concepts": art_concepts,
                "page_start": art.get("page_number"),
                "page_end": art.get("page_number"),
            })
        else:
            # مادة طويلة — تقسيم منطقي بناءً على الفقرات
            paragraphs = re.split(r'\n\s*\n|\n(?=\d+[\-\)\.]\s)', text)
            if len(paragraphs) <= 1:
                # لا توجد فقرات واضحة — تقسيم بناءً على الجمل
                sentences = re.split(r'(?<=[.،؛])\s+', text)
                paragraphs = []
                current = ""
                for s in sentences:
                    if len(current) + len(s) > MAX_CHUNK_SIZE and current:
                        paragraphs.append(current.strip())
                        current = s
                    else:
                        current += " " + s if current else s
                if current:
                    paragraphs.append(current.strip())

            # تجميع الفقرات في chunks
            merged_chunks = []
            current_chunk = ""
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len(current_chunk) + len(p) + 1 > MAX_CHUNK_SIZE and current_chunk:
                    merged_chunks.append(current_chunk.strip())
                    current_chunk = p
                else:
                    current_chunk += "\n" + p if current_chunk else p
            if current_chunk:
                merged_chunks.append(current_chunk.strip())

            total = len(merged_chunks)
            for idx, chunk_text in enumerate(merged_chunks, start=1):
                chunk_id = f"{doc_id}_art{art_num}_c{idx}"
                # إضافة ترويسة المادة في كل chunk للحفاظ على السياق
                header = f"المادة ({art_num})"
                if art_title:
                    header += f" - {art_title}"

                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "law_name": law_name,
                    "article_number": art_num,
                    "article_title": art_title,
                    "chunk_index": idx,
                    "total_chunks": total,
                    "text": f"{header}:\n{chunk_text}" if idx > 1 else chunk_text,
                    "summary": art_summary,
                    "keywords": art_keywords,
                    "legal_topics": art_topics,
                    "legal_concepts": art_concepts,
                    "page_start": art.get("page_number"),
                    "page_end": art.get("page_number"),
                })

    return chunks


# ═══════════════════════════════════════════════════════════
#  المرحلة 6: إنشاء embedding_text
# ═══════════════════════════════════════════════════════════

def build_embedding_text(chunk: dict) -> str:
    """إنشاء نص محسّن للتضمين المتجهي (embedding) حسب مواصفات prompot.md."""
    parts = [
        f"قانون: {chunk['law_name']}",
        f"المادة: ({chunk['article_number']})",
    ]
    if chunk.get("article_title"):
        parts.append(f"العنوان: {chunk['article_title']}")
    parts.append(f"النص: {chunk['text']}")
    
    # إضافة الكلمات المفتاحية والموضوعات
    keywords_str = "، ".join(chunk.get("keywords", []))
    parts.append(f"الكلمات المفتاحية: {keywords_str}")
    
    topics_str = "، ".join(chunk.get("legal_topics", []))
    parts.append(f"الموضوعات: {topics_str}")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
#  المرحلة 7: التحقق من سلامة المخرجات
# ═══════════════════════════════════════════════════════════

def validate_output(document: dict, chunks: list[dict]) -> dict:
    """التحقق من سلامة الإخراج وإنشاء تقرير."""
    report = {
        "law_name": document["document"]["title"],
        "timestamp": datetime.now().isoformat(),
        "total_articles": document["document"]["total_articles"],
        "total_chunks": len(chunks),
        "issues": [],
        "status": "success",
    }

    # فحص 1: هل JSON صالح؟
    try:
        json.dumps(document, ensure_ascii=False)
    except Exception as e:
        report["issues"].append(f"JSON غير صالح: {str(e)}")
        report["status"] = "error"

    # فحص 2: هل توجد مواد بنص فارغ؟
    empty_articles = []
    for ch in document["document"]["chapters"]:
        for sec in ch.get("sections", []):
            for art in sec.get("articles", []):
                if not art.get("article_text", "").strip():
                    empty_articles.append(art["article_number"])

    if empty_articles:
        report["issues"].append(
            f"مواد بنص فارغ: {', '.join(empty_articles)}"
        )
        report["status"] = "warning"

    # فحص 3: هل أرقام المواد متسلسلة؟
    all_nums = []
    for ch in document["document"]["chapters"]:
        for sec in ch.get("sections", []):
            for art in sec.get("articles", []):
                try:
                    all_nums.append(int(art["article_number"]))
                except ValueError:
                    pass

    if all_nums:
        all_nums_sorted = sorted(all_nums)
        missing = []
        for i in range(all_nums_sorted[0], all_nums_sorted[-1] + 1):
            if i not in all_nums:
                missing.append(str(i))
        if missing and len(missing) < 50:  # لا نعرض إذا كان الفرق كبيراً جداً
            report["issues"].append(
                f"مواد قد تكون مفقودة: {', '.join(missing[:20])}"
                + (f" ... و {len(missing)-20} أخرى" if len(missing) > 20 else "")
            )
            report["status"] = "warning"

    # فحص 4: هل كل chunk يحتوي على نص؟
    empty_chunks = [c["chunk_id"] for c in chunks if not c.get("text", "").strip()]
    if empty_chunks:
        report["issues"].append(
            f"chunks فارغة: {len(empty_chunks)}"
        )
        report["status"] = "warning"

    # فحص 5: هل embedding_text موجود؟
    no_embedding = [c["chunk_id"] for c in chunks if not c.get("embedding_text")]
    if no_embedding:
        report["issues"].append(
            f"chunks بدون embedding_text: {len(no_embedding)}"
        )

    if not report["issues"]:
        report["issues"].append("✅ لا توجد مشاكل - الإخراج سليم")

    return report


# ═══════════════════════════════════════════════════════════
#  التنفيذ الرئيسي
# ═══════════════════════════════════════════════════════════

def process_single_pdf(pdf_path: Path, law_name: str) -> dict:
    """معالجة ملف PDF واحد عبر جميع المراحل."""
    print(f"\n{'='*60}")
    print(f"  📜 معالجة: {law_name}")
    print(f"  📁 ملف: {pdf_path.name}")
    print(f"{'='*60}")

    # المرحلة 1: قراءة PDF
    print("  ▸ المرحلة 1: قراءة المستند...")
    pages = extract_text_from_pdf(pdf_path)
    full_text = join_all_text(pages)
    print(f"    ✓ تم قراءة {len(pages)} صفحة")

    # المرحلة 2: استخراج البنية والمواد
    print("  ▸ المرحلة 2: استخراج النص القانوني...")
    structure = extract_structure(full_text)
    print(f"    ✓ {len(structure['articles'])} مادة | "
          f"{len(structure['books'])} باب | "
          f"{len(structure['chapters'])} فصل")

    if not structure["articles"]:
        print("    ⚠ تحذير: لم يتم العثور على مواد قانونية في هذا الملف!")
        return {"status": "no_articles", "law_name": law_name}

    # المرحلة 3: بناء JSON
    print("  ▸ المرحلة 3: بناء JSON منظم...")
    metadata = LAW_METADATA.get(law_name)
    document = build_document_json(law_name, pdf_path.name, structure, metadata)
    print(f"    ✓ تم بناء الهيكل")

    # المرحلة 5: تقسيم إلى Chunks
    print("  ▸ المرحلة 5: تقسيم إلى Chunks...")
    chunks = build_chunks(document)
    print(f"    ✓ {len(chunks)} chunk تم إنشاؤها")

    # المرحلة 6: إنشاء embedding_text
    print("  ▸ المرحلة 6: إنشاء embedding_text...")
    for chunk in chunks:
        chunk["embedding_text"] = build_embedding_text(chunk)
    print(f"    ✓ تم إنشاء نصوص التضمين")

    # المرحلة 7: التحقق
    print("  ▸ المرحلة 7: التحقق من سلامة المخرجات...")
    report = validate_output(document, chunks)
    status_icon = "✅" if report["status"] == "success" else "⚠"
    print(f"    {status_icon} الحالة: {report['status']}")
    for issue in report["issues"]:
        print(f"       • {issue}")

    # حفظ المخرجات
    safe_name = re.sub(r'[^\w\u0600-\u06FF\s]', '', law_name).strip().replace(' ', '_')

    # حفظ JSON المنظم
    json_path = OUTPUT_JSON_DIR / f"{safe_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
    print(f"  💾 JSON: {json_path.name}")

    # حفظ Chunks
    chunks_path = OUTPUT_CHUNKS_DIR / f"{safe_name}_chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  💾 Chunks: {chunks_path.name}")

    # حفظ تقرير التحقق
    report_path = OUTPUT_REPORTS_DIR / f"{safe_name}_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  💾 Report: {report_path.name}")

    return {
        "status": report["status"],
        "law_name": law_name,
        "articles": len(structure["articles"]),
        "chunks": len(chunks),
        "pages": len(pages),
    }


def discover_pdfs() -> list[tuple[Path, str]]:
    """اكتشاف جميع ملفات PDF في مجلدات القوانين وتحديد أسمائها."""
    pdfs = []
    for pdf_path in sorted(LAWS_DIR.rglob("*.pdf")):
        # استخراج اسم القانون من اسم الملف
        name = pdf_path.stem  # اسم الملف بدون الامتداد
        pdfs.append((pdf_path, name))
    return pdfs


def main():
    print("\n" + "═" * 60)
    print("  محرك الاستخراج القانوني المتعدد المراحل")
    print("  Qanuni Legal Extraction Engine v1.0")
    print("═" * 60)

    # اكتشاف الملفات
    pdfs = discover_pdfs()
    if not pdfs:
        print("❌ لم يتم العثور على ملفات PDF في مجلد laws/")
        return

    print(f"\n📚 تم اكتشاف {len(pdfs)} ملف قانوني")
    print("-" * 40)
    for i, (path, name) in enumerate(pdfs, 1):
        print(f"  {i:2d}. {name}")

    # معالجة كل ملف
    results = []
    for pdf_path, law_name in pdfs:
        try:
            result = process_single_pdf(pdf_path, law_name)
            results.append(result)
        except Exception as e:
            print(f"\n  ❌ خطأ في معالجة {law_name}: {e}")
            results.append({
                "status": "error",
                "law_name": law_name,
                "error": str(e),
            })

    # ملخص نهائي
    print("\n\n" + "═" * 60)
    print("  📊 الملخص النهائي")
    print("═" * 60)

    total_articles = sum(r.get("articles", 0) for r in results)
    total_chunks = sum(r.get("chunks", 0) for r in results)
    success = sum(1 for r in results if r["status"] == "success")
    warnings = sum(1 for r in results if r["status"] == "warning")
    errors = sum(1 for r in results if r["status"] in ("error", "no_articles"))

    print(f"  📄 إجمالي القوانين المعالجة: {len(results)}")
    print(f"  ✅ ناجح: {success}")
    print(f"  ⚠  تحذيرات: {warnings}")
    print(f"  ❌ أخطاء: {errors}")
    print(f"  📝 إجمالي المواد المستخرجة: {total_articles}")
    print(f"  🧩 إجمالي الـ Chunks: {total_chunks}")
    print(f"\n  📁 المخرجات في: {OUTPUT_JSON_DIR}")
    print(f"  📁 الـ Chunks في: {OUTPUT_CHUNKS_DIR}")
    print(f"  📁 التقارير في: {OUTPUT_REPORTS_DIR}")

    # حفظ ملخص شامل
    summary = {
        "extraction_date": datetime.now().isoformat(),
        "total_files": len(results),
        "total_articles": total_articles,
        "total_chunks": total_chunks,
        "success": success,
        "warnings": warnings,
        "errors": errors,
        "details": results,
    }
    summary_path = OUTPUT_REPORTS_DIR / "extraction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n  📋 الملخص الشامل: {summary_path.name}")


if __name__ == "__main__":
    main()
