#!/usr/bin/env bash
# Production orchestrator: Phase 0–3 (+ helpers for 4–5 wrappers)
# Isolation: one DB at a time; sibling HTTPS curls after each mutating step.
set -euo pipefail

ROOT=/opt/tcrm
CONF=$ROOT/tcrm.prod.conf
PY=$ROOT/venv/bin/python
export PYTHONPATH=$ROOT/tcrm-src
export HOME=$ROOT

KEEP_DBS=(tcrm_master akod_prod perla_villalari)
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=$ROOT/backups/pre_demo_purge_${STAMP}
REPORT_DIR=/tmp/qa_run_${STAMP}
mkdir -p "$ROOT/backups" "$REPORT_DIR"
mkdir -p "$BACKUP_DIR"
chown postgres:postgres "$BACKUP_DIR"
chmod 755 "$BACKUP_DIR"

log() { echo "[$(date -Is)] $*" | tee -a "$REPORT_DIR/orchestrator.log"; }

sibling_curl() {
  local label="$1"
  log "SIBLING_UP ($label)"
  local fail=0
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://tcrm.online/web/login || echo ERR)
  echo "tcrm.online=$code" | tee -a "$REPORT_DIR/sibling.log"
  [[ "$code" == "200" ]] || fail=1
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 https://akod.tcrm.online/web/login || echo ERR)
  echo "akod.tcrm.online=$code" | tee -a "$REPORT_DIR/sibling.log"
  [[ "$code" == "200" ]] || fail=1
  # Perla domain — discover from master if needed
  local perla_host
  perla_host=$(sudo -u postgres psql -d tcrm_master -Atc \
    "SELECT COALESCE(
       (SELECT d.domain FROM tcrm_tenant_domain d
        JOIN tcrm_tenant t ON t.id=d.tenant_id
        WHERE d.domain ILIKE '%perla%' OR t.name ILIKE '%perla%' OR t.db_name ILIKE '%perla%'
        ORDER BY d.id DESC LIMIT 1),
       'perlavillalari.tcrm.online'
     );" 2>/dev/null || echo "perlavillalari.tcrm.online")
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "https://${perla_host}/web/login" || echo ERR)
  echo "${perla_host}=$code" | tee -a "$REPORT_DIR/sibling.log"
  [[ "$code" == "200" ]] || fail=1
  echo "$perla_host" > "$REPORT_DIR/perla_host.txt"
  if [[ "$fail" -ne 0 ]]; then
    log "SIBLING_UP FAIL ($label)"
    return 1
  fi
  log "SIBLING_UP OK ($label)"
  return 0
}

phase0() {
  log "=== PHASE 0 PRECHECK ==="
  sudo -u postgres psql -Atc "SELECT datname FROM pg_database WHERE datistemplate=false AND datname<>'postgres' ORDER BY 1;" \
    | tee "$REPORT_DIR/db_list.txt"

  {
    echo "=== counts ==="
    for DB in "${KEEP_DBS[@]}"; do
      echo "-- $DB"
      sudo -u postgres psql -d "$DB" -Atc "
        SELECT 'crm_lead='||COALESCE((SELECT count(*)::text FROM crm_lead), 'NA');
      " 2>/dev/null || echo "crm_lead=NA"
      sudo -u postgres psql -d "$DB" -Atc "
        SELECT 'propertio_sale='||COALESCE((SELECT count(*)::text FROM propertio_sale), 'NA');
      " 2>/dev/null || echo "propertio_sale=NA"
      sudo -u postgres psql -d "$DB" -Atc "
        SELECT 'propertio_project='||COALESCE((SELECT count(*)::text FROM propertio_project), 'NA');
      " 2>/dev/null || echo "propertio_project=NA"
      if [[ "$DB" == "tcrm_master" ]]; then
        sudo -u postgres psql -d "$DB" -Atc "
          SELECT 'tenant='||name||'|db='||COALESCE(db_name,'')||'|active='||active::text
          FROM tcrm_tenant ORDER BY id;
        " 2>/dev/null || true
      fi
    done
  } | tee "$REPORT_DIR/qa_precheck_counts.txt"

  log "Backing up keep-list DBs to $BACKUP_DIR"
  for DB in "${KEEP_DBS[@]}"; do
    sudo -u postgres pg_dump -Fc -f "$BACKUP_DIR/${DB}.dump" "$DB"
    ls -lh "$BACKUP_DIR/${DB}.dump" | tee -a "$REPORT_DIR/orchestrator.log"
  done

  # Classify extras
  EXTRA=0
  while read -r db; do
    skip=0
    for k in "${KEEP_DBS[@]}"; do [[ "$db" == "$k" ]] && skip=1 && break; done
    if [[ "$skip" -eq 0 ]]; then
      echo "EXTRA_DB $db" | tee -a "$REPORT_DIR/extra_dbs.txt"
      EXTRA=1
    fi
  done < "$REPORT_DIR/db_list.txt"

  sibling_curl "phase0_baseline"
  echo "$REPORT_DIR" > /tmp/qa_latest_report_dir.txt
  log "PHASE0_OK report=$REPORT_DIR"
}

phase1() {
  log "=== PHASE 1 PURGE ==="
  REPORT_DIR=$(cat /tmp/qa_latest_report_dir.txt)
  # Drop extras first (dump then drop) — never touch keep list
  if [[ -f "$REPORT_DIR/extra_dbs.txt" ]]; then
    while read -r line; do
      edb=${line#EXTRA_DB }
      [[ -z "$edb" ]] && continue
      log "Dumping extra DB $edb before DROP"
      sudo -u postgres pg_dump -Fc -f "$BACKUP_DIR/EXTRA_${edb}.dump" "$edb" || true
      log "DROP DATABASE $edb"
      # terminate backends then drop
      sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${edb}' AND pid<>pg_backend_pid();" || true
      sudo -u postgres psql -c "DROP DATABASE IF EXISTS \"${edb}\";"
      sibling_curl "after_drop_$edb"
    done < "$REPORT_DIR/extra_dbs.txt"
  fi

  for DB in "${KEEP_DBS[@]}"; do
    log "PURGE $DB"
    sudo -u tcrm env HOME=$ROOT PYTHONPATH=$ROOT/tcrm-src \
      "$PY" "$ROOT/scripts/purge_demo_data.py" -c "$CONF" -d "$DB" \
      | tee "$REPORT_DIR/purge_${DB}.json"
    sibling_curl "after_purge_$DB"
  done
  log "PHASE1_OK"
}

phase2() {
  log "=== PHASE 2 CACHE ==="
  REPORT_DIR=$(cat /tmp/qa_latest_report_dir.txt)
  for DB in "${KEEP_DBS[@]}"; do
    log "cache clear $DB"
    sudo -u tcrm env HOME=$ROOT PYTHONPATH=$ROOT/tcrm-src \
      "$PY" "$ROOT/scripts/clear_caches_db.py" -c "$CONF" -d "$DB" \
      | tee -a "$REPORT_DIR/orchestrator.log"
  done

  log "Restarting tcrm once (shared blip)"
  systemctl restart tcrm
  sleep 8
  systemctl is-active tcrm nginx postgresql | tee "$REPORT_DIR/services_after_restart.txt"
  sibling_curl "after_restart"
  log "PHASE2_OK"
}

phase3() {
  log "=== PHASE 3 HEALTH ==="
  REPORT_DIR=$(cat /tmp/qa_latest_report_dir.txt)
  {
    echo "=== services ==="
    systemctl is-active tcrm nginx postgresql
    echo "=== disk ==="
    df -h / /opt/tcrm | tail -n +1
    echo "=== memory ==="
    free -h
    echo "=== modules per DB ==="
    for DB in "${KEEP_DBS[@]}"; do
      echo "-- $DB"
      sudo -u postgres psql -d "$DB" -Atc "
        SELECT name||'|'||state||'|'||COALESCE(latest_version,'')
        FROM ir_module_module
        WHERE name IN ('meta_leads','custom_crm_integration','tcrm_saas_core','tcrm_call_center','tcrm_ai','tcrm_propertio','tcrm_marketing_hub','tcrm_web_enhance')
        ORDER BY 1;
      " 2>/dev/null || echo "module_query_failed"
    done
    echo "=== schema crm.lead missing cols ==="
    for DB in "${KEEP_DBS[@]}"; do
      echo "-- $DB"
      sudo -u tcrm env HOME=$ROOT PYTHONPATH=$ROOT/tcrm-src \
        "$PY" "$ROOT/scripts/check_crm_lead_schema.py" -c "$CONF" -d "$DB" || echo "schema_check_failed"
    done
    echo "=== recent UndefinedColumn (5m) ==="
    journalctl -u tcrm --since "5 minutes ago" --no-pager 2>/dev/null | grep -c UndefinedColumn || echo 0
    grep -c UndefinedColumn /opt/tcrm/tcrm_data/tcrm.log 2>/dev/null | tail -1 || true
  } | tee "$REPORT_DIR/qa_health_report.txt"

  sibling_curl "phase3_health" | tee -a "$REPORT_DIR/qa_health_report.txt"
  # Gate: services active + sibling up already enforced
  systemctl is-active --quiet tcrm
  systemctl is-active --quiet nginx
  systemctl is-active --quiet postgresql
  if grep -q "still_missing \\[\\]" "$REPORT_DIR/qa_health_report.txt" || grep -q "still_missing []" "$REPORT_DIR/qa_health_report.txt"; then
    :
  fi
  # Fail if any still_missing non-empty
  if grep -E "still_missing \[[^]]+\]" "$REPORT_DIR/qa_health_report.txt" | grep -v "still_missing \[\]"; then
    log "HEALTH GATE FAIL: missing columns"
    exit 4
  fi
  log "PHASE3_OK"
}

cmd=${1:-all}
case "$cmd" in
  phase0) phase0 ;;
  phase1) phase1 ;;
  phase2) phase2 ;;
  phase3) phase3 ;;
  all)
    phase0
    phase1
    phase2
    phase3
    ;;
  *) echo "usage: $0 [phase0|phase1|phase2|phase3|all]"; exit 1 ;;
esac
