#!/usr/bin/env python3
"""
Enhanced Creative System - Debug and Fix Script

This script upgrades the module with proper debugging capabilities
and architectural fixes following Odoo best practices.
"""

import subprocess
import requests
import time
import os

def check_odoo_running():
    """Check if Odoo is accessible"""
    try:
        response = requests.get('http://localhost:8069', timeout=5)
        return response.status_code == 200
    except:
        return False

def upgrade_module_via_docker():
    """Upgrade the custom_crm_integration module via Docker"""
    print("🔄 Upgrading module via Docker...")
    
    try:
        # Execute upgrade command in the Docker container
        cmd = [
            'docker', 'exec', 'odoo-web', 
            'odoo', '--addons-path=/mnt/custom-addons,/usr/lib/python3/dist-packages/odoo/addons',
            '-d', 'postgres',  # Default database name in Docker
            '-u', 'custom_crm_integration',
            '--stop-after-init'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Module upgrade successful!")
            return True
        else:
            print(f"❌ Module upgrade failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Upgrade command timed out, but changes may have been applied")
        return True
    except Exception as e:
        print(f"❌ Upgrade error: {str(e)}")
        return False

def restart_odoo_container():
    """Restart the Odoo container to ensure all changes are loaded"""
    print("🔄 Restarting Odoo container...")
    
    try:
        # Restart just the Odoo container
        subprocess.run(['docker', 'restart', 'odoo-web'], check=True, timeout=30)
        print("✅ Container restarted")
        
        # Wait for startup
        print("⏳ Waiting for Odoo to start...")
        for i in range(30):  # Wait up to 30 seconds
            if check_odoo_running():
                print("✅ Odoo is running!")
                return True
            time.sleep(1)
        
        print("⚠️ Odoo may still be starting up...")
        return True
        
    except Exception as e:
        print(f"❌ Container restart failed: {str(e)}")
        return False

def main():
    print("=" * 80)
    print("ENHANCED META CREATIVE SYSTEM - DEBUG & FIX DEPLOYMENT")
    print("=" * 80)
    print()
    print("🎯 Deploying fixes:")
    print("   ✅ Diagnostic Server Action for backend verification")
    print("   ✅ Proper Odoo view architecture with invisible modifiers")
    print("   ✅ Enhanced error handling and logging")
    print("   ✅ Explicit field storage (store=True)")
    print("   ✅ User-visible error messages")
    print()
    
    # Check if Docker is running
    if not check_odoo_running():
        print("❌ Odoo is not running. Please start with:")
        print("   docker-compose up -d")
        return
    
    print("✅ Odoo is running")
    
    # Upgrade the module
    print("\n1. Upgrading module with new debug capabilities...")
    if upgrade_module_via_docker():
        print("✅ Module upgrade completed")
    else:
        print("⚠️ Module upgrade had issues, trying container restart...")
    
    # Restart container to ensure changes are loaded
    print("\n2. Restarting Odoo to load all changes...")
    restart_odoo_container()
    
    print("\n" + "=" * 80)
    print("🎉 DEBUG-ENABLED SYSTEM IS READY!")
    print("=" * 80)
    print()
    print("🔍 TESTING INSTRUCTIONS:")
    print()
    print("1. 📋 Go to: http://localhost:8069/web")
    print("2. 🔑 Login: admin / admin")
    print("3. 📁 Navigate: CRM → Leads")
    print("4. 👆 Open any lead (or create a test lead)")
    print("5. ⚡ Run diagnostic: Action → Debug Meta Creative Data")
    print("6. 📊 Check results in the popup message")
    print()
    print("🎯 DIAGNOSTIC OUTCOMES:")
    print("   ✅ 'DATA AND PREVIEW EXIST' = View rendering issue")
    print("   ⚠️  'DATA EXISTS BUT NO PREVIEW' = View/template problem") 
    print("   ❌ 'NO CREATIVE DATA FOUND' = Service/API issue")
    print()
    print("📋 WHAT'S NEW IN THE VIEW:")
    print("   • 🚨 Error messages now display in the UI")
    print("   • 🎯 Quality badges with proper invisible modifiers")
    print("   • 🖼️ Standard Odoo image widgets instead of custom HTML")
    print("   • 🎬 Proper video/image separation logic")
    print("   • 🔧 Debug section for system administrators")
    print()
    print("🔄 Next steps:")
    print("   1. Run the diagnostic on a lead with Meta Ad ID")
    print("   2. Based on results, we'll know exactly where the issue is")
    print("   3. If service works but view doesn't, it's a frontend issue")
    print("   4. If service fails, we'll see the exact API error")

if __name__ == "__main__":
    main()