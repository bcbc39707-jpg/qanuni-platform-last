# -*- coding: utf-8 -*-
"""
Fix extracted JSON files: repair OCR corruption, Arabic text issues,
and structural problems in legal JSON data.
"""
import json
import re
import os
import sys
from pathlib import Path

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = PROJECT_ROOT / "legal_data" / "extracted_json" / "laws"
REPORTS_DIR = PROJECT_ROOT / "legal_data" / "extracted_json" / "validation_reports"

def fix_arabic_ocr(text: str) -> str:
    """Fix common OCR corruption in Arabic text."""
    if not text:
        return text
    
    fixes = {
        # Fix common OCR splitting issues
        "القوا نين": "القوانين",
        "ال عين": "العين",
        "ال ستعمال": "الاستعمال",
        "ال سكنى": "السكنى",
        "ال رتفاق": "الارتفاق",
        "القوا ن": "القوان",
        "ال شخص": "الشخص",
        "ال اعتباري": "الاعتباري",
        "ال رادة": "الإرادة",
        "ال المنفردة": "المنفردة",
        "المسئولية": "المسؤولية",
        "ال تقصيرية": "التقصيرية",
        "ال عقدية": "العقدية",
        "ال نافع": "النافع",
        "ال تنفيذ": "التنفيذ",
        "التعويض": "التعويض",
        "ال وفاء": "الوفاء",
        "ال مسماة": "المسماة",
        "ال رصف": "الرصف",
        "ال قرض": "القرض",
        "ال صلح": "الصلح",
        "ال تربع": "التربع",
        "ال مقاولة": "المقاولة",
        "ال زتام": "الالتزام",
        "ال وكالة": "الوكالة",
        "ال وديعة": "الوديعة",
        "ال عارية": "العارية",
        "ال تامني": "التأمين",
        "ال سباق": "السباق",
        "ال غصب": "الغصب",
        "ال ملكية": "الملكية",
        "ال قرار": "القرار",
        "ال خرى": "الأخرى",
        
        # Fix common OCR typo characters
        "عىل": "على",
        "ال ": "لا ",
        "هذا": "هذا",
        "هذه": "هذه",
        "ذلك": "ذلك",
        "أو": "أو",
        "أم": "أم",
        "أن": "إن",
        "فى": "في",
        "كل": "كل",
        "بعض": "بعض",
        "غير": "غير",
        "دون": "دون",
        "بين": "بين",
        "تحت": "تحت",
        "فوق": "فوق",
        "عند": "عند",
        "قبل": "قبل",
        "بعد": "بعد",
        
        # HTML entities that leaked
        "&quot;": "",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        
        # URL leakage
        r"www\.yemenilaw\.com.*?(?=\s|$)": "",
        r"\d+ :هاتف.*?(?=\s|$)": "",
        r"هدفنا نرش الوعي القانوني.*?(?=\s|$)": "",
        r"الموقع القانوني اليم[نيين]+.*?(?=\s|$)": "",
    }
    
    for old, new in fixes.items():
        if old.startswith(r"www"):
            text = re.sub(old, new, text)
        else:
            text = text.replace(old, new)
    
    # Fix repeated whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()

def fix_json_file(filepath: Path) -> dict:
    """Fix a single JSON law file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    changes = {"text_fixes": 0, "article_text_fixes": 0}
    
    doc = data.get("document", {})
    
    # Fix metadata fields
    for field in ["title", "country", "jurisdiction"]:
        if field in doc and doc[field]:
            old = doc[field]
            new = fix_arabic_ocr(old)
            if old != new:
                doc[field] = new
                changes["text_fixes"] += 1
    
    # Fix table_of_contents
    toc = doc.get("table_of_contents", {})
    for key in ["books", "chapters"]:
        for item in toc.get(key, []):
            if "title" in item and item["title"]:
                old = item["title"]
                new = fix_arabic_ocr(old)
                if old != new:
                    item["title"] = new
                    changes["text_fixes"] += 1
    
    # Fix articles
    chapters = doc.get("chapters", [])
    for ch in chapters:
        for sec in ch.get("sections", []):
            for art in sec.get("articles", []):
                if "article_text" in art and art["article_text"]:
                    old = art["article_text"]
                    new = fix_arabic_ocr(old)
                    if old != new:
                        art["article_text"] = new
                        changes["article_text_fixes"] += 1
                
                if "summary" in art and art["summary"]:
                    old = art["summary"]
                    new = fix_arabic_ocr(old)
                    if old != new:
                        art["summary"] = new
                        changes["text_fixes"] += 1
    
    # Save fixed data
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return changes

def fix_all():
    """Fix all JSON files."""
    json_files = sorted(list(JSON_DIR.glob("*.json")))
    total_changes = {"text_fixes": 0, "article_text_fixes": 0}
    log_lines = []
    
    for json_path in json_files:
        msg = f"Fixing: {json_path.name}..."
        log_lines.append(msg)
        print(msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        changes = fix_json_file(json_path)
        total_changes["text_fixes"] += changes["text_fixes"]
        total_changes["article_text_fixes"] += changes["article_text_fixes"]
        msg2 = f"OK ({changes['text_fixes']} metadata fixes, {changes['article_text_fixes']} article fixes)"
        log_lines.append(msg2)
        print(msg2)
    
    summary = f"Total: {total_changes['text_fixes']} metadata fixes, {total_changes['article_text_fixes']} article fixes"
    log_lines.append(summary)
    print(summary)
    
    # Write log
    log_path = Path(__file__).resolve().parent / "fix_extracted_json.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"Log written to: {log_path}")

if __name__ == "__main__":
    fix_all()
