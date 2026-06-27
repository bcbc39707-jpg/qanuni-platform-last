# -*- coding: utf-8 -*-
"""Analyze raw PDF text to find missing articles 1-26."""
import fitz, re

pdf_path = "D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/الدستور اليمني.pdf"
doc = fitz.open(pdf_path)
full_text = ""
for i in range(len(doc)):
    page = doc.load_page(i)
    full_text += page.get_text("text") + "\n"
doc.close()

print(f"Total raw text: {len(full_text)} chars")

# Search for article 1 mentions
for pat_name, pat in [
    ("مادة 1", re.compile(r".{0,30}مادة\s+1.{0,80}", re.DOTALL)),
    ("1(مادة", re.compile(r".{0,30}1\(\s*مادة.{0,80}", re.DOTALL)),
    ("(1)", re.compile(r".{0,30}\(1\).{0,80}", re.DOTALL)),
    ("1-", re.compile(r".{0,30}1-[\u0600-\u06FF].{0,80}", re.DOTALL)),
]:
    print(f"\n--- Pattern: {pat_name} ---")
    for m in pat.finditer(full_text[:5000]):
        print(f"  {repr(m.group(0)[:100])}")
