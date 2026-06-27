# -*- coding: utf-8 -*-
"""Dump first 2 pages of raw PDF text."""
import fitz

pdf_path = "D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/الدستور اليمني.pdf"
doc = fitz.open(pdf_path)
for i in range(min(3, len(doc))):
    page = doc.load_page(i)
    text = page.get_text("text")
    print(f"=== PAGE {i+1} ({len(text)} chars) ===")
    print(text)
    print()
doc.close()
