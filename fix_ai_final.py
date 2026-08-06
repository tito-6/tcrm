import psycopg2

def fix_ai_config():
    try:
        conn = psycopg2.connect("dbname=tcrm_master user=odoo password=odoo host=localhost port=5432")
        cur = conn.cursor()
        
        # 1. Flip priorities: Ollama (VPS) = 1, Gemini = 10
        cur.execute("UPDATE tcrm_ai_provider SET priority = 10 WHERE provider_code = 'gemini'")
        cur.execute("UPDATE tcrm_ai_provider SET priority = 1 WHERE provider_code = 'ollama'")
        
        # 2. Reset status of ALL keys so they are available right now
        cur.execute("UPDATE tcrm_ai_key SET status = 'active', cooldown_until = NULL, fail_count = 0")
        
        # 3. Double check VPS settings in ICP (tcrm.ai_base_url)
        # Ensure it is the RAG proxy which handles the logic
        cur.execute("UPDATE ir_config_parameter SET value = 'http://45.9.191.119:8000' WHERE key = 'tcrm.ai_base_url'")
        
        conn.commit()
        print("FIX APPLIED: Ollama VPS (Priority 1), Gemini (Priority 10). All keys RESET to active.")
        conn.close()
    except Exception as e:
        print(f"FAILED TO FIX CONFIG: {e}")

if __name__ == "__main__":
    fix_ai_config()
