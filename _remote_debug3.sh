#!/bin/bash
systemctl stop tcrm || true
sleep 1
export PYTHONPATH=/opt/tcrm/tcrm-src
wc -l /tmp/upgrade_debug.txt /tmp/import_test.txt 2>/dev/null || true
# Syntax check our new files
sudo -u tcrm bash -lc 'export PYTHONPATH=/opt/tcrm/tcrm-src
/opt/tcrm/venv/bin/python - <<PY
import ast, pathlib, traceback
files = [
 "/opt/tcrm/custom_addons/meta_leads/services/meta_capi_helpers.py",
 "/opt/tcrm/custom_addons/meta_leads/services/meta_capi_service.py",
 "/opt/tcrm/custom_addons/meta_leads/models/crm_lead.py",
 "/opt/tcrm/custom_addons/custom_crm_integration/controllers/webhook.py",
 "/opt/tcrm/custom_addons/tcrm_web_enhance/controllers/lead_api.py",
]
for f in files:
    try:
        ast.parse(pathlib.Path(f).read_text())
        print("OK", f)
    except Exception as e:
        print("FAIL", f, e)
PY
'

echo "==== try odoo shell style ===="
# Use PYTHONUNBUFFERED and redirect via script
sudo -u tcrm env PYTHONUNBUFFERED=1 PYTHONPATH=/opt/tcrm/tcrm-src \
  /opt/tcrm/venv/bin/python -u /opt/tcrm/tcrm-src/tcrm-bin \
  -c /opt/tcrm/tcrm.prod.conf --addons-path=/opt/tcrm/tcrm-src/tcrm/addons,/opt/tcrm/tcrm-src/addons,/opt/tcrm/custom_addons \
  -d akod_prod -u meta_leads --stop-after-init --log-handler=tcrm:DEBUG 2>&1 | head -200
echo EXIT:$?
systemctl start tcrm
