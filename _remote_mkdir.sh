#!/bin/bash
set -euxo pipefail
mkdir -p /opt/tcrm/custom_addons/meta_leads/static/description
mkdir -p /tmp/meta_leads_up
chown -R tcrm:tcrm /opt/tcrm/custom_addons/meta_leads/static || true
'