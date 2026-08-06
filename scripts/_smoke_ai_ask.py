from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    engine = env['tcrm.ai.engine']
    for msg in (
        'İstanbulda hava nasıl bugün?',
        '055252428866 numaralı leadi bul',
        'Kaç lead var sistemde?',
    ):
        res = engine._ask(msg)
        ans = (res.get('answer') or '')[:300]
        print('Q:', msg)
        print('A:', ans.replace('\n', ' '))
        print('disabled', res.get('disabled'), 'error', res.get('error'))
        print('---')
    cr.commit()
