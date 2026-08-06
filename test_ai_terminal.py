import sys
import logging
# Enable logging to see the fallback/retry logic
logging.basicConfig(level=logging.INFO)

sys.path.append('d:\\tcrm\\tcrm-src')
sys.path.append('d:\\tcrm\\custom_addons')

import tcrm

def test_tcrm_ai():
    try:
        # 1. Initialize TCRM environment
        tcrm.tools.config.parse_config(['-c', 'd:\\tcrm\\tcrm.conf'])
        registry = tcrm.registry('tcrm_master')
        
        with registry.cursor() as cr:
            env = tcrm.api.Environment(cr, tcrm.SUPERUSER_ID, {})
            
            # 2. Call the AI Engine
            # Asking about a real-time topic to test the DuckDuckGo layer
            prompt = "Model Sanayi Merkezi nerede ve bugünkü dolar kuru kaç TL?"
            print(f"\n[USER]: {prompt}")
            print("[THINKING] ... (Wait up to 120s for VPS search + generation)")
            
            # This calls the same method as the chat controller
            result = env['tcrm.ai.engine'].ask(prompt)
            
            # 3. Print Results
            print("\n" + "="*50)
            print("[AI RESPONSE]:")
            print(result.get('answer', 'NO ANSWER'))
            if result.get('error'):
                print(f"[ERROR]: {result.get('answer')}")
            print("="*50 + "\n")
            
    except Exception as e:
        print(f"\n[FATAL ERROR]: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tcrm_ai()
