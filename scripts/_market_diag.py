import json
from tcrm.modules.registry import Registry
from tcrm import api, SUPERUSER_ID
reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    src = env['tcrm.market.source'].sudo().search([])
    print('SOURCES', len(src))
    for s in src:
        print(json.dumps({
            'id': s.id, 'name': s.name, 'type': s.source_type, 'state': s.state,
            'scrape_state': s.scrape_state, 'progress': s.scrape_progress,
            'msg': s.scrape_progress_message, 'error': (s.error_log or s.last_error or '')[:300],
            'filters': [s.filter_transaction, s.filter_category, s.filter_province, s.filter_district],
        }, ensure_ascii=False))
    jobs = env['tcrm.market.import.job'].sudo().search([], limit=10, order='id desc')
    print('JOBS', len(jobs))
    for j in jobs:
        print(json.dumps({'id': j.id, 'type': j.job_type, 'state': j.state, 'read': j.count_read, 'created': j.count_created, 'err': (j.error_summary or '')[:250]}, ensure_ascii=False))
    print('LISTINGS', env['tcrm.market.listing'].sudo().search_count([]))
