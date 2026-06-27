# -*- coding: utf-8 -*-
"""Analyze medical law PDF for article count."""
import fitz, re

pdf_path = "D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/قانون مزاولة المهن الطبية والصيدلانية اليمني PDF.pdf"
doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")

full_text = ""
for i in range(len(doc)):
    text = doc.load_page(i).get_text("text")
    full_text += text + "\n"
doc.close()

# Clean
full_text = re.sub(r'www\.yemenilaw\.com[^\n]*', '', full_text)
full_text = re.sub(r'\d+ :هاتف.*?الموقع', '', full_text)
full_text = re.sub(r'هدفنا.*', '', full_text)
full_text = re.sub(r'\d+/\d+/\d+[, ]+\d+:\d+[^\n]*', '', full_text)
full_text = re.sub(r'https?://[^\s]+', '', full_text)
full_text = full_text.strip()

print(f"Clean text: {len(full_text)} chars")
print(f"\nFirst 500 chars:\n{full_text[:500]}")
print(f"\nLast 500 chars:\n{full_text[-500:]}")

# Count article markers
pat = re.compile(r'(\d+)\s*[\(\[]?\s*مادة', re.MULTILINE)
matches = pat.findall(full_text)
valid = [m for m in matches if 1 <= int(m) <= 200]
print(f"\nArticle markers found: {len(valid)}")
print(f"Article numbers: {sorted(valid, key=int)[:10]}...{sorted(valid, key=int)[-5:] if len(valid) > 5 else ''}")
