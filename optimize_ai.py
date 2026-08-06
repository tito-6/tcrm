import psycopg2

def optimize_ai():
    try:
        conn = psycopg2.connect("dbname=tcrm_master user=odoo password=odoo host=localhost port=5432")
        cur = conn.cursor()
        
        # 1. Deactivate Gemini Keys (dead)
        cur.execute("""
            UPDATE tcrm_ai_key 
            SET active = false 
            WHERE provider_id IN (SELECT id FROM tcrm_ai_provider WHERE provider_code = 'gemini')
        """)
        
        # 2. Reset Ollama Key
        cur.execute("""
            UPDATE tcrm_ai_key 
            SET active = true, status = 'active', cooldown_until = NULL, fail_count = 0 
            WHERE name = 'Ollama Default'
        """)
        
        # 3. Ensure Ollama Provider is Priority 1
        cur.execute("UPDATE tcrm_ai_provider SET priority = 1 WHERE provider_code = 'ollama'")
        
        conn.commit()
        print("OPTIMIZED: Gemini Deactivated. Ollama Reset (Priority 1).")
        conn.close()
    except Exception as e:
        print(f"FAILED TO OPTIMIZE: {e}")

if __name__ == "__main__":
    optimize_ai()
