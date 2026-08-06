import psycopg2

def check_ai_status():
    try:
        conn = psycopg2.connect("dbname=tcrm_master user=odoo password=odoo host=localhost port=5432")
        cur = conn.cursor()
        cur.execute("SELECT name, status, last_error, cooldown_until FROM tcrm_ai_key WHERE name = 'Ollama Default'")
        row = cur.fetchone()
        print(f"Ollama Default: {row}")
        conn.close()
    except Exception as e:
        print(f"FAILED TO CHECK: {e}")

if __name__ == "__main__":
    check_ai_status()
