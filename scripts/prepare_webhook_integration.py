#!/usr/bin/env python3
"""
Safe Webhook Integration Script
Integrates Meta/Google webhook system with Odoo CRM safely
"""

import os
import shutil
import json
from pathlib import Path

# Paths
WEBHOOK_REPO = Path("C:/D/webhook-integration")
ODOO_WORKSPACE = Path("C:/D/crm")
ADDONS_SOURCE = WEBHOOK_REPO / "extra_addons"
ADDONS_TARGET = ODOO_WORKSPACE / "custom-addons"

def update_manifest_version(manifest_path):
    """Update module version from 18.0 to 17.0"""
    content = manifest_path.read_text(encoding='utf-8')
    
    # Replace version strings
    content = content.replace('"version": "18.0.1.0.0"', '"version": "17.0.1.0.0"')
    content = content.replace("'version': '18.0.1.0.0'", "'version': '17.0.1.0.0'")
    
    manifest_path.write_text(content, encoding='utf-8')
    print(f"✓ Updated version in {manifest_path.name}")

def copy_addon_safely(addon_name):
    """Copy addon from webhook repo to Odoo custom-addons"""
    source = ADDONS_SOURCE / addon_name
    target = ADDONS_TARGET / addon_name
    
    if not source.exists():
        print(f"✗ Source addon not found: {source}")
        return False
    
    # Remove target if exists
    if target.exists():
        shutil.rmtree(target)
        print(f"  Removed existing: {target}")
    
    # Copy addon
    shutil.copytree(source, target)
    print(f"✓ Copied {addon_name} to {target}")
    
    # Update manifest version
    manifest = target / "__manifest__.py"
    if manifest.exists():
        update_manifest_version(manifest)
    
    return True

def verify_env_variables():
    """Check if required environment variables are set"""
    env_file = ODOO_WORKSPACE / ".env"
    
    if not env_file.exists():
        print("✗ .env file not found")
        return False
    
    required_vars = [
        'META_APP_ID',
        'META_APP_SECRET',
        'META_USER_ACCESS_TOKEN',
        'GOOGLE_DEVELOPER_TOKEN',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET'
    ]
    
    env_content = env_file.read_text()
    missing = []
    
    for var in required_vars:
        if var not in env_content or f"{var}=" in env_content and env_content.split(f"{var}=")[1].split('\n')[0].strip() == '':
            missing.append(var)
    
    if missing:
        print(f"⚠ Missing or empty environment variables: {', '.join(missing)}")
        return False
    
    print("✓ All required environment variables are set")
    return True

def create_backup_instructions():
    """Create backup instructions file"""
    instructions = """
# Database Backup Instructions

## Before Installing Addons

### Option 1: Full Reset (Simple)
If you're okay losing current data and starting fresh:
```bash
docker compose down
docker volume rm crm_odoo-db-data crm_odoo-web-data
docker compose up -d
```

### Option 2: Database Backup (Preserve Data)
To backup your current database:

1. Access Odoo Database Manager:
   http://localhost:8069/web/database/manager
   
2. Enter master password: 69b7-e2u4-jypu

3. Click "Backup" next to 'crm' database

4. Download the backup file (crm_backup.zip)

5. Store safely before proceeding with addon installation

### Option 3: Docker Volume Backup
```bash
# Stop Odoo (keep volumes)
docker compose stop odoo

# Create backup
docker run --rm -v crm_odoo-db-data:/source -v C:/D/backups:/backup alpine tar czf /backup/odoo-db-backup.tar.gz -C /source .
docker run --rm -v crm_odoo-web-data:/source -v C:/D/backups:/backup alpine tar czf /backup/odoo-web-backup.tar.gz -C /source .

# Restart Odoo
docker compose start odoo
```

## Restoration

If something goes wrong:

### From Odoo Backup:
1. Go to: http://localhost:8069/web/database/manager
2. Click "Restore Database"
3. Upload your backup file
4. Enter master password and restore

### From Volume Backup:
```bash
docker compose down
docker volume rm crm_odoo-db-data crm_odoo-web-data
docker volume create crm_odoo-db-data
docker volume create crm_odoo-web-data
docker run --rm -v crm_odoo-db-data:/target -v C:/D/backups:/backup alpine tar xzf /backup/odoo-db-backup.tar.gz -C /target
docker run --rm -v crm_odoo-web-data:/target -v C:/D/backups:/backup alpine tar xzf /backup/odoo-web-backup.tar.gz -C /target
docker compose up -d
```
"""
    
    backup_file = ODOO_WORKSPACE / "BACKUP_INSTRUCTIONS.md"
    backup_file.write_text(instructions)
    print(f"✓ Created backup instructions: {backup_file}")

def create_installation_script():
    """Create step-by-step installation script"""
    script = """#!/usr/bin/env python3
'''
Step-by-step addon installation with UI verification
'''

import odoorpc
import time

HOST = 'localhost'
PORT = 8069
DB = 'crm'
USER = 'admin'
PASSWORD = 'admin'

def connect_odoo():
    odoo = odoorpc.ODOO(HOST, port=PORT)
    odoo.login(DB, USER, PASSWORD)
    return odoo

def install_module(odoo, module_name):
    '''Install a single module and wait for completion'''
    print(f"\\n{'='*60}")
    print(f"Installing module: {module_name}")
    print('='*60)
    
    Module = odoo.env['ir.module.module']
    
    # Update module list first
    print("Updating module list...")
    Module.update_list()
    time.sleep(2)
    
    # Find module
    module_ids = Module.search([('name', '=', module_name)])
    if not module_ids:
        print(f"✗ Module '{module_name}' not found")
        return False
    
    module = Module.browse(module_ids[0])
    state = module.state
    
    if state == 'installed':
        print(f"✓ Module already installed")
        return True
    
    print(f"Current state: {state}")
    print("Installing...")
    
    try:
        Module.button_immediate_install([module.id])
        print(f"✓ Installation completed")
        
        # Verify installation
        module.invalidate_cache()
        module = Module.browse(module_ids[0])
        if module.state == 'installed':
            print(f"✓ Verification passed - module is installed")
            return True
        else:
            print(f"⚠ Warning: Module state is {module.state}")
            return False
            
    except Exception as e:
        print(f"✗ Installation failed: {e}")
        return False

def verify_ui_accessible():
    '''Check if Odoo UI is still accessible'''
    import requests
    try:
        response = requests.get(f'http://{HOST}:{PORT}/web/login', timeout=5)
        if response.status_code == 200:
            print("✓ Odoo UI is accessible")
            return True
        else:
            print(f"⚠ UI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ UI check failed: {e}")
        return False

def main():
    print("="*60)
    print("SAFE ADDON INSTALLATION WIZARD")
    print("="*60)
    
    input("\\nPress Enter to verify UI is working before starting...")
    if not verify_ui_accessible():
        print("\\n✗ UI is not accessible. Fix this before proceeding.")
        return
    
    print("\\n✓ UI is working. Connecting to Odoo...")
    
    try:
        odoo = connect_odoo()
        print(f"✓ Connected to Odoo")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Install modules in safe order
    modules = [
        ('meta_leads', 'Meta Lead Management - adds custom fields to CRM'),
        ('webhooks_bridge', 'Webhook Endpoints - exposes /webhooks/meta and /webhooks/google'),
    ]
    
    for module_name, description in modules:
        print(f"\\n{description}")
        proceed = input(f"Install '{module_name}'? (y/n): ").strip().lower()
        
        if proceed != 'y':
            print(f"Skipping {module_name}")
            continue
        
        success = install_module(odoo, module_name)
        
        if not success:
            print(f"\\n✗ Installation of {module_name} failed")
            retry = input("Continue anyway? (y/n): ").strip().lower()
            if retry != 'y':
                print("Installation aborted")
                return
        
        print("\\nVerifying UI accessibility...")
        time.sleep(2)
        
        if not verify_ui_accessible():
            print("\\n⚠ WARNING: UI may not be accessible after installing {module_name}")
            print("Check the logs and consider rollback")
            return
        
        print("✓ UI still working after installation")
        input("\\nPress Enter to continue to next module...")
    
    print("\\n" + "="*60)
    print("INSTALLATION COMPLETE")
    print("="*60)
    print("\\nPlease verify:")
    print("1. Open http://localhost:8069 in browser")
    print("2. Login with admin/admin")
    print("3. Check CRM > Leads menu")
    print("4. Look for Meta Lead fields")
    print("5. Check Settings > Technical > Webhooks")

if __name__ == '__main__':
    main()
"""
    
    install_script = ODOO_WORKSPACE / "scripts" / "safe_install_webhooks.py"
    install_script.write_text(script, encoding='utf-8')
    print(f"✓ Created installation script: {install_script}")

def main():
    print("="*70)
    print("SAFE WEBHOOK INTEGRATION PREPARATION")
    print("="*70)
    
    # Create custom-addons directory
    ADDONS_TARGET.mkdir(exist_ok=True)
    print(f"✓ Custom addons directory ready: {ADDONS_TARGET}")
    
    # Verify environment variables
    print("\n1. Verifying environment variables...")
    verify_env_variables()
    
    # Copy addons
    print("\n2. Copying webhook addons...")
    success_meta = copy_addon_safely("meta_leads")
    success_webhook = copy_addon_safely("webhooks_bridge")
    
    if success_meta and success_webhook:
        print("\n✓ All addons copied successfully")
    else:
        print("\n✗ Some addons failed to copy")
        return
    
    # Create helper files
    print("\n3. Creating helper documentation...")
    create_backup_instructions()
    create_installation_script()
    
    print("\n" + "="*70)
    print("PREPARATION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Review: C:\\D\\crm\\WEBHOOK_INTEGRATION_PLAN.md")
    print("2. Backup: Follow C:\\D\\crm\\BACKUP_INSTRUCTIONS.md")
    print("3. Update docker-compose.yml to pass environment variables")
    print("4. Run: python scripts\\safe_install_webhooks.py")
    print("\n⚠ DO NOT proceed without backing up your database!")

if __name__ == '__main__':
    main()
