# -*- coding: utf-8 -*-
"""Find medical law / civil code boundary in the PDF."""
import fitz, re

pdf_path = "D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/قانون مزاولة المهن الطبية والصيدلانية اليمني PDF.pdf"
doc = fitz.open(pdf_path)

full_text = ""
for i in range(len(doc)):
    full_text += doc.load_page(i).get_text("text") + "\n"
doc.close()

# Find all article markers
pat = re.compile(r':\)(\d+)\( مادة')
matches = [(int(m.group(1)), m.start()) for m in pat.finditer(full_text)]
print(f"Total articles found: {len(matches)}")
print(f"Article range: {min(m[0] for m in matches)} - {max(m[0] for m in matches)}")

# Group by article number to find discontinuities
article_positions = {}
for num, pos in matches:
    if num not in article_positions:
        article_positions[num] = []
    article_positions[num].append(pos)

print(f"\nArticles with multiple occurrences:")
for num, poses in sorted(article_positions.items()):
    if len(poses) > 1:
        print(f"  Article {num} appears {len(poses)} times")

# Find where the article counter resets (i.e., first occurrence of article 1 is medical, second is civil)
multi = {num: poses for num, poses in article_positions.items() if len(poses) > 1}
if 1 in multi:
    print(f"\nArticle 1 positions: {multi[1]}")
    print(f"Second occurrence context:")
    pos2 = multi[1][1]
    print(full_text[max(0,pos2-100):pos2+200])

# Show structure by chapter headings
print("\n--- Chapter headings ---")
for m in re.finditer(r'(الفصل\s+\S+|الباب\s+\S+|القسم\s+\S+)[^\n]*', full_text):
    pos = m.start()
    nearby = [n for n, p in article_positions.items() if abs(p - pos) < 500]
    print(f"  {m.group(0)} (near article {nearby[0] if nearby else '?'})")
