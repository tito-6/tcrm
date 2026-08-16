#!/usr/bin/env bash
# Deploy Lead Raporu + marketing automation to production tenant DBs.
set -euo pipefail

ROOT="${TCRM_ROOT:-/opt/tcrm}"
CONF="$ROOT/tcrm.prod.conf"
PY="$ROOT/venv/bin/python"
export PYTHONPATH="$ROOT/tcrm-src"
export HOME="$ROOT"

MODULES="${1:-tcrm_marketing_hub,tcrm_lead_report}"
DBS="${2:-perla_villalari,tcrm_master}"

echo "=== pull latest code ==="
cd "$ROOT"
git fetch origin
git pull --ff-only origin "${DEPLOY_BRANCH:-feature/provisioning-and-routing}"

echo "=== stopping tcrm ==="
systemctl stop tcrm
sleep 2

RC=0
for DB in $(echo "$DBS" | tr ',' ' '); do
  echo "=== update module list on $DB ==="
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
    -c "$CONF" -d "$DB" --stop-after-init --update=all 2>&1 | tail -5 || true

  echo "=== install/upgrade $MODULES on $DB ==="
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
    -c "$CONF" -d "$DB" -i "$MODULES" --stop-after-init 2>&1 | tail -80 || {
      sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
        -c "$CONF" -d "$DB" -u "$MODULES" --stop-after-init 2>&1 | tail -80
    }
  this_rc=${PIPESTATUS[0]}
  if [ "$this_rc" -ne 0 ]; then RC=$this_rc; fi

  echo "=== verify crons on $DB ==="
  sudo -u postgres psql -d "$DB" -Atc "
    SELECT cron_name, active, interval_number, interval_type
    FROM ir_cron ic
    JOIN ir_model im ON im.id = ic.model_id
    WHERE im.model IN ('tcrm.marketing.meta.lead','tcrm.marketing.daily.metric')
    ORDER BY cron_name;
  " || true
done

echo "=== starting tcrm ==="
systemctl start tcrm
sleep 5
systemctl is-active tcrm

echo "=== health check ==="
curl -s -o /dev/null -w "perla_login=%{http_code}\n" --max-time 20 \
  https://perlavillalari.tcrm.online/web/login || true

echo "deploy_rc=$RC"
exit $RC
