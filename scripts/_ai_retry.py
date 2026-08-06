# -*- coding: utf-8 -*-
import traceback
from tcrm.service.model import call_kw

print('=== Reset AI cooldowns ===')
keys = env['tcrm.ai.key'].sudo().search([])
print('  keys:', len(keys), [(k.id, k.status, k.cooldown_until) for k in keys])
if hasattr(keys, 'reset_cooldowns'):
    keys.reset_cooldowns()
else:
    keys.write({'status': 'active', 'cooldown_until': False})
env.cr.commit()
print('  reset done')

print('\n=== Invoke DB tools via engine helpers ===')
Engine = env['tcrm.ai.engine']
# Discover tool functions on engine by reading _get_tools or similar
tool_attrs = [a for a in dir(Engine) if 'tool' in a.lower() or a.startswith('_search') or a.startswith('_get_')]
print('  tool-ish attrs:', tool_attrs[:40])

# Direct ORM ground-truth answers the AI should produce
sale_n = env['propertio.sale'].search_count([('state', '=', 'confirmed')])
avail = env['propertio.unit'].search([('state', '=', 'available')]).mapped('name')
overdue = env['propertio.installment'].search([('is_paid', '=', False), ('overdue_days', '>', 0)])
paid = sum(env['propertio.payment'].search([('state', '=', 'posted')]).mapped('amount'))
mehmet = env['propertio.sale'].search([('partner_id.name', 'ilike', 'Mehmet Yilmaz')], limit=1)
if not mehmet:
    mehmet = env['propertio.sale'].search([('partner_id.name', 'ilike', 'Mehmet')], limit=1)
inst = env['propertio.installment'].search([('sale_id', '=', mehmet.id)]) if mehmet else env['propertio.installment']
print('  confirmed_sales=', sale_n)
print('  available_units=', avail)
print('  overdue_count=', len(overdue), 'days=', overdue.mapped('overdue_days')[:5])
print('  total_posted_payments=', paid)
print('  mehmet_sale=', mehmet.name if mehmet else None, 'installments=', len(inst))

# Try calling internal tool methods if exposed
for meth_name in (
    '_tool_list_sales', '_tool_search_sales', 'list_sales',
    '_propertio_list_sales', '_tool_get_payment_plan',
):
    if hasattr(Engine, meth_name):
        print('  found', meth_name)

# Inspect tools map builder
for meth_name in dir(Engine):
    if 'tools' in meth_name.lower() or meth_name in ('_build_tools', '_get_tools_map', '_make_tools'):
        print('  method', meth_name)

# Read source of _ask for tools_map construction - call private builder if any
if hasattr(Engine, '_get_tools'):
    try:
        tools = Engine._get_tools()
        print('  _get_tools keys:', list(tools.keys())[:30] if isinstance(tools, dict) else type(tools))
    except TypeError as e:
        print('  _get_tools needs args', e)

print('\n=== AI ask after cooldown reset (short) ===')
for q in ['merhaba', 'kac tane satimiz var', 'hangi daireler musait']:
    try:
        # Use ASCII-normalized queries to avoid console encoding; engine handles Turkish too
        result = Engine._ask(q, base_url='http://localhost:8069')
        print('  Q:', q, '| err=', result.get('error'), '|', (result.get('answer') or '')[:180].replace('\n',' '))
    except Exception as e:
        print('  FAIL', q, e)

# Specific Turkish via unicode escapes
q_tr = 'ka\u00e7 tane sat\u0131\u015f\u0131m\u0131z var'
result = Engine._ask(q_tr, base_url='http://localhost:8069')
print('  Q_TR:', q_tr, '| err=', result.get('error'), '|', (result.get('answer') or '')[:220].replace('\n',' '))

print('\nDONE')
exit()