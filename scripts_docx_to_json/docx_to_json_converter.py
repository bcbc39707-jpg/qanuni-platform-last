# -*- coding: utf-8 -*-
"""
DOCX to JSON Converter for Yemeni Legal Documents
=================================================
Converts all .docx files in yemen_legal_docs_v5 into structured JSON.

Usage:
    python docx_to_json_converter.py

Output:
    D:\الشريعة - ابي\new22\legal_data_json\  (one JSON per law + index.json)
"""

import os
import sys
import re
import json
import traceback
from datetime import datetime
from pathlib import Path
from docx import Document

# Fix Windows console encoding for Arabic output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

# ─── Configuration ──────────────────────────────────────────────────
BASE_DIR = r"C:\Users\LEGION\Documents\kimi\workspace\yemen_legal_docs_v5"
OUTPUT_DIR = r"D:\الشريعة - ابي\new22\legal_data_json"
LOG_FILE = os.path.join(OUTPUT_DIR, "conversion_log.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Arabic number mappings
ARABIC_TO_WESTERN = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
    '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
}

ORDINAL_ARABIC = {
    'الاول': '1', 'الأول': '1', 'الثاني': '2', 'الثانى': '2',
    'الثالث': '3', 'الرابع': '4', 'الخامس': '5', 'السادس': '6',
    'السابع': '7', 'الثامن': '8', 'التاسع': '9', 'العاشر': '10',
    'الحادي عشر': '11', 'الثاني عشر': '12', 'الثالث عشر': '13',
    'الرابع عشر': '14', 'الخامس عشر': '15', 'السادس عشر': '16',
    'السابع عشر': '17', 'الثامن عشر': '18', 'التاسع عشر': '19',
    'العشرون': '20', 'العشرين': '20', 'الحادي والعشرون': '21',
    'الثاني والعشرون': '22', 'الثالث والعشرون': '23',
    'الرابع والعشرون': '24', 'الخامس والعشرون': '25',
    'السادس والعشرون': '26', 'السابع والعشرون': '27',
    'الثامن والعشرون': '28', 'التاسع والعشرون': '29',
    'الثلاثون': '30', 'الاربعون': '40', 'الخمسون': '50',
    'الستون': '60', 'السبعون': '70', 'الثمانون': '80', 'التسعون': '90',
    'المئة': '100', 'المائة': '100', 'المائتان': '200',
}

# ─── Helpers ────────────────────────────────────────────────────────

def normalize_arabic_numbers(text):
    """Convert Arabic-Indic digits to Western digits."""
    if not text:
        return text
    return ''.join(ARABIC_TO_WESTERN.get(ch, ch) for ch in text)


def extract_numeric_value(text):
    """Extract the first number from text (Arabic or Western)."""
    text = normalize_arabic_numbers(text)
    match = re.search(r'\d+', text)
    return int(match.group()) if match else None


def parse_arabic_ordinal(text):
    """Try to convert Arabic ordinal words to numbers."""
    text = text.strip().lower()
    for word, num in ORDINAL_ARABIC.items():
        if word in text:
            return int(num)
    return None


def clean_text(text):
    """Clean Arabic text: remove kashida, zero-width chars, normalize spaces."""
    if not text:
        return ""
    # Remove kashida (tatweel)
    text = text.replace('ـ', '')
    # Remove zero-width and non-breaking spaces
    text = text.replace('\u00a0', ' ').replace('\u200b', '').replace('\u200c', '')
    text = text.replace('\u200d', '').replace('\u200e', '').replace('\u200f', '')
    text = text.replace('\ufeff', '').replace('\u2028', '\n').replace('\u2029', '\n')
    # Normalize multiple spaces and newlines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def safe_filename(text):
    """Create a safe filename from Arabic text."""
    text = text.strip()
    # Replace problematic chars
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    text = text[:80]
    return text


# ─── Structure Detectors ────────────────────────────────────────────

RE_KITAB = re.compile(r'^(?:كتاب|الكتاب)\s+(?:ال([\w\s]+)|([\d٠-٩]+))', re.IGNORECASE)
RE_QISM = re.compile(r'^(?:قسم|القسم)\s+(?:ال([\w\s]+)|([\d٠-٩]+))', re.IGNORECASE)
RE_BAB = re.compile(r'^(?:باب|الباب)\s+(?:ال([\w\s]+)|([\d٠-٩]+))', re.IGNORECASE)
RE_FASL = re.compile(r'^(?:فصل|الفصل)\s+(?:ال([\w\s]+)|([\d٠-٩]+))', re.IGNORECASE)
RE_MADDA = re.compile(r'^(?:مادة|المادة)\s*\(?([\d٠-٩]+)\)?', re.IGNORECASE)


def detect_level(text):
    """Detect structural level of a paragraph."""
    text = text.strip()
    if not text:
        return None, None

    # Article
    m = RE_MADDA.match(text)
    if m:
        num_str = normalize_arabic_numbers(m.group(1))
        return 'article', num_str

    # Kitab (Book)
    m = RE_KITAB.match(text)
    if m:
        name = m.group(1) or m.group(2)
        num = parse_arabic_ordinal('ال' + name) if name and not name.isdigit() else extract_numeric_value(name)
        return 'part', num or name

    # Qism (Division/Section)
    m = RE_QISM.match(text)
    if m:
        name = m.group(1) or m.group(2)
        num = parse_arabic_ordinal('ال' + name) if name and not name.isdigit() else extract_numeric_value(name)
        return 'division', num or name

    # Bab (Chapter)
    m = RE_BAB.match(text)
    if m:
        name = m.group(1) or m.group(2)
        num = parse_arabic_ordinal('ال' + name) if name and not name.isdigit() else extract_numeric_value(name)
        return 'chapter', num or name

    # Fasl (Section)
    m = RE_FASL.match(text)
    if m:
        name = m.group(1) or m.group(2)
        num = parse_arabic_ordinal('ال' + name) if name and not name.isdigit() else extract_numeric_value(name)
        return 'subdivision', num or name

    return None, None


# ─── Metadata Extractor ───────────────────────────────────────────

def extract_metadata(paragraphs):
    """Extract metadata from the first few paragraphs."""
    metadata = {
        'title': '',
        'classification': '',
        'number': '',
        'year': '',
        'source_url': '',
        'preamble': '',
    }

    if not paragraphs:
        return metadata

    # Title is usually first paragraph
    metadata['title'] = clean_text(paragraphs[0])

    for i, para in enumerate(paragraphs[:15]):
        para = para.strip()
        if para.startswith('التصنيف:') or para.startswith('التصنيف :'):
            metadata['classification'] = clean_text(para.split(':', 1)[1])
        elif para.startswith('الرقم:') or para.startswith('الرقم :'):
            metadata['number'] = clean_text(para.split(':', 1)[1])
        elif para.startswith('السنة:') or para.startswith('السنة :'):
            metadata['year'] = clean_text(para.split(':', 1)[1])
        elif para.startswith('المصدر:') or para.startswith('المصدر :'):
            metadata['source_url'] = clean_text(para.split(':', 1)[1])

    # Preamble: everything between metadata and first structural marker
    preamble_lines = []
    in_preamble = False
    for i, para in enumerate(paragraphs[:30]):
        if para.startswith('التصنيف:') or para.startswith('الرقم:') or para.startswith('السنة:') or para.startswith('المصدر:'):
            continue
        if i == 0:
            continue  # Skip title
        lvl, _ = detect_level(para)
        if lvl:
            break
        if para.strip():
            in_preamble = True
        if in_preamble:
            preamble_lines.append(para)

    metadata['preamble'] = clean_text('\n'.join(preamble_lines))
    return metadata


# ─── Structure Parser ─────────────────────────────────────────────

def parse_structure(paragraphs):
    """Parse the hierarchical structure of a legal document."""
    metadata = extract_metadata(paragraphs)
    structure = {
        'metadata': metadata,
        'parts': [],
        'articles': [],
        'flat_articles': [],
    }

    current_part = None
    current_chapter = None
    current_division = None
    current_subdivision = None
    current_article = None
    current_article_text = []

    def flush_article():
        nonlocal current_article, current_article_text
        if current_article:
            text = clean_text('\n'.join(current_article_text))
            current_article['content'] = text
            structure['flat_articles'].append(current_article)
            # Add to hierarchy
            target = current_subdivision or current_division or current_chapter or current_part
            if target:
                target.setdefault('articles', []).append(current_article)
            else:
                structure['articles'].append(current_article)
        current_article = None
        current_article_text = []

    def get_or_create_part(title, number=None):
        nonlocal current_part, current_chapter, current_division, current_subdivision
        flush_article()
        current_chapter = None
        current_division = None
        current_subdivision = None
        part = {'title': clean_text(title), 'number': number, 'chapters': [], 'divisions': [], 'articles': []}
        current_part = part
        structure['parts'].append(part)
        return part

    def get_or_create_chapter(title, number=None):
        nonlocal current_chapter, current_division, current_subdivision
        flush_article()
        current_division = None
        current_subdivision = None
        ch = {'title': clean_text(title), 'number': number, 'divisions': [], 'subdivisions': [], 'articles': []}
        current_chapter = ch
        if current_part:
            current_part['chapters'].append(ch)
        else:
            structure.setdefault('orphan_chapters', []).append(ch)
        return ch

    def get_or_create_division(title, number=None):
        nonlocal current_division, current_subdivision
        flush_article()
        current_subdivision = None
        div = {'title': clean_text(title), 'number': number, 'subdivisions': [], 'articles': []}
        current_division = div
        if current_chapter:
            current_chapter['divisions'].append(div)
        elif current_part:
            current_part['divisions'].append(div)
        else:
            structure.setdefault('orphan_divisions', []).append(div)
        return div

    def get_or_create_subdivision(title, number=None):
        nonlocal current_subdivision
        flush_article()
        sub = {'title': clean_text(title), 'number': number, 'articles': []}
        current_subdivision = sub
        if current_division:
            current_division.setdefault('subdivisions', []).append(sub)
        elif current_chapter:
            current_chapter.setdefault('subdivisions', []).append(sub)
        else:
            structure.setdefault('orphan_subdivisions', []).append(sub)
        return sub

    # Start parsing after metadata (skip first ~15 paragraphs where metadata lives)
    start_idx = 0
    for i, para in enumerate(paragraphs[:20]):
        if para.strip().startswith('مادة') or para.strip().startswith('القسم') or para.strip().startswith('الباب') or para.strip().startswith('الفصل') or para.strip().startswith('كتاب'):
            start_idx = i
            break

    # If no structural marker found, just parse all articles from the beginning
    for i, para in enumerate(paragraphs[start_idx:], start=start_idx):
        para = para.strip()
        if not para:
            continue

        lvl, num = detect_level(para)

        if lvl == 'article':
            flush_article()
            current_article = {
                'number': str(num),
                'title': '',
                'content': '',
                'part_number': current_part['number'] if current_part else None,
                'chapter_number': current_chapter['number'] if current_chapter else None,
                'division_number': current_division['number'] if current_division else None,
                'subdivision_number': current_subdivision['number'] if current_subdivision else None,
            }
            current_article_text = [para]

        elif lvl == 'part':
            get_or_create_part(para, num)

        elif lvl == 'chapter':
            get_or_create_chapter(para, num)

        elif lvl == 'division':
            get_or_create_division(para, num)

        elif lvl == 'subdivision':
            get_or_create_subdivision(para, num)

        elif current_article:
            current_article_text.append(para)

    flush_article()

    # Clean up empty lists
    for key in ['orphan_chapters', 'orphan_divisions', 'orphan_subdivisions']:
        if key in structure and not structure[key]:
            del structure[key]

    return structure


# ─── File Processor ─────────────────────────────────────────────────

def process_file(filepath):
    """Process a single .docx file and return structured data."""
    try:
        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs]
        structure = parse_structure(paragraphs)

        result = {
            'source_file': os.path.basename(filepath),
            'source_path': filepath,
            'converted_at': datetime.now().isoformat(),
            'metadata': structure['metadata'],
            'parts': structure.get('parts', []),
            'articles': structure.get('articles', []),
            'flat_articles': structure.get('flat_articles', []),
            'total_articles': len(structure.get('flat_articles', [])),
        }

        return result, None
    except Exception as e:
        return None, f"{os.path.basename(filepath)}: {str(e)}\n{traceback.format_exc()}"


# ─── Main ───────────────────────────────────────────────────────────

def main():
    # Collect all .docx files
    all_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            if f.endswith('.docx') and not f.startswith('~'):
                all_files.append(os.path.join(root, f))

    total = len(all_files)
    print(f"Found {total} .docx files")
    print(f"Output directory: {OUTPUT_DIR}")

    index = []
    errors = []
    success_count = 0

    for i, filepath in enumerate(all_files, 1):
        basename = os.path.basename(filepath)
        print(f"[{i}/{total}] Processing: {basename} ...")

        result, error = process_file(filepath)
        if error:
            errors.append(error)
            print(f"  ERROR: {error[:200]}")
            continue

        # Save individual JSON using source filename to ensure uniqueness
        safe_name = basename.replace('.docx', '').replace('.DOCX', '')
        if not safe_name:
            safe_name = f"doc_{i}"
        json_filename = f"{safe_name}.json"
        json_path = os.path.join(OUTPUT_DIR, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        index.append({
            'id': i,
            'file': json_filename,
            'title': result['metadata']['title'],
            'classification': result['metadata']['classification'],
            'number': result['metadata']['number'],
            'year': result['metadata']['year'],
            'total_articles': result['total_articles'],
        })

        success_count += 1
        print(f"  OK: {result['total_articles']} articles -> {json_filename}")

    # Save index
    index_path = os.path.join(OUTPUT_DIR, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'total_files': total,
            'success_count': success_count,
            'error_count': len(errors),
            'laws': index,
        }, f, ensure_ascii=False, indent=2)

    # Save log
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"DOCX to JSON Conversion Log\n")
        f.write(f"===========================\n")
        f.write(f"Total files: {total}\n")
        f.write(f"Success: {success_count}\n")
        f.write(f"Errors: {len(errors)}\n\n")
        if errors:
            f.write("Errors:\n")
            for e in errors:
                f.write(f"  {e}\n\n")

    print(f"\n{'='*50}")
    print(f"Done! {success_count}/{total} files converted successfully.")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Index: {index_path}")
    if errors:
        print(f"Errors: {len(errors)} (see {LOG_FILE})")


if __name__ == '__main__':
    main()
