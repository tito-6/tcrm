import psycopg2
conn = psycopg2.connect("dbname=tcrm_master user=odoo password=odoo host=localhost port=5432")
cur = conn.cursor()
print("Deleting orphaned selection values...")
cur.execute("DELETE FROM ir_model_fields_selection WHERE field_id IN (SELECT id FROM ir_model_fields WHERE name='gemini_model');")
conn.commit()
print("Cleanup done.")
