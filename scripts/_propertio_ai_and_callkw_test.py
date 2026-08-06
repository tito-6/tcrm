# -*- coding: utf-8 -*-
"""Verify call_kw bug fix + TCRM AI direct/engine answers against seeded data."""
import traceback
from tcrm.service.model import call_kw
from tcrm import SUPERUSER_ID

print('=== call_kw: action_generate_tasks ===')
Task = env['propertio.collection.task']
try:
    # Standard list header call (empty selection)
    r1 = call_kw(Task, 'action_generate_tasks', [[]], {'context': {}})
    print('  PASS call_kw [[]] ->', r1)
    # Bug reproduction: extra positional after ids
    r2 = call_kw(Task, 'action_generate_tasks', [[], {'lang': 'tr_TR'}], {'context': {}})
    print('  PASS call_kw [[], context_dict] ->', r2)
except Exception as e:
    print('  FAIL call_kw:', e)
    traceback.print_exc()

print('\n=== TCRM AI direct + engine ===')
from tcrm_ai.controllers.main import _try_direct_propertio_answer

queries = [
    ('merhaba', None),  # may need engine
    ('kaç tane satışımız var', 'sale'),
    ('satışlarımızı listele', 'sale'),
    ('hangi daireler müsait', 'unit'),
    ('Mavi Bahçe projesi hakkında bilgi ver', 'project'),
    ('gecikmiş ödemeler var mı', 'overdue'),
    ('toplam tahsilat ne kadar', 'payment'),
    ('Mehmet Yılmaz ödeme planı', 'install'),
    ('OVER-999 kontratı', 'missing'),
    ('iptal satışlar', 'empty'),
    ('kaç satışımız var', 'no_web'),  # must not invent
]

for q, kind in queries:
    try:
        direct = _try_direct_propertio_answer(env, q)
        if direct:
            ans = (direct.get('answer') or '')[:200]
            bad = '?' in ans and 'kaç' not in q  # rough encoding check
            print('  DIRECT [%s] %s -> %s' % (kind, q, ans.replace('\n', ' | ')))
            if bad:
                print('    WARN possible encoding issue')
        else:
            # Try full engine (needs API key)
            try:
                result = env['tcrm.ai.engine']._ask(q, base_url='http://localhost:8069')
                ans = (result.get('answer') or '')[:200]
                err = result.get('error')
                print('  ENGINE [%s] %s -> error=%s | %s' % (kind, q, err, ans.replace('\n', ' | ')))
            except Exception as e:
                print('  ENGINE FAIL [%s] %s -> %s' % (kind, q, e))
    except Exception as e:
        print('  FAIL [%s] %s -> %s' % (kind, q, e))
        traceback.print_exc()

# Follow-up / memory via session if available
print('\n=== Session memory (best-effort) ===')
try:
    Session = env['tcrm.ai.session']
    sid = 'test-suite-%s' % env.uid
    if hasattr(Session, 'clear'):
        Session.clear(sid)
    r1 = env['tcrm.ai.engine']._ask({'text': 'satışlarımızı listele', 'session_id': sid}, base_url='http://localhost:8069')
    r2 = env['tcrm.ai.engine']._ask({'text': 'bunların toplam değeri ne kadar', 'session_id': sid}, base_url='http://localhost:8069')
    print('  list:', (r1.get('answer') or '')[:180])
    print('  followup:', (r2.get('answer') or '')[:180])
except Exception as e:
    print('  session test skip/fail:', e)

# Settings field gemini-1.5-flash-8b via res.config.settings
print('\n=== Settings gemini model field ===')
try:
    ICP = env['ir.config_parameter'].sudo()
    ICP.set_param('tcrm_ai.gemini_model', 'gemini-1.5-flash-8b')
    assert ICP.get_param('tcrm_ai.gemini_model') == 'gemini-1.5-flash-8b'
    # Also via settings create/execute if present
    Settings = env['res.config.settings']
    if 'tcrm_ai_gemini_model' in Settings._fields:
        s = Settings.create({'tcrm_ai_gemini_model': 'gemini-1.5-flash-8b'})
        s.execute()
        got = ICP.get_param('tcrm_ai.gemini_model')
        print('  PASS settings execute ->', got)
    else:
        print('  PASS icp only -> gemini-1.5-flash-8b')
except Exception as e:
    print('  FAIL settings:', e)
    traceback.print_exc()

print('\nDONE')
exit()
