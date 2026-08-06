import sys
sys.path.append('d:\\tcrm\\tcrm-src')
sys.path.append('d:\\tcrm\\custom_addons')

import tcrm
tcrm.tools.config.parse_config(['-c', 'd:\\tcrm\\tcrm.conf'])
registry = tcrm.registry('tcrm_master')

with registry.cursor() as cr:
    env = tcrm.api.Environment(cr, tcrm.SUPERUSER_ID, {})
    
    # Needs to import the class since we have to construct a UnifiedMessage
    # Wait, we can just use dicts if we look at api_manager.py:
    # `adapter.build_request` takes dicts or UnifiedMessage.
    
    manager = env['tcrm.ai.engine']._get_api_manager()
    print("Testing AI configuration... calling get_response")
    try:
        resp = manager.get_response([{'role': 'user', 'content': 'Say "Configuration Complete."'}])
        print("SUCCESS! Provider:", resp.provider)
        print("Model:", resp.model)
        print("Key Label:", resp.key_label)
        print("Response Text:", resp.text)
    except Exception as e:
        print("ERROR:", e)
