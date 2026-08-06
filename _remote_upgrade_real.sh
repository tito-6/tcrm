#!/bin/bash
set -euo pipefail
systemctl stop tcrm
sleep 2
export PYTHONPATH=/opt/tcrm/tcrm-src
ADDONS=/opt/tcrm/tcrm-src/tcrm/addons,/opt/tcrm/tcrm-src/addons,/opt/tcrm/custom_addons

echo "Before:"
sudo -u postgres psql -d akod_prod -tAc "SELECT name, latest_version, state FROM ir_module_module WHERE name IN ('meta_leads','tcrm_web_enhance','custom_crm_integration');"
sudo -u postgres psql -d akod_prod -tAc "SELECT count(*) FROM information_schema.columns WHERE table_name='crm_lead' AND column_name='meta_event_id';"

sudo -u tcrm env PYTHONUNBUFFERED=1 PYTHONPATH=/opt/tcrm/tcrm-src \
  /opt/tcrm/venv/bin/python -u /opt/tcrm/tcrm-src/tcrm-bin \
  -c /opt/tcrm/tcrm.prod.conf \
  --addons-path="$ADDONS" \
  -d akod_prod \
  -u meta_leads,custom_crm_integration,tcrm_web_enhance \
  --stop-after-init \
  --log-level=info > /tmp/upgrade_real.log 2>&1
echo upgrade_exit:$?
wc -l /tmp/upgrade_real.log
tail -60 /tmp/upgrade_real.log

# Install modules one by one if needed
for m in board mass_mailing_crm website_mass_mailing hr_timesheet sale_timesheet website_google_map website_links survey_crm; do
  state=$(sudo -u postgres psql -d akod_prod -tAc "SELECT state FROM ir_module_module WHERE name='$m';")
  echo "module $m state=$state"
  if [ "$state" = "uninstalled" ] || [ "$state" = "uninstallable" ] || [ -z "$state" ]; then
    echo "Installing $m..."
    sudo -u tcrm env PYTHONUNBUFFERED=1 PYTHONPATH=/opt/tcrm/tcrm-src \
      /opt/tcrm/venv/bin/python -u /opt/tcrm/tcrm-src/tcrm-bin \
      -c /opt/tcrm/tcrm.prod.conf --addons-path="$ADDONS" \
      -d akod_prod -i "$m" --stop-after-init --log-level=warn \
      > /tmp/install_$m.log 2>&1 || echo "FAIL $m (see /tmp/install_$m.log)"
    tail -5 /tmp/install_$m.log || true
  fi
done

echo "After:"
sudo -u postgres psql -d akod_prod -tAc "SELECT name, latest_version, state FROM ir_module_module WHERE name IN ('meta_leads','tcrm_web_enhance','custom_crm_integration','board','mass_mailing_crm','website_mass_mailing','hr_timesheet','sale_timesheet');"
sudo -u postgres psql -d akod_prod -tAc "SELECT count(*) FROM information_schema.columns WHERE table_name='crm_lead' AND column_name IN ('meta_event_id','meta_date_of_birth','meta_gender');"
sudo -u postgres psql -d akod_prod -tAc "SELECT key, left(value,24) FROM ir_config_parameter WHERE key LIKE 'meta_leads%';"

systemctl start tcrm
sleep 3
systemctl is-active tcrm
echo DONE
