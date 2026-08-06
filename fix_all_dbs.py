import psycopg2
import os

conn = psycopg2.connect(dbname='postgres', user='odoo', password='odoo', host='localhost')
cur = conn.cursor()
cur.execute("SELECT datname FROM pg_database WHERE datname NOT LIKE 'template%' AND datname != 'postgres';")
dbs = [r[0] for r in cur.fetchall()]
print("Found databases:", dbs)

for db in dbs:
    try:
        db_conn = psycopg2.connect(dbname=db, user='odoo', password='odoo', host='localhost')
        db_cur = db_conn.cursor()
        
        # Delete broken ir_asset records
        try:
            db_cur.execute("DELETE FROM ir_asset WHERE path LIKE '%zoomtcrm%' OR path LIKE '%s_mega_menu_tcrm_menu%';")
            print(f"[{db}] Deleted {db_cur.rowcount} broken ir_asset rows")
        except Exception as e:
            db_conn.rollback()
            
        # Delete broken ir_ui_view records containing zoomtcrm or s_mega_menu_tcrm_menu (casting jsonb to text)
        try:
            db_cur.execute("DELETE FROM ir_ui_view WHERE arch_db::text LIKE '%zoomtcrm%' OR arch_db::text LIKE '%s_mega_menu_tcrm_menu%';")
            print(f"[{db}] Deleted {db_cur.rowcount} broken ir_ui_view rows")
        except Exception as e:
            db_conn.rollback()
            
        # Delete all cached asset attachments
        try:
            db_cur.execute("DELETE FROM ir_attachment WHERE url LIKE '%/assets/%' OR name LIKE '%assets%' OR name LIKE '%.css' OR name LIKE '%.js';")
            print(f"[{db}] Deleted {db_cur.rowcount} cached asset attachment rows")
        except Exception as e:
            db_conn.rollback()
            
        db_conn.commit()
        db_conn.close()
        
    except Exception as e:
        print(f"Error connecting to {db}: {e}")

# Purge local filestore directory completely
filestore_base = r"C:\Users\sheha\AppData\Local\TCRM\tcrm\filestore"
if os.path.exists(filestore_base):
    import shutil
    for folder in os.listdir(filestore_base):
        fpath = os.path.join(filestore_base, folder)
        if os.path.isdir(fpath):
            print(f"Purging filestore: {fpath}")
            shutil.rmtree(fpath, ignore_errors=True)

print("All databases and filestores purged!")
