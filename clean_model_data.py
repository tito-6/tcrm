import psycopg2

for db in ['akod_prod', 'tcrm_master', 'tcrm_db', 'tcrm']:
    print(f"=== Cleaning ir_model_data in {db} ===")
    try:
        conn = psycopg2.connect(dbname=db, user='odoo', password='odoo', host='localhost')
        cur = conn.cursor()
        
        # Delete broken ir_model_data records
        cur.execute("DELETE FROM ir_model_data WHERE name LIKE '%zoomtcrm%' OR name LIKE '%s_mega_menu_tcrm_menu%';")
        print(f"Deleted {cur.rowcount} ir_model_data rows in {db}")
        
        # Delete broken ir_asset records
        cur.execute("DELETE FROM ir_asset WHERE path LIKE '%zoomtcrm%' OR path LIKE '%s_mega_menu_tcrm_menu%';")
        print(f"Deleted {cur.rowcount} ir_asset rows in {db}")
        
        # Delete broken ir_ui_view records
        cur.execute("DELETE FROM ir_ui_view WHERE arch_db::text LIKE '%zoomtcrm%' OR arch_db::text LIKE '%s_mega_menu_tcrm_menu%';")
        print(f"Deleted {cur.rowcount} ir_ui_view rows in {db}")
        
        # Delete all cached asset attachments
        cur.execute("DELETE FROM ir_attachment WHERE url LIKE '%/assets/%' OR name LIKE '%assets%' OR name LIKE '%.css' OR name LIKE '%.js';")
        print(f"Deleted {cur.rowcount} cached asset attachment rows in {db}")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error on {db}: {e}")

print("Successfully cleaned ir_model_data across all databases!")
