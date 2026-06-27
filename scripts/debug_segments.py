# -*- coding: utf-8 -*-
"""Debug segment 0 content."""
import re, json, fitz
from pathlib import Path

pdf_path = Path(__file__).resolve().parent.parent / "القوانين الرئيسية" / "الدستور اليمني.pdf"
doc = fitz.open(str(pdf_path))
text = "\n".join(p.get_text("text") for p in doc)
doc.close()

# Clean
text = re.sub(r'www\.yemenilaw\.com[^\n]*', '', text)
text = re.sub(r'\d+ :هاتف \| \d+ :هاتف \| www\.yemenilaw\.com :الموقع', '', text)
text = re.sub(r'هدفنا نرش الوعي القانوني[^\n]*', '', text)
text = re.sub(r'الموقع القانوني اليمني[^\n]*', '', text)
text = re.sub(r'\d+/\d+/\d+[, ]+\d+:\d+[^\n]*', '', text)
text = re.sub(r'https?://[^\s]+', '', text)
text = re.sub(r'\n{3,}', '\n\n', text)

segments = re.split(r'\d+\(\s*مادة', text)
print(f"Total segments: {len(segments)}")
print(f"=== Segment 0 ({len(segments[0])} chars) ===")
for i, line in enumerate(segments[0].split('\n')):
    print(f"  L{i}: {repr(line[:80])}")

print(f"\n=== Segment 1 ({len(segments[1])} chars) ===")
for i, line in enumerate(segments[1].split('\n')):
    print(f"  L{i}: {repr(line[:80])}")
