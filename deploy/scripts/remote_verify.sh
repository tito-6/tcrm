#!/usr/bin/env bash
set -euo pipefail
ufw delete allow 8080/tcp || true
ufw delete allow 11434/tcp || true
ufw delete allow 8000/tcp || true
ufw status
systemctl is-active tcrm nginx postgresql
echo '--- HTTP redirect ---'
curl -sI http://tcrm.online/web/login | head -8
echo '--- HTTPS ---'
curl -sI https://tcrm.online/web/login | head -8
echo '--- WWW ---'
curl -sI https://www.tcrm.online/web/login | head -8
echo '--- module ---'
sudo -u postgres psql -d tcrm_master -c "SELECT name,state FROM ir_module_module WHERE name='tcrm_call_center';"
echo '--- santral config ---'
sudo -u postgres psql -d tcrm_master -c "SELECT enabled, is_configured, (account_sid IS NOT NULL) AS has_sid, (api_key_secret_encrypted LIKE 'enc:v1:%') AS enc_ok FROM tcrm_call_provider_config LIMIT 5;"
echo '--- webhook routes ---'
curl -s -o /dev/null -w 'status=%{http_code}\n' -X POST https://tcrm.online/tcrm/twilio/call/status
curl -s -o /dev/null -w 'outgoing=%{http_code}\n' -X POST https://tcrm.online/tcrm/twilio/voice/outgoing
curl -s -o /dev/null -w 'recording=%{http_code}\n' https://tcrm.online/tcrm/call/recording/1
echo DONE
