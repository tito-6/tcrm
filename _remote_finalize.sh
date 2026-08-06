#!/bin/bash
set -euxo pipefail
chown tcrm:tcrm /opt/tcrm/custom_addons/meta_leads/models/crm_lead.py
systemctl restart tcrm
sleep 4
systemctl is-active tcrm
systemctl is-active akod-api
sudo -u postgres psql -d akod_prod -c "UPDATE crm_lead SET active=false WHERE id=23 AND email_from LIKE 'emq.coverage.%';"
# Ensure description file still present
test -f /opt/tcrm/custom_addons/meta_leads/static/description/index.html
# Confirm action_set_won in deployed file
grep -n 'action_set_won\|became_hot' /opt/tcrm/custom_addons/meta_leads/models/crm_lead.py | head
# Confirm akod patch
grep -n 'Do not invent fbp\|fbp: payload.fbp\|eventId: event_id' /var/www/akod/app/dist/server/pages/api/lead.astro.mjs | head
echo DONE
'