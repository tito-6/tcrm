import psycopg2
import time

def setup_db():
    conn = psycopg2.connect("dbname=tcrm_master user=odoo password=odoo host=localhost port=5432")
    cur = conn.cursor()
    
    # 1. Clear existing provider and key tables safely
    cur.execute("DELETE FROM tcrm_ai_key;")
    cur.execute("DELETE FROM tcrm_ai_provider;")
    
    # 2. Insert Gemini Provider
    cur.execute("""
        INSERT INTO tcrm_ai_provider (name, provider_code, default_model, priority, active, rpm_limit, rpd_limit, tpm_limit)
        VALUES ('Google Gemini', 'gemini', 'gemini-2.0-flash', 10, true, 15, 1500, 0)
        RETURNING id;
    """)
    gemini_id = cur.fetchone()[0]
    
    # 3. Insert Gemini Keys
    keys = [
        'AIzaSyAgQzJw6INFZBIHv_RtrZtp4eBEDc816kU',
        'AIzaSyDJsDRb_jjhIaQIGThhDQQWPTEp5LooFF0',
        'AIzaSyB8KYdlP0hTwsUJfwPR6MW8leQRhKqKTYI',
    ]
    for i, key in enumerate(keys):
        cur.execute("""
            INSERT INTO tcrm_ai_key (provider_id, sequence, name, api_key, active, status, rpm_count, rpd_count, tpm_used, tpd_used, success_count, fail_count, total_calls)
            VALUES (%s, %s, %s, %s, true, 'active', 0, 0, 0, 0, 0, 0, 0);
        """, (gemini_id, i * 10, f'Gemini Key {i+1}', key))
        
    # 4. Insert Ollama VPS Provider
    cur.execute("""
        INSERT INTO tcrm_ai_provider (name, provider_code, default_model, base_url, priority, active, rpm_limit, rpd_limit, tpm_limit)
        VALUES ('Ollama VPS', 'ollama', 'qwen2.5:3b', 'http://45.9.191.119:11434', 20, true, 0, 0, 0)
        RETURNING id;
    """)
    ollama_id = cur.fetchone()[0]
    
    # 5. Insert Ollama VPS Key
    cur.execute("""
        INSERT INTO tcrm_ai_key (provider_id, sequence, name, api_key, active, status, rpm_count, rpd_count, tpm_used, tpd_used, success_count, fail_count, total_calls)
        VALUES (%s, 10, 'Ollama Default', 'http://45.9.191.119:11434', true, 'active', 0, 0, 0, 0, 0, 0, 0);
    """, (ollama_id,))
    
    # 6. Update System Parameters
    # ir_config_parameter updates
    params = {
        'tcrm.ai_base_url': 'http://45.9.191.119:8000',
        'tcrm_ai.ollama_url': 'http://45.9.191.119:11434',
        'tcrm_ai.ollama_model': 'qwen2.5:3b',
        'tcrm_ai.active_provider_id': str(gemini_id),
    }
    for k, v in params.items():
        cur.execute("SELECT id FROM ir_config_parameter WHERE key = %s", (k,))
        if cur.fetchone():
            cur.execute("UPDATE ir_config_parameter SET value = %s WHERE key = %s", (v, k))
        else:
            cur.execute("INSERT INTO ir_config_parameter (key, value) VALUES (%s, %s)", (k, v))
            
    conn.commit()
    print("Database successfully configured with new AI providers!")
    conn.close()

if __name__ == "__main__":
    setup_db()
