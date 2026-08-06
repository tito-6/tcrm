#!/bin/bash
set -euo pipefail

echo "=== installed on tcrm_master (custom + website/crm related) ==="
sudo -u postgres psql -d tcrm_master -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE state IN ('installed','to upgrade','to install')
  AND (
    name LIKE 'tcrm_%'
    OR name LIKE 'website%'
    OR name LIKE 'crm%'
    OR name LIKE 'sale%'
    OR name LIKE 'account%'
    OR name LIKE 'hr%'
    OR name LIKE 'mail%'
    OR name LIKE 'mass_mailing%'
    OR name LIKE 'social%'
    OR name LIKE 'utm%'
    OR name LIKE 'phone%'
    OR name LIKE 'calendar%'
    OR name LIKE 'project%'
    OR name LIKE 'board%'
    OR name LIKE 'contacts%'
    OR name LIKE 'base_setup%'
    OR name LIKE 'web_%'
  )
ORDER BY name;
"

echo
echo "=== installed on akod_prod (same filter) ==="
sudo -u postgres psql -d akod_prod -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE state IN ('installed','to upgrade','to install')
  AND (
    name LIKE 'tcrm_%'
    OR name LIKE 'website%'
    OR name LIKE 'crm%'
    OR name LIKE 'sale%'
    OR name LIKE 'account%'
    OR name LIKE 'hr%'
    OR name LIKE 'mail%'
    OR name LIKE 'mass_mailing%'
    OR name LIKE 'social%'
    OR name LIKE 'utm%'
    OR name LIKE 'phone%'
    OR name LIKE 'calendar%'
    OR name LIKE 'project%'
    OR name LIKE 'board%'
    OR name LIKE 'contacts%'
    OR name LIKE 'base_setup%'
    OR name LIKE 'web_%'
  )
ORDER BY name;
"

echo
echo "=== tcrm_* only: master vs akod ==="
sudo -u postgres psql -d tcrm_master -tAc "SELECT name FROM ir_module_module WHERE state='installed' AND name LIKE 'tcrm_%' ORDER BY 1;" > /tmp/m_tcrm.txt
sudo -u postgres psql -d akod_prod -tAc "SELECT name FROM ir_module_module WHERE state='installed' AND name LIKE 'tcrm_%' ORDER BY 1;" > /tmp/a_tcrm.txt
echo "ONLY ON MASTER:"
comm -23 /tmp/m_tcrm.txt /tmp/a_tcrm.txt
echo "ONLY ON AKOD:"
comm -13 /tmp/m_tcrm.txt /tmp/a_tcrm.txt

echo
echo "=== all installed only on master (not akod) — full list ==="
sudo -u postgres psql -d tcrm_master -tAc "SELECT name FROM ir_module_module WHERE state='installed' ORDER BY 1;" > /tmp/m_all.txt
sudo -u postgres psql -d akod_prod -tAc "SELECT name FROM ir_module_module WHERE state='installed' ORDER BY 1;" > /tmp/a_all.txt
comm -23 /tmp/m_all.txt /tmp/a_all.txt | head -200
echo "(total only-on-master: $(comm -23 /tmp/m_all.txt /tmp/a_all.txt | wc -l))"
