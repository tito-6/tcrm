#!/bin/bash
systemctl stop tcrm || true
sleep 1
export PYTHONPATH=/opt/tcrm/tcrm-src
# Capture all output
sudo -u tcrm bash -lc 'export PYTHONPATH=/opt/tcrm/tcrm-src; /opt/tcrm/venv/bin/python -c "
import traceback
try:
    import tcrm
    print(\"tcrm ok\", tcrm)
    from tcrm.cli import main
    print(\"cli ok\")
except Exception:
    traceback.print_exc()
"' 2>&1 | tee /tmp/import_test.txt

echo "==== run with logging ===="
sudo -u tcrm bash -lc 'export PYTHONPATH=/opt/tcrm/tcrm-src; /opt/tcrm/venv/bin/python /opt/tcrm/tcrm-src/tcrm-bin -c /opt/tcrm/tcrm.prod.conf -d akod_prod -u meta_leads --stop-after-init --log-level=debug' 2>&1 | tee /tmp/upgrade_debug.txt | tail -120
echo EXIT:${PIPESTATUS[0]}
systemctl start tcrm
