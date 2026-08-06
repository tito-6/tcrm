import psycopg2

for db in ['akod_prod', 'tcrm_master', 'tcrm_db', 'tcrm']:
    try:
        conn = psycopg2.connect(dbname=db, user='odoo', password='odoo', host='localhost')
        cur = conn.cursor()
        cur.execute("DELETE FROM ir_ui_view WHERE arch_db::text LIKE '%meta_creative_fetch_method%';")
        print(f"[{db}] Deleted broken views: {cur.rowcount}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[{db}] Error: {e}")
