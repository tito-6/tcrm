#!/bin/bash
set -euo pipefail

ROOT=/opt/tcrm
PY=$ROOT/venv/bin/python
CONF=$ROOT/tcrm.prod.conf
export PYTHONPATH=$ROOT/tcrm-src

echo "=== 1) Copy Meta pixel credentials master → akod_prod ==="
PIXEL=$(sudo -u postgres psql -d tcrm_master -tAc "SELECT value FROM ir_config_parameter WHERE key='meta_leads.pixel_id' LIMIT 1;")
TOKEN=$(sudo -u postgres psql -d tcrm_master -tAc "SELECT value FROM ir_config_parameter WHERE key='meta_leads.access_token' LIMIT 1;")
TOKEN2=$(sudo -u postgres psql -d tcrm_master -tAc "SELECT value FROM ir_config_parameter WHERE key='custom_crm_integration.meta_user_access_token' LIMIT 1;")
echo "pixel=$PIXEL token_len=${#TOKEN}"

sudo -u postgres psql -d akod_prod <<SQL
INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
VALUES
  ('meta_leads.pixel_id', '${PIXEL}', 1, 1, NOW(), NOW()),
  ('meta_leads.access_token', '${TOKEN}', 1, 1, NOW(), NOW()),
  ('custom_crm_integration.meta_user_access_token', '${TOKEN2:-$TOKEN}', 1, 1, NOW(), NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();
SQL

echo "=== 2) Install free useful modules missing on akod_prod ==="
# Curated: CRM/marketing/HR useful, skip POS/event bloat and saas/mock
MODULES_CSV="board,data_recycle,mass_mailing_crm,mass_mailing_crm_sms,mass_mailing_sale,mass_mailing_sale_sms,mass_mailing_sms,mass_mailing_themes,website_mass_mailing,website_mass_mailing_sms,website_google_map,website_links,website_timesheet,hr_timesheet,hr_timesheet_attendance,hr_hourly_cost,hr_gamification,hr_livechat,hr_skills_survey,sale_timesheet,survey_crm,google_calendar,microsoft_calendar,auth_oauth,stock_sms,project_stock,project_stock_account,project_timesheet_holidays,sale_project_stock,sale_project_stock_account"

systemctl stop tcrm
sleep 2

sudo -u tcrm env PYTHONPATH=$ROOT/tcrm-src "$PY" "$ROOT/tcrm-src/tcrm-bin" \
  -c "$CONF" -d akod_prod -i "$MODULES_CSV" --stop-after-init \
  > /tmp/akod_install_modules.log 2>&1 || {
    echo "INSTALL had errors — showing log tail";
    tail -80 /tmp/akod_install_modules.log;
  }
echo "install log lines: $(wc -l < /tmp/akod_install_modules.log)"
tail -30 /tmp/akod_install_modules.log

echo "=== 3) Upgrade meta_leads + custom_crm_integration + tcrm_web_enhance ==="
sudo -u tcrm env PYTHONPATH=$ROOT/tcrm-src "$PY" "$ROOT/tcrm-src/tcrm-bin" \
  -c "$CONF" -d akod_prod -u meta_leads,custom_crm_integration,tcrm_web_enhance --stop-after-init \
  > /tmp/akod_upgrade_capi.log 2>&1 || {
    echo "UPGRADE FAILED";
    tail -100 /tmp/akod_upgrade_capi.log;
    systemctl start tcrm;
    exit 1;
  }
tail -40 /tmp/akod_upgrade_capi.log

systemctl start tcrm
sleep 4
systemctl is-active tcrm

echo "=== 4) Verify credentials + modules ==="
sudo -u postgres psql -d akod_prod -tAc "SELECT key, left(value,20) FROM ir_config_parameter WHERE key LIKE 'meta_leads%' OR key LIKE 'custom_crm_integration.meta%' ORDER BY 1;"
sudo -u postgres psql -d akod_prod -tAc "SELECT name, state FROM ir_module_module WHERE name IN ('meta_leads','custom_crm_integration','tcrm_call_center','tcrm_marketing_hub','board','mass_mailing_crm','website_mass_mailing','hr_timesheet','sale_timesheet') ORDER BY 1;"

echo "=== 5) Patch akod.tech API to forward fbc/fbp if present ==="
AKOD_API="/var/www/akod/app/dist/server/pages/api/lead.astro.mjs"
if [ -f "$AKOD_API" ]; then
  cp -a "$AKOD_API" "${AKOD_API}.bak.$(date +%Y%m%d%H%M%S)"
  python3 - <<'PY'
from pathlib import Path
p = Path("/var/www/akod/app/dist/server/pages/api/lead.astro.mjs")
src = p.read_text(encoding="utf-8")
needle = "utm_campaign: payload.utm_campaign || \"\""
inject = '''utm_campaign: payload.utm_campaign || "",
      fbc: payload.fbc || payload.meta_fbc || "",
      fbp: payload.fbp || payload.meta_fbp || "",
      fbclid: payload.fbclid || "",
      event_id: payload.event_id || payload.eventId || "",
      client_ip: payload.client_ip || payload.clientIp || "",
      client_user_agent: payload.client_user_agent || payload.userAgent || "",
      page_url: payload.page_url || payload.pageUrl || payload.website || "https://akod.tech",
      city: payload.city || "",
      zip: payload.zip || payload.postcode || "",
      country: payload.country || ""'''
if "fbc: payload.fbc" not in src and needle in src:
    src = src.replace(needle, inject, 1)
    p.write_text(src, encoding="utf-8")
    print("patched akod API lead payload")
else:
    print("akod API already patched or needle missing")
PY
  # restart akod node if systemd unit exists
  systemctl restart akod 2>/dev/null || systemctl restart akod-tech 2>/dev/null || true
else
  echo "akod API file not found at $AKOD_API — skip site patch"
fi

echo "DONE"
