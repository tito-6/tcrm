# -*- coding: utf-8 -*-
"""Run inside: python -m tcrm shell -c tcrm.conf < this file
OR: exec(open(r'd:\\tcrm\\scripts\\_test_direct_ai.py', encoding='utf-8').read())
"""
import importlib.util
import json
import sys

path = r'd:\tcrm\custom_addons\tcrm_ai\controllers\main.py'
spec = importlib.util.spec_from_file_location('tcrm_ai_main_direct', path)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

fn = mod._try_direct_propertio_answer
out = []

queries = [
    'kaç tane satışımız var',
    'satışlarımızı listele',
    'hangi daireler müsait',
    'Mavi Bahçe projesi hakkında bilgi ver',
    'gecikmiş ödemeler var mı',
    'toplam tahsilat ne kadar',
    'Mehmet Yılmaz ödeme planı',
    'OVER-999 kontratı',
    'iptal satışlar',
    'kaç satışımız var',
    'müşterilerimizi listele',
]

for q in queries:
    try:
        r = fn(env, q)
        if r is None:
            out.append({'q': q, 'direct': False, 'answer': None})
        else:
            sample_rows = []
            tables = r.get('tables') or []
            if tables and tables[0].get('rows'):
                sample_rows = tables[0]['rows'][:3]
            out.append({
                'q': q,
                'direct': True,
                'answer': r.get('answer'),
                'tables': len(tables),
                'sample_rows': sample_rows,
                'error': r.get('error'),
            })
    except Exception as e:
        out.append({'q': q, 'direct': 'ERR', 'answer': str(e)})

report_path = r'd:\tcrm\scripts\_ai_direct_results.json'
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# Also write a simple text report
txt_path = r'd:\tcrm\scripts\_ai_direct_results.txt'
with open(txt_path, 'w', encoding='utf-8') as f:
    for row in out:
        f.write('%s\n  direct=%s\n  answer=%s\n\n' % (
            row['q'], row.get('direct'), row.get('answer')))
print('WROTE', report_path)
print('WROTE', txt_path)
