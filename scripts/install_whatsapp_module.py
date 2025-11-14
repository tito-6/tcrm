#!/usr/bin/env python3

"""
Install WhatsApp Business Integration Module
This script installs the new WhatsApp Business integration module in Odoo.
"""

import xmlrpc.client
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_whatsapp_module():
    """Install the WhatsApp Business integration module"""
    
    # Odoo connection settings
    url = 'http://localhost:8069'
    db = 'crm'
    username = 'admin'
    password = os.getenv('ODOO_ADMIN_PASSWORD', 'admin')
    
    try:
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        
        # Get Odoo version info
        version_info = common.version()
        logger.info(f"Connected to Odoo {version_info['server_version']}")
        
        # Authenticate
        uid = common.authenticate(db, username, password, {})
        if not uid:
            logger.error("Authentication failed")
            return False
        
        logger.info(f"Authenticated as user {username} (ID: {uid})")
        
        # Connect to object service
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Update module list first
        logger.info("Updating module list...")
        models.execute_kw(db, uid, password, 'ir.module.module', 'update_list', [])
        
        # Search for the WhatsApp Business Integration module
        module_name = 'whatsapp_business_integration'
        module_ids = models.execute_kw(db, uid, password, 'ir.module.module', 'search', 
                                     [[['name', '=', module_name]]])
        
        if not module_ids:
            logger.error(f"Module {module_name} not found")
            return False
        
        module_id = module_ids[0]
        logger.info(f"Found module {module_name} (ID: {module_id})")
        
        # Get module info
        module_info = models.execute_kw(db, uid, password, 'ir.module.module', 'read', 
                                      [module_id], {'fields': ['name', 'state', 'summary']})
        
        logger.info(f"Module state: {module_info[0]['state']}")
        
        if module_info[0]['state'] == 'installed':
            logger.info("Module is already installed")
            return True
        
        # Install the module
        logger.info(f"Installing module {module_name}...")
        models.execute_kw(db, uid, password, 'ir.module.module', 'button_immediate_install', 
                         [module_id])
        
        # Check installation status
        updated_info = models.execute_kw(db, uid, password, 'ir.module.module', 'read', 
                                       [module_id], {'fields': ['state']})
        
        if updated_info[0]['state'] == 'installed':
            logger.info("Module installed successfully!")
            return True
        else:
            logger.error(f"Installation failed. Module state: {updated_info[0]['state']}")
            return False
            
    except Exception as e:
        logger.error(f"Error installing module: {str(e)}")
        return False

def verify_installation():
    """Verify the installation by checking for new models"""
    
    # Odoo connection settings
    url = 'http://localhost:8069'
    db = 'crm'
    username = 'admin'
    password = os.getenv('ODOO_ADMIN_PASSWORD', 'admin')
    
    try:
        # Connect to Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Check if WhatsApp models exist
        whatsapp_models = [
            'whatsapp.message',
            'whatsapp.conversation',
            'whatsapp.message.wizard'
        ]
        
        for model_name in whatsapp_models:
            try:
                # Try to access the model
                model_info = models.execute_kw(db, uid, password, model_name, 'search_count', [[]])
                logger.info(f"✓ Model {model_name} is available (records: {model_info})")
            except Exception as e:
                logger.error(f"✗ Model {model_name} not found: {str(e)}")
                return False
        
        logger.info("All WhatsApp models are available!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying installation: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting WhatsApp Business Integration module installation...")
    
    if install_whatsapp_module():
        logger.info("Installation completed successfully!")
        
        # Verify installation
        logger.info("Verifying installation...")
        if verify_installation():
            logger.info("Installation verification successful!")
        else:
            logger.warning("Installation verification failed")
    else:
        logger.error("Installation failed")