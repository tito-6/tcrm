#!/bin/bash
set -euxo pipefail
export HOME=/var/lib/tcrm
export PYTHONUNBUFFERED=1
LOG=/tmp/upgrade_nohup.log
exec >"$LOG" 2>&1

echo "=== START $(date -Is) ==="
systemctl stop tcrm || true
sleep 2

ADDONS="/opt/tcrm/tcrm-src/addons,/opt/tcrm/custom_addons"
BIN=/opt/tcrm/tcrm-src/tcrm-bin
PY=/opt/tcrm/venv/bin/python
CFG=/opt/tcrm/tcrm.prod.conf
DB=akod_prod

# Syntax check new Python files
$PY -c "
import ast
for p in [
  '/opt/tcrm/custom_addons/meta_leads/services/meta_capi_service.py',
  '/opt/tcrm/custom_addons/meta_leads/services/meta_capi_helpers.py',
  '/opt/tcrm/custom_addons/meta_leads/models/crm_lead.py',
  '/opt/tcrm/custom_addons/custom_crm_integration/controllers/webhook.py',
  '/opt/tcrm/custom_addons/tcrm_web_enhance/controllers/lead_api.py',
]:
    ast.parse(open(p).read())
    print('syntax ok', p)
"

# Update module versions in DB so -u will reload
sudo -u postgres psql -d "$DB" -c "UPDATE ir_module_module SET latest_version='19.0.1.0.2' WHERE name='meta_leads';"
sudo -u postgres psql -d "$DB" -c "UPDATE ir_module_module SET latest_version='19.0.1.1.9' WHERE name='tcrm_web_enhance';"

# Add columns if missing (safe bootstrap so runtime works even if -u flaky)
sudo -u postgres psql -d "$DB" <<'SQL'
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS meta_event_id varchar;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS meta_date_of_birth date;
ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS meta_gender varchar;
SQL

# Install free modules that exist and are not installed
sudo -u postgres psql -d "$DB" -tAc "
SELECT name FROM ir_module_module
WHERE state='uninstalled'
  AND name IN (
    'board','mass_mailing_crm','website_mass_mailing','hr_timesheet','sale_timesheet',
    'calendar','contacts','crm_iap_enrich','crm_iap_mine','iap_crm','link_tracker',
    'marketing_card','mass_mailing','mass_mailing_sms','sms','phone_validation',
    'website_crm','website_crm_sms','website_sale','payment','account','sale_management',
    'crm_enterprise','knowledge','sign','documents','project','hr','hr_recruitment',
    'website_blog','website_event','website_forum','website_slides','im_livechat',
    'helpdesk','social','social_facebook','social_linkedin','social_twitter','social_youtube',
    'social_instagram','social_push_notifications','utm','survey','event','event_sale',
    'appointment','website_appointment','quality_control','maintenance','fleet','lunch',
    'approvals','planning','timesheet_grid','industry_fsm','worksheet'
  );
" | tr -d ' ' | grep -v '^$' > /tmp/to_install.txt || true
echo "Candidates:"; cat /tmp/to_install.txt || true

# Filter to modules that actually exist on disk
> /tmp/install_ok.txt
while read -r m; do
  [ -z "$m" ] && continue
  if [ -d "/opt/tcrm/tcrm-src/addons/$m" ] || [ -d "/opt/tcrm/custom_addons/$m" ]; then
    echo "$m" >> /tmp/install_ok.txt
  else
    echo "skip missing on disk: $m"
  fi
done < /tmp/to_install.txt
echo "Will install:"; cat /tmp/install_ok.txt || true

INSTALL_LIST=$(tr '\n' ',' < /tmp/install_ok.txt | sed 's/,$//')

# Run upgrade of our modules first
echo "=== UPGRADE custom modules ==="
sudo -u tcrm $PY $BIN -c $CFG -d $DB \
  --addons-path="$ADDONS" \
  --stop-after-init \
  -u meta_leads,custom_crm_integration,tcrm_web_enhance \
  --log-level=info
echo "upgrade exit=$?"

if [ -n "${INSTALL_LIST:-}" ]; then
  echo "=== INSTALL $INSTALL_LIST ==="
  sudo -u tcrm $PY $BIN -c $CFG -d $DB \
    --addons-path="$ADDONS" \
    --stop-after-init \
    -i "$INSTALL_LIST" \
    --log-level=info || echo "install exit=$?"
fi

# Verify
echo "=== VERIFY ==="
sudo -u postgres psql -d "$DB" -c "
SELECT name, latest_version, state FROM ir_module_module
WHERE name IN ('meta_leads','custom_crm_integration','tcrm_web_enhance','tcrm_call_center','tcrm_marketing_hub','board','mass_mailing_crm','website_mass_mailing','hr_timesheet','sale_timesheet')
ORDER BY name;
"
sudo -u postgres psql -d "$DB" -c "
SELECT column_name FROM information_schema.columns
WHERE table_name='crm_lead' AND column_name LIKE 'meta_%' ORDER BY 1;
"
sudo -u postgres psql -d "$DB" -c "
SELECT key, CASE WHEN value IS NULL OR value='' THEN 'EMPTY' ELSE 'SET' END
FROM ir_config_parameter
WHERE key IN ('meta_leads.pixel_id','meta_leads.access_token','custom_crm_integration.meta_user_access_token')
ORDER BY 1;
"

systemctl start tcrm
sleep 4
systemctl is-active tcrm
echo "=== DONE $(date -Is) ==="
'