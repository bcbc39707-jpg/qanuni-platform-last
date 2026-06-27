# -*- coding: utf-8 -*-
"""Deep analysis of medical law PDF structure."""
import fitz, re

pdf_path = "D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/قانون مزاولة المهن الطبية والصيدلانية اليمني PDF.pdf"
doc = fitz.open(pdf_path)

full_text = ""
for i in range(len(doc)):
    full_text += doc.load_page(i).get_text("text") + "\n"
doc.close()

# Count ALL article markers
pat = re.compile(r'\((\d+)\)\s*مادة', re.MULTILINE)
matches = pat.findall(full_text)
print(f"Pattern (N)مادة: {len(matches)} matches")
nums = sorted(set(int(m) for m in matches))
print(f"Distinct article numbers: {len(nums)}")
print(f"Range: {min(nums)} - {max(nums)}")
print(f"First 15: {nums[:15]}")
print(f"Last 10: {nums[-10:]}")

# Check where the article numbers change from medical to civil
print("\nSearching for law title in later pages...")
for m in re.finditer(r'قانون المهن الطبية', full_text):
    pos = m.start()
    context = full_text[max(0,pos-50):pos+100]
    print(f"  At pos {pos}: ...{context}...")

# Check article 196 content
for m in re.finditer(r'\(\s*196\s*\)\s*مادة', full_text):
    pos = m.start()
    print(f"\nArticle 196 at pos {pos}:")
    print(full_text[pos:pos+200])
