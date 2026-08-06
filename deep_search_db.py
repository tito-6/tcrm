import psycopg2

for db in ['tcrm_master', 'akod_prod', 'tcrm', 'tcrm_db']:
    print(f"=== Searching DB: {db} ===")
    try:
        conn = psycopg2.connect(dbname=db, user='odoo', password='odoo', host='localhost')
        cur = conn.cursor()
        cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public'")
        cols = cur.fetchall()
        for t, c in cols:
            try:
                cur.execute(f'SELECT id, "{c}"::text FROM "{t}" WHERE "{c}"::text LIKE %s OR "{c}"::text LIKE %s LIMIT 3', ('%zoomtcrm%', '%s_mega_menu_tcrm_menu%'))
                rows = cur.fetchall()
                if rows:
                    print(f"  MATCH in table [{t}], column [{c}]:")
                    for r in rows:
                        print(f"    Row ID {r[0]}: {r[1][:150]}")
            except Exception as e:
                conn.rollback()
        conn.close()
    except Exception as e:
        print(f"  Failed to connect: {e}")
