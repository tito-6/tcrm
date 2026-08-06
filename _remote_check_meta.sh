#!/bin/bash
set -euo pipefail
echo "=== addons_path ==="
grep addons_path /opt/tcrm/tcrm.prod.conf
echo "=== custom-addons on disk ==="
ls /opt/tcrm/custom-addons 2>/dev/null || echo 'no custom-addons'
ls /opt/tcrm/custom_addons | head -40
echo "=== meta_leads / custom_crm on master ==="
sudo -u postgres psql -d tcrm_master -tAc "SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('meta_leads','custom_crm_integration','tcrm_call_center','tcrm_marketing_hub') ORDER BY 1;"
echo "=== meta_leads / custom_crm on akod ==="
sudo -u postgres psql -d akod_prod -tAc "SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('meta_leads','custom_crm_integration','tcrm_call_center','tcrm_marketing_hub') ORDER BY 1;"
echo "=== pixel config akod ==="
sudo -u postgres psql -d akod_prod -tAc "SELECT key, left(value,40) FROM ir_config_parameter WHERE key ILIKE '%meta%' OR key ILIKE '%pixel%' ORDER BY 1;"
echo "=== pixel config master ==="
sudo -u postgres psql -d tcrm_master -tAc "SELECT key, left(value,40) FROM ir_config_parameter WHERE key ILIKE '%meta%' OR key ILIKE '%pixel%' ORDER BY 1;"
echo "=== modules to install candidates (free useful ones missing on akod) ==="
comm -23 /tmp/m_all.txt /tmp/a_all.txt
