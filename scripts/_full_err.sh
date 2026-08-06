#!/usr/bin/env bash
echo "=== full parse error context ==="
grep -n "ParseError\|website_branding\|Element.*cannot\|xpath\|can not be located\|Invalid" /opt/tcrm/tcrm_data/tcrm.log | tail -30
echo "=== run upgrade in foreground to see exact error ==="
export PYTHONPATH=/opt/tcrm/tcrm-src
sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm \
  -c /opt/tcrm/tcrm.prod.conf -d tcrm_master -u tcrm_web_enhance --stop-after-init --log-level=error 2>&1 | grep -iE "ParseError|Element|xpath|locate|website_branding|Error|Invalid" | head -40
