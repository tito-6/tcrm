#!/usr/bin/env bash
echo "=== recent errors (tcrm_web_enhance / docs) ==="
grep -iE 'tcrm_web_enhance|docs_|ParseError|CRITICAL|Traceback|help_links|website_branding|Failed to (load|init)' /opt/tcrm/tcrm_data/tcrm.log | tail -50
echo "=== docs templates in db ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT key FROM ir_ui_view WHERE key LIKE 'tcrm_web_enhance.%' ORDER BY key;"
echo "=== module state ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT name||' | '||state||' | '||coalesce(latest_version,'?') FROM ir_module_module WHERE name IN ('tcrm_web_enhance','tcrm_call_center','tcrm_saas_core');"
echo "=== /docs direct render ==="
curl -s http://127.0.0.1:8069/docs | head -c 400
echo ""
echo "=== controller registered? (grep routing) ==="
grep -iE "GET /docs|/docs HTTP" /opt/tcrm/tcrm_data/tcrm.log | tail -5
