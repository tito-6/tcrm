#!/usr/bin/env bash
# Provision TCRM on Ubuntu 24.04 VPS (idempotent-ish).
set -euo pipefail

TCRM_ROOT=/opt/tcrm
DB_PASS="${TCRM_DB_PASSWORD:-$(openssl rand -hex 16)}"
ADMIN_PASS="${TCRM_ADMIN_PASSWORD:-$(openssl rand -hex 12)}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  postgresql postgresql-contrib \
  python3 python3-venv python3-dev python3-pip \
  build-essential libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev \
  libjpeg-dev zlib1g-dev libpq-dev git curl nginx certbot python3-certbot-nginx \
  ufw rsync

# Firewall: SSH/HTTP/HTTPS only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable || true

id tcrm >/dev/null 2>&1 || useradd --system --home "$TCRM_ROOT" --shell /bin/bash tcrm
mkdir -p "$TCRM_ROOT" "$TCRM_ROOT/tcrm_data" "$TCRM_ROOT/backups" /var/www/certbot
chown -R tcrm:tcrm "$TCRM_ROOT"

# PostgreSQL role + DB
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='tcrm'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER tcrm WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='tcrm_master'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE tcrm_master OWNER tcrm;"
sudo -u postgres psql -c "ALTER USER tcrm WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tcrm_master TO tcrm;"

# Python venv
if [ ! -x "$TCRM_ROOT/venv/bin/python" ]; then
  sudo -u tcrm python3 -m venv "$TCRM_ROOT/venv"
fi
sudo -u tcrm "$TCRM_ROOT/venv/bin/pip" install --upgrade pip wheel setuptools
if [ -f "$TCRM_ROOT/tcrm-src/requirements.txt" ]; then
  sudo -u tcrm "$TCRM_ROOT/venv/bin/pip" install -r "$TCRM_ROOT/tcrm-src/requirements.txt"
fi
sudo -u tcrm "$TCRM_ROOT/venv/bin/pip" install twilio requests cryptography psycopg2-binary

# Production conf
if [ ! -f "$TCRM_ROOT/tcrm.prod.conf" ]; then
  sed -e "s/CHANGE_ME_DB_PASSWORD/${DB_PASS}/g" \
      -e "s/CHANGE_ME_ADMIN_MASTER_PASSWORD/${ADMIN_PASS}/g" \
      "$TCRM_ROOT/deploy/tcrm.prod.conf.template" > "$TCRM_ROOT/tcrm.prod.conf"
  chown tcrm:tcrm "$TCRM_ROOT/tcrm.prod.conf"
  chmod 600 "$TCRM_ROOT/tcrm.prod.conf"
fi

install -m 644 "$TCRM_ROOT/deploy/systemd/tcrm.service" /etc/systemd/system/tcrm.service
systemctl daemon-reload
systemctl enable tcrm

# Nginx site (SSL certs may be missing until certbot)
install -m 644 "$TCRM_ROOT/deploy/nginx/tcrm.online.conf" /etc/nginx/sites-available/tcrm.online
ln -sfn /etc/nginx/sites-available/tcrm.online /etc/nginx/sites-enabled/tcrm.online

# Cron backup
install -m 755 "$TCRM_ROOT/deploy/scripts/backup_tcrm.sh" /usr/local/bin/backup_tcrm.sh
grep -q backup_tcrm /etc/crontab || echo "15 3 * * * root /usr/local/bin/backup_tcrm.sh >> /var/log/tcrm_backup.log 2>&1" >> /etc/crontab

echo "DB password: ${DB_PASS}"
echo "Admin master password: ${ADMIN_PASS}"
echo "Provision base complete. Sync code, init DB modules, start tcrm, then certbot."
