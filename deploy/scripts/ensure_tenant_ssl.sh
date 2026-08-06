#!/usr/bin/env bash
# Platform SSL for *.tcrm.online
#
# Preferred: a Let's Encrypt WILDCARD cert (tcrm.online + *.tcrm.online) via
# Hostinger DNS-01. That covers every future tenant subdomain automatically.
#
# Fallback: HTTP-01 --expand of individual hostnames (spool / one-shot).
#
# Usage:
#   ensure_tenant_ssl.sh --issue-wildcard
#   ensure_tenant_ssl.sh perlavillalari.tcrm.online
#   ensure_tenant_ssl.sh --from-spool
#   ensure_tenant_ssl.sh --status
set -euo pipefail

LIVE_DIR="${TCRM_LE_LIVE_DIR:-/etc/letsencrypt/live/tcrm.online}"
SPOOL_DIR="${TCRM_SSL_SPOOL_DIR:-/var/lib/tcrm/ssl-pending}"
CERT_NAME="${TCRM_LE_CERT_NAME:-tcrm.online}"
WEBROOT="${TCRM_CERTBOT_WEBROOT:-/var/www/certbot}"
HOSTINGER_INI="${TCRM_HOSTINGER_INI:-/etc/letsencrypt/hostinger.ini}"
PLATFORM_SUFFIX=".tcrm.online"
APEX="tcrm.online"
WILDCARD="*.tcrm.online"

log() { echo "[tcrm-ssl] $*"; }

cert_sans() {
  local cert="$LIVE_DIR/fullchain.pem"
  [[ -f "$cert" ]] || return 0
  openssl x509 -in "$cert" -noout -text 2>/dev/null \
    | tr ',' '\n' \
    | sed -n 's/.*DNS:\s*//p'
}

domain_on_cert() {
  local want="$1"
  cert_sans | grep -qxF "$want"
}

wildcard_active() {
  domain_on_cert "$WILDCARD" && domain_on_cert "$APEX"
}

platform_covered() {
  local domain="$1"
  if [[ "$domain" == "$APEX" || "$domain" == "www.$APEX" ]]; then
    domain_on_cert "$domain" && return 0
    domain_on_cert "$APEX" && return 0
  fi
  if [[ "$domain" == *"$PLATFORM_SUFFIX" ]]; then
    wildcard_active && return 0
    domain_on_cert "$domain" && return 0
  fi
  return 1
}

mark_db_active() {
  local d="$1"
  if [[ "$d" == "--all-platform" ]]; then
    sudo -u postgres psql -d tcrm_master -v ON_ERROR_STOP=1 -c \
      "UPDATE tcrm_tenant_domain
          SET ssl_status='active', verified=true
        WHERE lower(domain) LIKE '%.tcrm.online'
           OR lower(domain) IN ('tcrm.online','www.tcrm.online');" \
      >/dev/null 2>&1 || log "warn: could not bulk-update ssl_status"
    return 0
  fi
  sudo -u postgres psql -d tcrm_master -v ON_ERROR_STOP=1 -c \
    "UPDATE tcrm_tenant_domain SET ssl_status='active', verified=true WHERE lower(domain)='${d}';" \
    >/dev/null 2>&1 || log "warn: could not update ssl_status in DB for $d"
}

reload_nginx() {
  nginx -t
  systemctl reload nginx
}

issue_wildcard() {
  if wildcard_active; then
    log "wildcard already active on $CERT_NAME"
    mark_db_active --all-platform
    return 0
  fi

  if [[ ! -f "$HOSTINGER_INI" ]]; then
    log "ERROR: missing $HOSTINGER_INI"
    log "Create it with:"
    log "  dns_hostinger_api_token = YOUR_HOSTINGER_API_TOKEN"
    log "Token: https://hpanel.hostinger.com/profile/api (DNS permissions)"
    return 2
  fi
  chmod 600 "$HOSTINGER_INI" || true

  # Ensure plugin is available.
  if ! certbot plugins 2>/dev/null | grep -qi 'dns-hostinger'; then
    log "installing certbot-dns-hostinger"
    pip3 install --break-system-packages 'certbot-dns-hostinger' \
      || pip3 install 'certbot-dns-hostinger'
  fi

  log "issuing wildcard cert $APEX + $WILDCARD via Hostinger DNS-01"
  # www is covered by *.tcrm.online — LE rejects listing both together.
  CERTBOT_BIN="${CERTBOT_BIN:-/opt/tcrm/certbot-dns-venv/bin/certbot}"
  [[ -x "$CERTBOT_BIN" ]] || CERTBOT_BIN="$(command -v certbot)"
  "$CERTBOT_BIN" certonly \
    --authenticator dns-hostinger \
    --dns-hostinger-credentials "$HOSTINGER_INI" \
    --dns-hostinger-propagation-seconds "${TCRM_DNS_PROPAGATION_SECONDS:-120}" \
    --cert-name "$CERT_NAME" \
    --non-interactive --agree-tos --keep-until-expiring \
    --email "${TCRM_LE_EMAIL:-info@akod.tech}" \
    -d "$APEX" \
    -d "$WILDCARD"

  reload_nginx
  mark_db_active --all-platform
  # Clear pending spool — wildcard covers them all.
  rm -f "$SPOOL_DIR"/*.domain 2>/dev/null || true
  log "OK: wildcard active; all *.tcrm.online tenants covered"
}

expand_domain_http01() {
  local domain="$1"
  local -a names=("$APEX" "www.$APEX")
  local san found

  if [[ -f "$LIVE_DIR/fullchain.pem" ]]; then
    while IFS= read -r san; do
      [[ -n "$san" ]] || continue
      # Drop previous wildcard attempts from SAN list if LE rejects mix? keep as-is.
      found=0
      for n in "${names[@]}"; do
        [[ "$n" == "$san" ]] && found=1 && break
      done
      [[ $found -eq 0 ]] && names+=("$san")
    done < <(cert_sans)
  fi
  found=0
  for n in "${names[@]}"; do
    [[ "$n" == "$domain" ]] && found=1 && break
  done
  [[ $found -eq 0 ]] && names+=("$domain")

  local -a args=()
  for n in "${names[@]}"; do
    args+=(-d "$n")
  done

  log "HTTP-01 expand '$CERT_NAME' (+${#names[@]} names) for $domain"
  if certbot certonly --webroot -w "$WEBROOT" --cert-name "$CERT_NAME" \
      --expand --non-interactive --agree-tos --keep-until-expiring \
      "${args[@]}"; then
    reload_nginx
    mark_db_active "$domain"
    log "OK: $domain covered (HTTP-01)"
    return 0
  fi
  log "webroot failed; trying nginx plugin"
  certbot --nginx --cert-name "$CERT_NAME" --expand --non-interactive \
      --agree-tos --keep-until-expiring "${args[@]}"
  reload_nginx
  mark_db_active "$domain"
  log "OK: $domain covered (nginx plugin)"
}

ensure_domain() {
  local domain="$1"
  domain="${domain,,}"
  domain="${domain%%:*}"
  domain="${domain%.}"

  if [[ ! "$domain" =~ ^[a-z0-9*]([a-z0-9.-]*[a-z0-9])?$ ]]; then
    log "reject invalid domain: $domain"
    return 1
  fi
  if [[ "$domain" != *"$PLATFORM_SUFFIX" && "$domain" != "$APEX" && "$domain" != "www.$APEX" ]]; then
    log "skip non-platform domain: $domain"
    return 0
  fi

  if platform_covered "$domain"; then
    log "already covered: $domain (wildcard=$(wildcard_active && echo yes || echo no))"
    mark_db_active "$domain"
    return 0
  fi

  # Prefer upgrading the whole platform to a wildcard when Hostinger creds exist.
  if [[ -f "$HOSTINGER_INI" ]]; then
    if issue_wildcard; then
      return 0
    fi
    log "wildcard issue failed; falling back to single-host HTTP-01"
  else
    log "no Hostinger DNS creds ($HOSTINGER_INI); using single-host HTTP-01"
    log "tip: add Hostinger API token once → --issue-wildcard covers ALL future tenants"
  fi

  expand_domain_http01 "$domain"
}

process_spool() {
  mkdir -p "$SPOOL_DIR"
  shopt -s nullglob
  local files=("$SPOOL_DIR"/*.domain)
  if [[ ${#files[@]} -eq 0 ]]; then
    # Still useful: if wildcard is active, keep DB rows green.
    if wildcard_active; then
      mark_db_active --all-platform
    fi
    log "spool empty"
    return 0
  fi

  # One wildcard issue covers the whole spool.
  if [[ -f "$HOSTINGER_INI" ]] && ! wildcard_active; then
    if issue_wildcard; then
      rm -f "${files[@]}"
      return 0
    fi
  fi

  local f domain
  for f in "${files[@]}"; do
    domain="$(tr -d '[:space:]' < "$f")"
    if ensure_domain "$domain"; then
      rm -f "$f"
      printf '%s\n' "$domain" > "${f%.domain}.done"
    else
      log "FAILED for $domain (leaving $f)"
    fi
  done
}

print_status() {
  echo "cert: $LIVE_DIR/fullchain.pem"
  if [[ -f "$LIVE_DIR/fullchain.pem" ]]; then
    echo "SANs:"
    cert_sans | sed 's/^/  /'
  else
    echo "  (missing)"
  fi
  echo "wildcard_active: $(wildcard_active && echo yes || echo no)"
  echo "hostinger_ini: $([[ -f $HOSTINGER_INI ]] && echo present || echo MISSING)"
  echo "spool: $SPOOL_DIR"
  ls -1 "$SPOOL_DIR" 2>/dev/null | sed 's/^/  /' || true
}

case "${1:-}" in
  --issue-wildcard) issue_wildcard ;;
  --from-spool) process_spool ;;
  --status) print_status ;;
  "")
    echo "Usage: $0 --issue-wildcard | --from-spool | --status | <hostname>" >&2
    exit 2
    ;;
  *) ensure_domain "$1" ;;
esac
