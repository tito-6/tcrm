import psycopg2

for db in ['tcrm_master', 'akod_prod', 'tcrm', 'tcrm_db']:
    try:
        conn = psycopg2.connect(dbname=db, user='odoo', password='odoo', host='localhost')
        cur = conn.cursor()
        cur.execute("SELECT id, name, url, store_fname FROM ir_attachment WHERE index_content LIKE '%css_error%' OR index_content LIKE '%zoomtcrm%' OR url LIKE '%032ba33%' OR name LIKE '%assets_frontend%'")
        rows = cur.fetchall()
        if rows:
            print(f"DB {db} has {len(rows)} matching attachment rows:")
            for r in rows:
                print(' ', r)
        conn.close()
    except Exception as e:
        print(f"Error connecting to {db}: {e}")
