# -*- coding: utf-8 -*-
"""Verify constitution structure and OCR."""
import json

p = 'D:/الشريعة - ابي/اعاده صياغة الطعن/المرحله الاولى/تعديل قواعد البيانات/qanuni-platform/legal_data/extracted_json/laws/الدستور_اليمني.json'
with open(p, 'r', encoding='utf-8') as f:
    doc = json.load(f)
d = doc['document']
print('Total articles:', d['total_articles'])
print('Chapters:', len(d['chapters']))
for ch in d['chapters']:
    total = sum(len(s['articles']) for s in ch['sections'])
    sec_names = ', '.join(s['section_title'] for s in ch['sections'])
    print('  Chapter {}: {} ({} arts) [{}]'.format(
        ch['chapter_number'], ch['chapter_title'], total, sec_names))
    for s in ch['sections']:
        arts = s['articles']
        r = ' - '.join([arts[0]['article_number'], arts[-1]['article_number']])
        print('    {}: {} ({} arts)'.format(s['section_title'], r, len(arts)))

# Verify OCR fixes
print('\n=== OCR verification ===')
# Check critical fixes
checks = {
    'الإسلام': False, 'الاستفتاء': False, 'الانتخابات': False,
    'الاقتصاد': False, 'الإجراءات': False, 'الاجتماعية': False,
    'الاستقلال': False, 'الاستثمار': False, 'الامتيازات': False,
    'الاقتراع': False, 'الانتماء': False, 'الاختصاص': False,
}
for ch in d['chapters']:
    for s in ch['sections']:
        for a in s['articles']:
            t = a['article_text']
            for word in checks:
                if word in t:
                    checks[word] = True

print('Correct words found:')
for word, found in checks.items():
    status = 'OK' if found else 'MISSING'
    print('  {}: {}'.format(word, status))

# Also check wrong forms are absent
wrong_checks = ['الستفتاء', 'النتخابات', 'القتصاد', 'الجراءات',
                'الجتماعية', 'المتيازات', 'القتراع', 'النتماء']
print('\nWrong forms present:')
for word in wrong_checks:
    found = False
    for ch in d['chapters']:
        for s in ch['sections']:
            for a in s['articles']:
                if word in a['article_text']:
                    found = True
                    break
    if found:
        print('  {}: STILL PRESENT (FIX FAILED)'.format(word))
    else:
        print('  {}: removed (OK)'.format(word))

# Show article 1-2
print('\n=== Article 1 ===')
print(d['chapters'][0]['sections'][0]['articles'][0]['article_text'][:150])
print('\n=== Article 2 ===')
print(d['chapters'][0]['sections'][0]['articles'][1]['article_text'][:150])
