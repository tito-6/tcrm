#!/bin/bash
set -euxo pipefail
cd /opt/tcrm
export HOME=/opt/tcrm
export PYTHONPATH=/opt/tcrm/tcrm-src
export PYTHONUNBUFFERED=1

LOG=/opt/tcrm/tcrm_data/tcrm.log
DB=akod_prod

echo "=== FIX DESCRIPTION + UPGRADE $(date -Is) ===" | tee /tmp/capi_fix.log

# Minimal module description so Odoo _check() does not choke
mkdir -p /opt/tcrm/custom_addons/meta_leads/static/description
cat > /opt/tcrm/custom_addons/meta_leads/static/description/index.html <<'HTML'
<section class="oe_container">
  <div class="oe_row oe_spaced">
    <h2 class="oe_slogan">Meta Leads</h2>
    <p class="oe_mt32">Meta Lead Ads + Conversions API integration for TCRM.</p>
  </div>
</section>
HTML
chown -R tcrm:tcrm /opt/tcrm/custom_addons/meta_leads/static

# Same for other custom modules if missing
for mod in custom_crm_integration tcrm_web_enhance tcrm_call_center tcrm_marketing_hub; do
  dir=/opt/tcrm/custom_addons/$mod/static/description
  if [ -d "/opt/tcrm/custom_addons/$mod" ] && [ ! -f "$dir/index.html" ]; then
    mkdir -p "$dir"
    echo "<section><h2>$mod</h2></section>" > "$dir/index.html"
    chown -R tcrm:tcrm "/opt/tcrm/custom_addons/$mod/static"
  fi
done

# Shorten/clear description in DB to avoid docutils path permission issues as fallback
sudo -u postgres psql -d "$DB" -c "UPDATE ir_module_module SET description='' WHERE name='meta_leads';" || true

systemctl stop tcrm || true
sleep 2

# Bootstrap columns
sudo -u postgres psql -d "$DB" <<'SQL'
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS meta_event_id varchar;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS meta_date_of_birth date;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS meta_gender varchar;
SQL

MARKER="===CAPI_UPGRADE_START $(date -Is)==="
echo "$MARKER" >> "$LOG"

sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src \
  /opt/tcrm/venv/bin/python -m tcrm -c /opt/tcrm/tcrm.prod.conf \
  -d "$DB" --stop-after-init \
  -u meta_leads,custom_crm_integration,tcrm_web_enhance \
  --log-level=info
UP_EC=$?
echo "upgrade_exit=$UP_EC" | tee -a /tmp/capi_fix.log
tail -n 80 "$LOG" | tee -a /tmp/capi_fix.log

# Install free modules present on disk and uninstalled
INSTALL_LIST=$(sudo -u postgres psql -d "$DB" -tAc "
SELECT string_agg(name, ',' ORDER BY name)
FROM ir_module_module
WHERE state='uninstalled'
  AND name IN (
    'board','mass_mailing_crm','website_mass_mailing','hr_timesheet','sale_timesheet',
    'mass_mailing_sms','event_sale','marketing_card'
  );
" | tr -d ' ')

if [ -n "${INSTALL_LIST:-}" ] && [ "$INSTALL_LIST" != "" ]; then
  echo "=== INSTALL $INSTALL_LIST ===" | tee -a /tmp/capi_fix.log
  MARKER2="===FREE_INSTALL_START $(date -Is)==="
  echo "$MARKER2" >> "$LOG"
  sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src \
    /opt/tcrm/venv/bin/python -m tcrm -c /opt/tcrm/tcrm.prod.conf \
    -d "$DB" --stop-after-init \
    -i "$INSTALL_LIST" \
    --log-level=info || echo "install_exit=$?" | tee -a /tmp/capi_fix.log
  tail -n 40 "$LOG" | tee -a /tmp/capi_fix.log
fi

echo "=== VERIFY ===" | tee -a /tmp/capi_fix.log
sudo -u postgres psql -d "$DB" -c "
SELECT name, latest_version, state FROM ir_module_module
WHERE name IN (
  'meta_leads','custom_crm_integration','tcrm_web_enhance','tcrm_call_center','tcrm_marketing_hub',
  'board','mass_mailing_crm','website_mass_mailing','hr_timesheet','sale_timesheet',
  'mass_mailing_sms','event_sale','marketing_card'
) ORDER BY name;
" | tee -a /tmp/capi_fix.log

sudo -u postgres psql -d "$DB" -c "
SELECT column_name FROM information_schema.columns
WHERE table_name='crm_lead' AND column_name IN ('meta_event_id','meta_date_of_birth','meta_gender','meta_fbc','meta_fbp','meta_client_ip_address','meta_client_user_agent')
ORDER BY 1;
" | tee -a /tmp/capi_fix.log

sudo -u postgres psql -d "$DB" -c "
SELECT key, CASE WHEN value IS NULL OR value='' THEN 'EMPTY' ELSE 'SET' END AS status
FROM ir_config_parameter
WHERE key IN ('meta_leads.pixel_id','meta_leads.access_token','custom_crm_integration.meta_user_access_token')
ORDER BY 1;
" | tee -a /tmp/capi_fix.log

systemctl start tcrm
sleep 5
systemctl is-active tcrm | tee -a /tmp/capi_fix.log
echo "=== DONE $(date -Is) ===" | tee -a /tmp/capi_fix.log
'