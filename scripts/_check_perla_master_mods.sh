#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
echo "=== installed saas/master-ish modules on perla_villalari ==="
sudo -u postgres psql -d perla_villalari -Atc \
  "SELECT name || '|' || state || '|' || COALESCE(latest_version,'') FROM ir_module_module WHERE state IN ('installed','to upgrade','to remove') AND (name ILIKE '%saas%' OR name ILIKE '%tcrm_master%' OR name ILIKE '%command_center%' OR name ILIKE '%tcrm_saas%' OR name = 'tcrm_saas_core' OR name ILIKE '%routing%') ORDER BY name;"

echo "=== menus mentioning Master/Command ==="
sudo -u postgres psql -d perla_villalari -Atc \
  "SELECT m.id || '|' || m.name || '|' || COALESCE(m.complete_name,'') || '|' || m.active FROM ir_ui_menu m WHERE m.name ILIKE '%master%' OR m.name ILIKE '%command%' OR m.complete_name ILIKE '%TCRM Master%' OR m.complete_name ILIKE '%Command%' ORDER BY m.complete_name LIMIT 40;"
