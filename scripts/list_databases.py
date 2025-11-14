#!/usr/bin/env python3
"""List available databases"""

import odoorpc

try:
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    
    # List databases
    db_list = odoo.db.list()
    print("Available databases:")
    for db in db_list:
        print(f"  - {db}")
        
except Exception as e:
    print(f'Connection error: {e}')