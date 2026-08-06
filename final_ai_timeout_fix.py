import psycopg2
from datetime import datetime, timedelta, timezone

def final_fix():
    try:
        conn = psycopg2.connect("dbname=tcrm_master user=odoo password=odoo host=localhost port=5432")
        cur = conn.cursor()
        
        # 1. Bump timeouts (Odoo side)
        cur.execute("UPDATE ir_config_parameter SET value = '120' WHERE key = 'tcrm.ai_request_timeout'")
        cur.execute("UPDATE tcrm_ai_config SET request_timeout = 120")
        
        # 2. Reset status of Ollama (Priority 1)
        cur.execute("""
            UPDATE tcrm_ai_key 
            SET active = true, status = 'active', cooldown_until = NULL, fail_count = 0, last_error = NULL
            WHERE name = 'Ollama Default'
        """)
        
        # 3. Ensure Gemini keys are DEACTIVATED (no fallback to dead keys)
        cur.execute("""
            UPDATE tcrm_ai_key 
            SET active = false 
            WHERE provider_id IN (SELECT id FROM tcrm_ai_provider WHERE provider_code = 'gemini')
        """)
        
        conn.commit()
        print("FINAL FIX: Timeout 120s. Ollama ACTIVE. Gemini DEACTIVATED.")
        conn.close()
    except Exception as e:
        print(f"FAILED TO APPLY FINAL FIX: {e}")

if __name__ == "__main__":
    final_fix()
