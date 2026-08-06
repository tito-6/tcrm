#!/bin/bash
set -euo pipefail


echo "15. INSTALL THE RESTRICTED CLEANUP TIMER"
echo "=================================================="
cat << 'EOF' > /etc/systemd/system/tcrm-rate-limit-cleanup.service
[Unit]
Description=TCRM Rate Limit Counter Cleanup
After=network.target

[Service]
Type=oneshot
User=tcrm_maintenance
Group=tcrm_maintenance
Environment="DB_URL=postgresql://tcrm_public_rate_limit_maintenance:testpass@127.0.0.1:5432/tcrm_master"
ExecStart=/opt/tcrm/venv/bin/python3 -c "import psycopg2, os; conn = psycopg2.connect(os.environ['DB_URL']); conn.autocommit = True; cur = conn.cursor(); cur.execute('SELECT public_web.cleanup_expired_rate_limits(1000);'); print(cur.fetchone()[0]);"
EOF

cat << 'EOF' > /etc/systemd/system/tcrm-rate-limit-cleanup.timer
[Unit]
Description=Run TCRM Rate Limit Cleanup Every Minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now tcrm-rate-limit-cleanup.timer
systemctl start tcrm-rate-limit-cleanup.service || true


