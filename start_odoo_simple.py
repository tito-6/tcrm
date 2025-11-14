#!/usr/bin/env python3
"""Simple Odoo startup script with minimal dependencies"""

import sys
import os

# Add the odoo directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'odoo'))

try:
    # Try to import and start Odoo
    import odoo
    
    # Set up basic configuration
    config_args = [
        '--addons-path=custom_addons,odoo/addons',
        '--database=crm_db',
        '--db-filter=^crm_db$',
        '--http-port=8069',
        '--workers=0',  # Single process mode
        '--no-database-list',
        '--update=custom_crm_integration'
    ]
    
    # Start Odoo
    sys.argv = ['odoo-bin'] + config_args
    odoo.cli.main()
    
except ImportError as e:
    print(f"Error importing Odoo: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)
except Exception as e:
    print(f"Error starting Odoo: {e}")
    sys.exit(1)