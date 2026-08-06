ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@public-staging.tcrm.online << 'EOF'
echo "ALTER ROLE tcrm_public_rate_limit_app WITH PASSWORD 'testpass'; ALTER ROLE tcrm_public_rate_limit_maintenance WITH PASSWORD 'testpass';" > /tmp/setpass.sql
sudo -u postgres psql -d tcrm_master -f /tmp/setpass.sql
EOF
