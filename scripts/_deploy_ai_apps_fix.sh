#!/usr/bin/env bash
set -euo pipefail
# Deploy AI power-up + Apps sidebar hide across master + all tenant DBs.

export PYTHONPATH=/opt/tcrm/tcrm-src
CONF=/opt/tcrm/tcrm.prod.conf
PY=/opt/tcrm/venv/bin/python

systemctl stop tcrm

# Discover tenant DBs from master
mapfile -t DBS < <(sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('tcrm_master')
dbs = ['tcrm_master']
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    if 'tcrm.tenant' in env:
        for t in env['tcrm.tenant'].sudo().search([('db_name', '!=', False)]):
            name = (t.db_name or '').strip()
            if name and name not in dbs:
                dbs.append(name)
print('\n'.join(dbs))
PY
)

echo "Databases: ${DBS[*]}"

for db in "${DBS[@]}"; do
  echo "=== Upgrade tcrm_ai + tcrm_web_enhance on $db ==="
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
    -c "$CONF" -d "$db" -u tcrm_ai,tcrm_web_enhance --stop-after-init \
    || echo "WARN: upgrade failed on $db"
done

# Force-hide Apps menus on every non-master DB
for db in "${DBS[@]}"; do
  [[ "$db" == "tcrm_master" ]] && continue
  echo "=== Hide Apps on $db ==="
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" /opt/tcrm/scripts/_force_hide_apps.py "$db" || true
done

systemctl start tcrm
sleep 3
systemctl is-active tcrm

# Verify master AI
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc
reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    cfg = env['tcrm.ai.config'].sudo().get_config()
    print('AI model', cfg.model, 'internet', cfg.allow_internet_research, 'payment', cfg.allow_payment_data)
    print('chat_block', entitlement_svc.chat_block_reason(env))
    tools = env['tcrm.ai.engine']
    from tcrm.addons.tcrm_ai.services.tools import TcrmAiToolExecutor
    ex = TcrmAiToolExecutor(env, cfg, base_url='')
    names = [t['function']['name'] for t in ex.available_tool_defs()]
    print('tools', sorted(names))
    # phone search smoke
    res = ex.search_accessible_leads(query='055252428866', limit=5)
    print('phone_search_count', res.get('record_count'), 'query', res.get('query'))
PY

echo DONE
