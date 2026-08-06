#!/bin/bash
set -euo pipefail

echo "=================================================="
echo "2. CREATE RESTRICTED OPERATING-SYSTEM USERS"
echo "=================================================="

if ! id -u tcrm-public > /dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin tcrm-public
fi

if ! id -u tcrm_maintenance > /dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin tcrm_maintenance
fi

echo "=================================================="
echo "3. CREATE DEPLOYMENT DIRECTORIES"
echo "=================================================="

mkdir -p /opt/tcrm-public/releases
mkdir -p /opt/tcrm-public/shared/logs
mkdir -p /etc/tcrm-public

chown -R tcrm-public:tcrm-public /opt/tcrm-public/releases
chown -R tcrm-public:tcrm-public /opt/tcrm-public/shared
chown root:root /etc/tcrm-public
chmod 755 /etc/tcrm-public

echo "=================================================="
echo "4. INSTALL A SUPPORTED NODE ENVIRONMENT"
echo "=================================================="
corepack enable
corepack prepare pnpm@9.15.4 --activate

echo "=================================================="
echo "6. CREATE THE PROTECTED APPLICATION ENVIRONMENT"
echo "=================================================="

ENV_FILE="/etc/tcrm-public/tcrm-public.env"
RATE_LIMIT_HASH_SECRET=$(openssl rand -hex 32)
TCRM_LEAD_SECRET=$(openssl rand -hex 32)
TCRM_TENANT_PUBLIC_UUID=$(cat /proc/sys/kernel/random/uuid)

cat << EOF > $ENV_FILE
NODE_ENV=production
HOSTNAME=127.0.0.1
PORT=3002
RATE_LIMIT_DB_URL=postgresql://tcrm_public_rate_limit_app:testpass@127.0.0.1:5432/tcrm_master
RATE_LIMIT_HASH_SECRET=$RATE_LIMIT_HASH_SECRET
TCRM_LEAD_SECRET=$TCRM_LEAD_SECRET
TCRM_TENANT_PUBLIC_UUID=$TCRM_TENANT_PUBLIC_UUID
TCRM_BACKEND_INTERNAL_URL=http://127.0.0.1:8069
NEXT_PUBLIC_SITE_URL=https://public-staging.tcrm.online
EOF

chown tcrm-public:tcrm-public $ENV_FILE
chmod 0600 $ENV_FILE

stat -c '%U %G %a %n' $ENV_FILE
