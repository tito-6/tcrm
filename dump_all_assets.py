import psycopg2

conn = psycopg2.connect(dbname='tcrm_master', user='odoo', password='odoo', host='localhost')
cur = conn.cursor()
cur.execute("SELECT id, name, path, target, bundle FROM ir_asset ORDER BY id ASC")
rows = cur.fetchall()
print(f"Total ir_asset rows in tcrm_master: {len(rows)}")
for r in rows:
    if 'zoom' in str(r) or 'mega' in str(r) or 'tcrm' in str(r):
        print("  MATCHING ASSET:", r)
conn.close()
