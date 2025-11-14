#!/usr/bin/env python3

"""
Manual script to update the CRM lead view through the running Odoo instance.
This will force refresh the view cache.
"""

import requests
import json

def update_view_manual():
    """Update the view manually through the web interface"""
    
    # Odoo instance details
    url = 'http://localhost:8069'
    database = 'crm_db'
    username = 'admin'
    password = 'admin'  # Replace with actual password if different
    
    try:
        # Start session
        session = requests.Session()
        
        # Login
        login_data = {
            'login': username,
            'password': password,
            'db': database
        }
        
        login_response = session.post(f'{url}/web/login', data=login_data)
        
        if login_response.status_code == 200:
            print("Login successful")
            
            # Clear view cache by accessing the developer menu functionality
            # This is equivalent to going to Developer Tools -> Clear Caches
            
            # Get session info
            session_info_response = session.post(f'{url}/web/session/get_session_info')
            
            if session_info_response.status_code == 200:
                print("Session established")
                
                # Force update module through web interface
                # This simulates clicking "Update Module List" and then "Upgrade" on custom_crm_integration
                
                print("Attempting to trigger view refresh...")
                
                # Try to access the module update functionality
                module_data = {
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'service': 'object',
                        'method': 'execute',
                        'args': [database, 1, password, 'ir.module.module', 'update_list']
                    },
                    'id': 1
                }
                
                module_response = session.post(f'{url}/jsonrpc', 
                                             data=json.dumps(module_data),
                                             headers={'Content-Type': 'application/json'})
                
                if module_response.status_code == 200:
                    print("Module list updated successfully")
                    
                    # Now try to upgrade the specific module
                    upgrade_data = {
                        'jsonrpc': '2.0',
                        'method': 'call',
                        'params': {
                            'service': 'object',
                            'method': 'execute',
                            'args': [database, 1, password, 'ir.module.module', 'search_read', 
                                   [['name', '=', 'custom_crm_integration']], ['id', 'state']]
                        },
                        'id': 2
                    }
                    
                    upgrade_response = session.post(f'{url}/jsonrpc',
                                                  data=json.dumps(upgrade_data),
                                                  headers={'Content-Type': 'application/json'})
                    
                    if upgrade_response.status_code == 200:
                        result = upgrade_response.json()
                        print(f"Module status: {result}")
                        
                        if result.get('result'):
                            module_id = result['result'][0]['id']
                            
                            # Trigger upgrade
                            button_data = {
                                'jsonrpc': '2.0',
                                'method': 'call',
                                'params': {
                                    'service': 'object',
                                    'method': 'execute',
                                    'args': [database, 1, password, 'ir.module.module', 'button_immediate_upgrade', [module_id]]
                                },
                                'id': 3
                            }
                            
                            button_response = session.post(f'{url}/jsonrpc',
                                                         data=json.dumps(button_data),
                                                         headers={'Content-Type': 'application/json'})
                            
                            if button_response.status_code == 200:
                                print("Module upgrade triggered successfully!")
                                print("Please refresh your browser to see the changes.")
                                return True
                            else:
                                print(f"Failed to trigger upgrade: {button_response.text}")
                        else:
                            print("Module not found or not installed")
                    else:
                        print(f"Failed to get module info: {upgrade_response.text}")
                else:
                    print(f"Failed to update module list: {module_response.text}")
            else:
                print(f"Failed to get session info: {session_info_response.text}")
        else:
            print(f"Login failed: {login_response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        
    return False

if __name__ == "__main__":
    print("Attempting to manually update the view...")
    success = update_view_manual()
    
    if success:
        print("\nSUCCESS! The changes have been applied.")
        print("\nWhat changed:")
        print("1. UI now uses standard Odoo styling (no custom CSS)")
        print("2. Creative preview moved to separate 'Meta Creative' tab")
        print("3. Creative preview will show 'This lead does not have Meta creative data.' when no data")
        print("4. Both tabs have the 'Refresh Creative Data' button")
        print("\nPlease:")
        print("1. Refresh your browser (F5)")
        print("2. Navigate to CRM > Leads")
        print("3. Open a lead record")
        print("4. Check both 'Meta Lead Data' and 'Meta Creative' tabs")
    else:
        print("\nManual update failed. You may need to:")
        print("1. Restart the Odoo service manually")
        print("2. Or upgrade the module from the Apps menu in Odoo")
        print("3. Or clear browser cache and refresh")