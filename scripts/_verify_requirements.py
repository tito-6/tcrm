# -*- coding: utf-8 -*-
"""JSON-RPC verification of the TCRM requirements."""
import json
import sys
import urllib.request
import http.cookiejar

BASE = 'http://127.0.0.1:8069'
DB = 'tcrm_master'
USER = 'admin'
PASS = 'admin'

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def rpc(url, params):
    data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params, 'id': 1}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with opener.open(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get('error'):
        raise RuntimeError(json.dumps(payload['error'].get('data', payload['error']), ensure_ascii=False)[:800])
    return payload.get('result')


def call_kw(model, method, args=None, kwargs=None):
    return rpc(f'{BASE}/web/dataset/call_kw', {
        'model': model,
        'method': method,
        'args': args or [],
        'kwargs': kwargs or {},
    })


def xmlid_id(xmlid):
    module, name = xmlid.split('.', 1)
    rows = call_kw('ir.model.data', 'search_read', [[
        ('module', '=', module), ('name', '=', name),
    ]], {'fields': ['res_id', 'model'], 'limit': 1})
    if not rows:
        raise RuntimeError(f'missing xmlid {xmlid}')
    return rows[0]['res_id']


def main():
    fails = []
    auth = rpc(f'{BASE}/web/session/authenticate', {'db': DB, 'login': USER, 'password': PASS})
    assert auth and auth.get('uid'), 'auth failed'
    print('OK auth uid=', auth['uid'])

    menu_id = xmlid_id('tcrm_propertio.menu_propertio_inventory')
    name = call_kw('ir.ui.menu', 'read', [[menu_id], ['name']], {'context': {'lang': 'tr_TR'}})[0]['name']
    if name != 'Proje Stok ve Takibi':
        fails.append(f'inventory menu={name!r}')
    else:
        print('OK inventory menu', name)

    types = call_kw('propertio.project.type', 'search_read', [[]], {'fields': ['name', 'code'], 'limit': 80})
    stages = call_kw('propertio.project.stage', 'search_read', [[]], {'fields': ['name', 'code', 'fold'], 'limit': 80})
    type_names = {t['name'] for t in types}
    stage_names = {s['name'] for s in stages}
    needed_types = {
        'Konut Projesi', 'Villa Projesi', 'Ticari Dükkan Projesi', 'Karma Proje',
        'Devremülk Projesi', 'Arsa ve Parsel Projesi', 'Kentsel Dönüşüm Projesi',
        'Rezidans Projesi', 'Ofis Projesi', 'Sanayi veya Depo Projesi',
    }
    needed_stages = {
        'Planlama', 'Ruhsat Süreci', 'Projelendirme', 'Satışa Hazır', 'Ön Satışta',
        'İnşaat Başladı', 'İnşaat Devam Ediyor', 'Teslime Hazır', 'Teslim Edildi',
        'Tamamlandı', 'Durduruldu', 'İptal Edildi',
    }
    if not needed_types.issubset(type_names):
        fails.append(f'missing types {needed_types - type_names}')
    else:
        print('OK project types', len(needed_types))
    if not needed_stages.issubset(stage_names):
        fails.append(f'missing stages {needed_stages - stage_names}')
    else:
        print('OK project stages', len(needed_stages))

    projects = call_kw('propertio.project', 'search_count', [[]])
    units = call_kw('propertio.unit', 'search_count', [[]])
    if projects < 10:
        fails.append(f'projects={projects}')
    else:
        print('OK projects', projects, 'units', units)

    action_id = xmlid_id('tcrm_propertio.action_lead_havuzu')
    action = call_kw('ir.actions.act_window', 'read', [[action_id], ['name', 'domain', 'res_model']])[0]
    if action['name'] != 'Lead Havuzu' or action['res_model'] != 'crm.lead':
        fails.append(f'lead havuzu action {action}')
    else:
        print('OK Lead Havuzu action')

    old_leads = call_kw('ir.ui.menu', 'read', [[xmlid_id('crm.crm_menu_leads')], ['active', 'name']])[0]
    old_pipe = call_kw('ir.ui.menu', 'read', [[xmlid_id('crm.menu_crm_opportunities')], ['active', 'name']])[0]
    if old_leads.get('active') or old_pipe.get('active'):
        fails.append(f'old menus still active leads={old_leads} pipe={old_pipe}')
    else:
        print('OK obsolete menus inactive')

    views = call_kw('ir.ui.view', 'search_read', [[
        ('name', 'ilike', 'hide.ai.probability'),
    ]], {'fields': ['arch_db', 'name'], 'limit': 5})
    if not views:
        fails.append('missing hide ai probability view')
    else:
        print('OK AI probability hide view')

    fields_info = call_kw(
        'mail.activity.schedule', 'fields_get', [['create_reminder']],
        {'context': {'lang': 'tr_TR'}},
    )
    if fields_info.get('create_reminder', {}).get('string') != 'Hatırlatıcı oluştur':
        fails.append(f'reminder field {fields_info}')
    else:
        print('OK Hatırlatıcı oluştur field')

    catalog = call_kw('propertio.report.engine', 'list_reports', [])
    nums = sorted({r['category_number'] for r in catalog['reports'] if r.get('category_number')})
    if nums != list(range(1, len(nums) + 1)):
        fails.append(f'report numbers {nums}')
    else:
        print('OK report category numbers', nums)
    bad_label = False
    for r in catalog['reports']:
        label = r.get('category_label') or ''
        n = r.get('category_number')
        if not label.startswith(f'{n}. '):
            fails.append(f'bad category_label {label}')
            bad_label = True
            break
    if not bad_label:
        print('OK category labels prefixed')

    pages = call_kw('tcrm.marketing.hub', 'get_page_management', [])
    blob = json.dumps(pages)
    leaked = [s for s in ('api_key', 'access_token', 'Authorization', 'Bearer ') if s in blob]
    if leaked:
        fails.append(f'token leaked: {leaked}')
    else:
        print('OK page management no secrets keys=', list(pages.keys()) if isinstance(pages, dict) else type(pages))

    lead_fields = call_kw('crm.lead', 'fields_get', [[
        'mh_source_platform', 'mh_leadgen_id', 'mh_creative_html', 'marketing_has_meta_lead',
    ]])
    missing = [f for f in ('mh_source_platform', 'mh_leadgen_id', 'mh_creative_html') if f not in lead_fields]
    if missing:
        fails.append(f'missing lead fields {missing}')
    else:
        print('OK marketing source/creative fields on crm.lead')

    # Reminder smoke: schedule activity with reminder
    lead_ids = call_kw('crm.lead', 'search', [[('type', '=', 'opportunity')]], {'limit': 1})
    if lead_ids:
        type_id = xmlid_id('mail.mail_activity_data_call')
        wiz = call_kw('mail.activity.schedule', 'create', [{
            'res_model': 'crm.lead',
            'res_ids': str(lead_ids),
            'activity_type_id': type_id,
            'summary': 'Verify reminder',
            'date_deadline': '2026-07-30',
            'activity_user_id': auth['uid'],
            'create_reminder': True,
        }], {'context': {'active_model': 'crm.lead', 'active_id': lead_ids[0], 'active_ids': lead_ids}})
        call_kw('mail.activity.schedule', 'action_schedule_activities', [[wiz]])
        acts = call_kw('mail.activity', 'search_read', [[
            ('res_model', '=', 'crm.lead'), ('res_id', '=', lead_ids[0]), ('summary', '=', 'Verify reminder'),
        ]], {'fields': ['todo_task_id', 'reminder_calendar_event_id', 'calendar_event_id'], 'limit': 1})
        if not acts or not acts[0].get('todo_task_id'):
            fails.append(f'reminder todo missing {acts}')
        else:
            print('OK reminder created todo=', acts[0]['todo_task_id'], 'cal=', acts[0].get('reminder_calendar_event_id') or acts[0].get('calendar_event_id'))

    # HTTP route smoke (authenticated session cookie already set)
    for route in ('/web', '/tcrm/crm'):
        req = urllib.request.Request(f'{BASE}{route}')
        with opener.open(req, timeout=30) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
            if resp.status != 200:
                fails.append(f'route {route} status {resp.status}')
            elif 'oe_login_form' in body and route != '/web/login':
                fails.append(f'route {route} login redirect')
            elif 'Internal Server Error' in body or 'Traceback' in body:
                fails.append(f'route {route} server error')
            else:
                print('OK route', route, 'HTTP', resp.status)

    if fails:
        print('FAILS:')
        for f in fails:
            print(' -', f)
        sys.exit(1)
    print('ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
