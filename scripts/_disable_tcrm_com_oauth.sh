#!/bin/bash
set -euo pipefail
export HOME=/opt/tcrm
export PYTHONPATH=/opt/tcrm/tcrm-src
cd /opt/tcrm

echo "=== Disable Tcrm.com OAuth on all product DBs ==="
for DB in tcrm_master akod_prod perla_villalari; do
  if sudo -u postgres psql -d "$DB" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='auth_oauth_provider'" | grep -q 1; then
    sudo -u postgres psql -d "$DB" -c "
      UPDATE auth_oauth_provider
         SET enabled = false
       WHERE enabled IS TRUE
         AND (
              name ILIKE '%Tcrm.com%'
           OR auth_endpoint ILIKE '%accounts.tcrm.com%'
           OR css_class ILIKE '%o_tcrm_provider%'
         );
    "
    echo "DB $DB: oauth providers after update:"
    sudo -u postgres psql -d "$DB" -c "SELECT id, name, enabled FROM auth_oauth_provider ORDER BY id;"
  else
    echo "DB $DB: no auth_oauth_provider table"
  fi
done

echo "=== Upgrade tcrm_web_enhance on product DBs ==="
systemctl stop tcrm
sleep 2
for DB in tcrm_master akod_prod perla_villalari; do
  echo "--- upgrading $DB ---"
  sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src \
    /opt/tcrm/venv/bin/python -m tcrm \
    -c /opt/tcrm/tcrm.prod.conf -d "$DB" -u tcrm_web_enhance --stop-after-init \
    > /tmp/upgrade_web_enhance_${DB}.log 2>&1 || {
      echo "WARN upgrade failed on $DB";
      tail -40 /tmp/upgrade_web_enhance_${DB}.log;
    }
done
systemctl start tcrm
sleep 4
systemctl is-active tcrm
echo DONE
