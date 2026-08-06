import os
import sys
import subprocess
import psycopg2

PROJECT_ROOT = r"d:\tcrm"
TCRM_SRC = r"d:\crm\tcrm-src"
PYTHON_BIN = os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe")
TCRM_BIN = os.path.join(TCRM_SRC, "tcrm-bin")
CONF_PATH = os.path.join(PROJECT_ROOT, "tcrm.conf")

MASTER_DB = "tcrm_master"
TENANT_DB = "akod_prod"
TENANT_NAME = "AK KOD YAZILIM BİLİŞİM LTD. ŞTİ."
TENANT_BRAND = "AK KOD"
DOMAIN_NAME = "akod.tcrm.online"
SUPPORT_EMAIL = "info@akod.tech"
SUPPORT_PHONE = "05525242866"
WEBSITE_URL = "https://akod.tech/"

ALL_MODULES = [
    "base", "web", "mail", "contacts", "crm", "sale", "website",
    "tcrm_propertio", "tcrm_ai", "tcrm_ai_research", "tcrm_call_center",
    "tcrm_market_analysis", "tcrm_marketing_hub", "tcrm_research_hub",
    "tcrm_vector_sync", "tcrm_web_enhance", "tcrm_web_enhance_sale",
    "tcrm_org", "tcrm_offer", "custom_crm_integration", "meta_leads", "theme_tcrm",
    "whatsapp_business_integration"
]

def run_cmd(cmd_list, env=None):
    print(f"Running: {' '.join(cmd_list)}")
    res = subprocess.run(cmd_list, capture_output=True, text=True, env=env or os.environ.copy(), cwd=PROJECT_ROOT)
    if res.returncode != 0:
        print(f"STDOUT:\n{res.stdout[-2000:]}")
        print(f"STDERR:\n{res.stderr[-2000:]}")
        raise RuntimeError(f"Command failed with code {res.returncode}")
    print(f"Command succeeded.")
    return res.stdout

def init_master_tenant_record():
    print("--- 1. Registering AK KOD Master Tenant in tcrm_master ---")
    conn = psycopg2.connect('dbname=tcrm_master user=odoo password=odoo host=localhost')
    conn.autocommit = True
    cur = conn.cursor()
    
    # Get Master company_id in tcrm_master
    cur.execute("SELECT id FROM res_company ORDER BY id ASC LIMIT 1;")
    company_id = cur.fetchone()[0]
    print(f"Using Master company_id = {company_id}")
    
    # Check if tenant already exists
    cur.execute("SELECT id FROM tcrm_tenant WHERE db_name = %s OR name = %s;", (TENANT_DB, TENANT_NAME))
    row = cur.fetchone()
    if row:
        tenant_id = row[0]
        print(f"Existing tenant found with ID {tenant_id}, updating...")
        cur.execute("""
            UPDATE tcrm_tenant
            SET name = %s, client_name = %s, state = 'active', company_id = %s, support_email = %s, support_phone = %s
            WHERE id = %s;
        """, (TENANT_NAME, TENANT_BRAND, company_id, SUPPORT_EMAIL, SUPPORT_PHONE, tenant_id))
    else:
        print("Creating new tenant record in tcrm_tenant...")
        cur.execute("""
            INSERT INTO tcrm_tenant (name, client_name, state, active, create_date, write_date, company_id, db_name, support_email, support_phone)
            VALUES (%s, %s, 'active', true, NOW(), NOW(), %s, %s, %s, %s)
            RETURNING id;
        """, (TENANT_NAME, TENANT_BRAND, company_id, TENANT_DB, SUPPORT_EMAIL, SUPPORT_PHONE))
        tenant_id = cur.fetchone()[0]
        print(f"Created tenant ID {tenant_id}")
        
    # Bind domain
    cur.execute("SELECT id FROM tcrm_tenant_domain WHERE domain = %s;", (DOMAIN_NAME,))
    dom_row = cur.fetchone()
    if dom_row:
        print(f"Domain {DOMAIN_NAME} already exists (ID {dom_row[0]}).")
        cur.execute("UPDATE tcrm_tenant_domain SET tenant_id = %s, is_primary = true, active = true WHERE id = %s;", (tenant_id, dom_row[0]))
    else:
        print(f"Creating domain {DOMAIN_NAME} for tenant ID {tenant_id}...")
        cur.execute("""
            INSERT INTO tcrm_tenant_domain (tenant_id, domain, is_primary, active, verified, ssl_status, create_date, write_date)
            VALUES (%s, %s, true, true, true, 'active', NOW(), NOW());
        """, (tenant_id, DOMAIN_NAME))
        
    conn.close()
    print("Master tenant record initialized successfully.")

def create_pg_database():
    print(f"--- 2. Creating PostgreSQL Database {TENANT_DB} ---")
    conn = psycopg2.connect('dbname=postgres user=odoo password=odoo host=localhost')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (TENANT_DB,))
    if cur.fetchone():
        print(f"Database {TENANT_DB} already exists.")
    else:
        print(f"Creating database {TENANT_DB}...")
        cur.execute(f'CREATE DATABASE "{TENANT_DB}" OWNER odoo ENCODING \'UTF8\';')
        print(f"Database {TENANT_DB} created.")
    conn.close()

def install_modules_to_db(db_name, modules):
    print(f"--- 3. Installing Modules to {db_name} ---")
    env = os.environ.copy()
    env["PYTHONPATH"] = TCRM_SRC
    modules_csv = ",".join(modules)
    
    cmd = [
        PYTHON_BIN, TCRM_BIN,
        "-c", CONF_PATH,
        "-d", db_name,
        "-i", modules_csv,
        "--stop-after-init",
        "--without-demo=all",
        "--load-language=tr_TR",
        "--log-level=warn"
    ]
    run_cmd(cmd, env=env)
    print(f"Modules installed successfully in {db_name}.")

def apply_branding_to_tenant():
    print(f"--- 4. Applying AK KOD Branding to {TENANT_DB} ---")
    env = os.environ.copy()
    env["PYTHONPATH"] = TCRM_SRC
    
    branding_code = f"""import os, sys
sys.path.insert(0, r"{TCRM_SRC}")
import tcrm
from tcrm.tools import config as odoo_config
odoo_config.parse_config(['-c', r"{CONF_PATH}"])
from tcrm.modules.module import initialize_sys_path
initialize_sys_path()

from tcrm.modules.registry import Registry
from tcrm import api, SUPERUSER_ID

registry = Registry('{TENANT_DB}')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {{}})
    company = env.company
    company.sudo().write({{
        'name': '{TENANT_NAME}',
        'phone': '{SUPPORT_PHONE}',
        'email': '{SUPPORT_EMAIL}',
        'website': '{WEBSITE_URL}',
        'street': 'Karanfil Sokak No:13',
        'city': 'Besiktas',
        'zip': '34330',
        'social_facebook': 'https://www.facebook.com/akkoddijital',
        'social_linkedin': 'https://www.linkedin.com/company/ak-kod/',
        'social_instagram': 'https://www.instagram.com/akkod_yazilim/',
    }})
    print("Updated company:", company.name.encode('ascii', 'ignore').decode())
    
    website = env['website'].search([], limit=1)
    if website:
        website.sudo().write({{
            'name': 'AK KOD TCRM',
            'social_facebook': 'https://www.facebook.com/akkoddijital',
            'social_linkedin': 'https://www.linkedin.com/company/ak-kod/',
            'social_instagram': 'https://www.instagram.com/akkod_yazilim/',
        }})
        print("Updated website:", website.name.encode('ascii', 'ignore').decode())
        
    admin = env.ref('base.user_admin', raise_if_not_found=False) or env['res.users'].search([('login', '=', 'admin')], limit=1)
    if admin:
        admin.sudo().write({{
            'name': 'AK KOD Admin',
            'email': '{SUPPORT_EMAIL}',
        }})
        print("Updated admin user:", admin.login)
        
    cr.commit()
print("Branding applied successfully!")
"""
    tmp_path = os.path.join(PROJECT_ROOT, "scratch", "_apply_akod_branding.py")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(branding_code)
        
    run_cmd([PYTHON_BIN, tmp_path], env=env)

if __name__ == "__main__":
    print("=== Starting AK KOD Production Master Tenant Provisioning ===")
    init_master_tenant_record()
    create_pg_database()
    install_modules_to_db(TENANT_DB, ALL_MODULES)
    apply_branding_to_tenant()
    print("=== Provisioning Completed Successfully! ===")
