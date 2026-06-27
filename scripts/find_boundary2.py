# -*- coding: utf-8 -*-
"""Find the boundary between medical law and civil code."""
import fitz, re

pdf_path = "D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/قانون مزاولة المهن الطبية والصيدلانية اليمني PDF.pdf"
doc = fitz.open(pdf_path)

full_text = ""
for i in range(len(doc)):
    full_text += doc.load_page(i).get_text("text") + "\n"
doc.close()

pat = re.compile(r':\)(\d+)\( مادة')
matches = [(int(m.group(1)), m.start()) for m in pat.finditer(full_text)]

# Article 1 second occurrence ~16000
# Show articles around position 15000-18000
print("Articles near the boundary:")
boundary_articles = [(n, p) for n, p in matches if 14000 < p < 22000]
for n, p in sorted(boundary_articles, key=lambda x: x[1]):
    ctx = full_text[p:p+100].replace('\n', ' ').strip()
    print(f"  Art {n} at {p}: {ctx[:80]}...")

# Find the first article after pos 15000
first_after = [(n, p) for n, p in matches if p > 15000]
if first_after:
    first_after.sort(key=lambda x: x[1])
    n, p = first_after[0]
    print(f"\nFirst article after position 15000: Article {n} at {p}")
    print(f"  Context: {full_text[p:p+200]}")
