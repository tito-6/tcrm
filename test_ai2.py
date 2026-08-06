import sys
import logging
logging.basicConfig(level=logging.DEBUG)

sys.path.append('d:\\tcrm\\tcrm-src')
sys.path.append('d:\\tcrm\\custom_addons')

import tcrm
tcrm.tools.config.parse_config(['-c', 'd:\\tcrm\\tcrm.conf'])
registry = tcrm.registry('tcrm_master')

with registry.cursor() as cr:
    env = tcrm.api.Environment(cr, tcrm.SUPERUSER_ID, {})
    manager = env['tcrm.ai.engine']._get_api_manager()
    from tcrm_ai.utils.api_manager.unified_types import UnifiedMessage
    msgs = [UnifiedMessage(role='user', content='Say hi')]
    try:
        resp = manager.get_response(msgs)
        print("SUCCESS:", resp.provider, resp.text)
    except Exception as e:
        print("EXCEPTION:", e)
        # dump key states
        cur = env.cr
        cur.execute("SELECT name, status, fail_count, last_error FROM tcrm_ai_key")
        for r in cur.fetchall():
            print(r)
