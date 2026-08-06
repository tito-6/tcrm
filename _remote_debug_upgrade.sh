#!/bin/bash
set -x
ROOT=/opt/tcrm
export PYTHONPATH=$ROOT/tcrm-src
systemctl stop tcrm || true
sleep 2
# Show binary
head -5 $ROOT/tcrm-src/tcrm-bin
ls -la $ROOT/venv/bin/python
# Run upgrade with full output
sudo -u tcrm env PYTHONPATH=$ROOT/tcrm-src $ROOT/venv/bin/python $ROOT/tcrm-src/tcrm-bin \
  -c $ROOT/tcrm.prod.conf -d akod_prod -u meta_leads --stop-after-init
echo EXIT:$?
systemctl start tcrm
