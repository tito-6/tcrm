#!/bin/bash
set -euxo pipefail
echo "=== COLUMNS ==="
sudo -u postgres psql -d akod_prod -c "SELECT column_name FROM information_schema.columns WHERE table_name='crm_lead' AND column_name LIKE 'meta_%' ORDER BY 1;"

echo "=== MODULE GAP (installed on master, not on akod) ==="
sudo -u postgres psql -d tcrm_master -tAc "SELECT name FROM ir_module_module WHERE state='installed' ORDER BY 1;" > /tmp/m_master.txt
sudo -u postgres psql -d akod_prod -tAc "SELECT name FROM ir_module_module WHERE state='installed' ORDER BY 1;" > /tmp/m_akod.txt
comm -23 /tmp/m_master.txt /tmp/m_akod.txt | tee /tmp/m_gap.txt | wc -l
echo "sample gap:"
head -60 /tmp/m_gap.txt

echo "=== PARAMS ==="
sudo -u postgres psql -d akod_prod -c "SELECT key, CASE WHEN value IS NULL OR value='' THEN 'EMPTY' ELSE 'SET' END FROM ir_config_parameter WHERE key IN ('meta_leads.pixel_id','meta_leads.access_token','meta_leads.test_event_code','tcrm_web_enhance.akod_lead_api_key','custom_crm_integration.akod_webhook_secret') OR key ILIKE '%lead%api%' OR key ILIKE '%akod%' ORDER BY 1;"

echo "=== DRY-RUN CAPI PAYLOAD (no Graph send) ==="
sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm shell -c /opt/tcrm/tcrm.prod.conf -d akod_prod <<'PY'
from tcrm.addons.meta_leads.services.meta_capi_helpers import get_capi_credentials, build_fbc
from tcrm.addons.meta_leads.services.meta_capi_service import MetaCAPIService
pix, tok = get_capi_credentials(env)
print('creds_ok', bool(pix), bool(tok), 'pixel', pix)
Lead = env['crm.lead']
needed = ['meta_fbc','meta_fbp','meta_client_ip','meta_event_id','meta_date_of_birth','meta_gender','meta_capi_lead_event_sent','meta_capi_purchase_event_sent']
print('fields_ok', {f: f in Lead._fields for f in needed})
# Use newest real lead if any, else skip send
lead = Lead.search([], order='id desc', limit=1)
print('latest_lead', lead.id if lead else None, getattr(lead, 'email_from', None) if lead else None)
if lead:
    # Build event payload without sending
    class _Tmp: pass
    # clone tracking onto a newrecord-like browse by writing to a copy in memory via service helpers
    svc = MetaCAPIService(pix, tok)
    # temporarily ensure match fields if missing — DO NOT invent; only show what would send
    ud = svc._build_user_data(lead)
    print('user_data_keys', sorted(ud.keys()))
    print('has_fbc', 'fbc' in ud, 'has_fbp', 'fbp' in ud, 'has_ip', 'client_ip_address' in ud, 'has_em', 'em' in ud, 'has_ph', 'ph' in ud, 'has_external_id', 'external_id' in ud)
    # Verify token against Graph (no event)
    try:
        v = svc.verify_credentials()
        print('graph_verify', v)
    except Exception as e:
        print('graph_verify_error', e)
PY

echo "=== HTTP API smoke (match params) ==="
# Discover API key if set
KEY=$(sudo -u postgres psql -d akod_prod -tAc "SELECT value FROM ir_config_parameter WHERE key IN ('tcrm_web_enhance.akod_lead_api_key','akod.lead_api_key') LIMIT 1;" | tr -d ' ')
echo "api_key_set=$( [ -n \"$KEY\" ] && echo yes || echo no )"
'