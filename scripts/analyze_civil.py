# -*- coding: utf-8 -*-
"""Analyze civil code PDF to build hierarchy mapping."""
import fitz, re
from pathlib import Path

PDF_PATH = Path("D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/القوانين الرئيسية/القانون المدني اليمني PDF.PDF")

doc = fitz.open(str(PDF_PATH))
lines = []
for i in range(len(doc)):
    text = doc.load_page(i).get_text("text")
    lines.extend(text.split("\n"))
doc.close()

# Clean watermarks
full = "\n".join(lines)
full = re.sub(r'www\.yemenilaw\.com[^\n]*', '', full)
full = re.sub(r'\d+ :هاتف[^\n]*', '', full)
full = re.sub(r'هدفنا[^\n]*', '', full)
full = re.sub(r'\d+/\d+/\d+[, ]+\d+:\d+[^\n]*', '', full)
full = re.sub(r'https?://[^\s]+', '', full)
lines = full.split("\n")

# Build hierarchy
LEVEL_KEYS = [
    (re.compile(r'^القسم\s+\S+'), 0),
    (re.compile(r'^الباب\s+\S+'), 1),
    (re.compile(r'^الفصل\s+\S+'), 2),
    (re.compile(r'^الفرع\s+\S+'), 3),
]

# Collect all header entries with their levels
all_entries = []
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
    
    # Find next article number
    next_art = None
    for j in range(i, min(i+5, len(lines))):
        m = re.search(r'(\d+)\(\s*مادة', lines[j])
        if m:
            next_art = int(m.group(1))
            break
    
    # Try to find title (next substantive line)
    title = s
    for j in range(i+1, min(i+3, len(lines))):
        t = lines[j].strip()
        if t and len(t) < 100 and not re.search(r'[\d]+\(\s*مادة', t):
            is_header = False
            for pat_inner, _ in LEVEL_KEYS:
                if pat_inner.search(t):
                    is_header = True
                    break
            if not is_header and not t.startswith('http'):
                title = t
                break
    
    all_entries.append((level, title, i, next_art))

# Print simple structure: just the tree with article ranges
stack = []
for lvl, title, line, art in all_entries:
    # Pop stack to correct level
    while stack and stack[-1][0] >= lvl:
        stack.pop()
    stack.append((lvl, title, art))
    
    indent = "  " * lvl
    art_info = f" (art {art})" if art else ""
    print(f"{indent}[L{lvl}] {title}{art_info}")
    
    # Show the children range
    if len(stack) >= 2:
        parent = stack[-2]
        if parent[2] and art:
            pass  # Can compute range

print(f"Total headers: {len(all_entries)}")
