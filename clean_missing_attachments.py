import os
import psycopg2

for db in ['akod_prod', 'tcrm_master', 'tcrm_db', 'tcrm']:
    try:
        conn = psycopg2.connect(dbname=db, user='odoo', password='odoo', host='localhost')
        cur = conn.cursor()
        cur.execute("SELECT id, name, store_fname, res_model, res_id, res_field FROM ir_attachment WHERE store_fname IS NOT NULL;")
        rows = cur.fetchall()
        filestore_base = os.path.join(r"C:\Users\sheha\AppData\Local\TCRM\tcrm\filestore", db)
        missing_ids = []
        for r_id, name, store_fname, model, res_id, field in rows:
            full_path = os.path.join(filestore_base, store_fname.replace('/', os.sep))
            if not os.path.exists(full_path):
                missing_ids.append(r_id)
        
        print(f"[{db}] Total attachments with store_fname: {len(rows)}, Missing on disk: {len(missing_ids)}")
        if missing_ids:
            # Delete attachment records whose files were lost on disk
            cur.execute("DELETE FROM ir_attachment WHERE id = ANY(%s)", (missing_ids,))
            print(f"[{db}] Deleted {cur.rowcount} missing attachment records from database.")
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[{db}] Error: {e}")
