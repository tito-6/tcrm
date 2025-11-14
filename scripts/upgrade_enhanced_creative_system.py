#!/usr/bin/env python3
"""
Enhanced Creative Fetching System - Module Upgrade Script

This script restarts Odoo and upgrades the custom_crm_integration module
to enable the new high-resolution creative fetching capabilities.
"""

import subprocess
import time
import requests
import sys
import os

def check_odoo_running():
    """Check if Odoo is running on port 8069"""
    try:
        response = requests.get('http://localhost:8069', timeout=5)
        return response.status_code == 200
    except:
        return False

def kill_odoo_processes():
    """Kill any running Odoo processes"""
    try:
        # Kill processes on port 8069
        subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        
        # For Windows, find and kill processes using port 8069
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if ':8069' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], 
                                     capture_output=True, check=True)
                        print(f"✅ Killed process PID {pid}")
                    except:
                        pass
    except Exception as e:
        print(f"⚠️ Warning killing processes: {e}")

def start_odoo():
    """Start Odoo with the upgraded module"""
    print("🚀 Starting Odoo with enhanced creative fetching...")
    
    # Change to CRM directory
    os.chdir('c:/D/crm')
    
    # Start Odoo in background
    cmd = [
        'python', 'odoo/odoo-bin',
        '--addons-path=custom_addons,odoo/addons',
        '-d', 'crm_db',
        '--db-filter=^crm_db$',
        '-u', 'custom_crm_integration'  # Upgrade the module
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait a bit for startup
    print("⏳ Waiting for Odoo to start...")
    time.sleep(15)
    
    # Check if it's running
    if check_odoo_running():
        print("✅ Odoo started successfully!")
        print("🎯 Enhanced creative fetching system is now active!")
        print()
        print("🔗 Access your CRM at: http://localhost:8069/web")
        print("📋 Login credentials: admin / admin")
        print()
        print("✨ New Features Available:")
        print("   • High-resolution creative fetching")
        print("   • Dynamic ad support")  
        print("   • Video embed playback")
        print("   • Quality assessment badges")
        print("   • Advanced fallback strategies")
        return True
    else:
        print("❌ Failed to start Odoo")
        print("📋 Process output:")
        stdout, stderr = process.communicate(timeout=5)
        print("STDOUT:", stdout.decode()[:500])
        print("STDERR:", stderr.decode()[:500])
        return False

def main():
    print("=" * 60)
    print("ENHANCED META CREATIVE FETCHING - MODULE UPGRADE")
    print("=" * 60)
    print()
    
    print("1. Checking current Odoo status...")
    if check_odoo_running():
        print("✅ Odoo is running, will restart with upgrades")
        print("2. Stopping current Odoo processes...")
        kill_odoo_processes()
        time.sleep(3)
    else:
        print("✅ No Odoo running, will start fresh")
    
    print("3. Starting Odoo with enhanced creative system...")
    success = start_odoo()
    
    if success:
        print()
        print("🎉 SUCCESS! Enhanced Creative Fetching System is now active!")
        print()
        print("📝 What's New:")
        print("   • 6-tier waterfall strategy for maximum resolution")
        print("   • Support for Dynamic Creative & Advantage+ Catalog ads")  
        print("   • Page Post fallback using effective_object_story_id")
        print("   • Asset feed spec parsing for dynamic assets")
        print("   • AdImage endpoint access for original resolution")
        print("   • Comprehensive video handling with embed_html")
        print("   • Real-time quality assessment and reporting")
        print()
        print("🚀 Test it now:")
        print("   1. Go to CRM > Leads")
        print("   2. Open any lead with Meta data") 
        print("   3. Click 'Meta Creative' tab")
        print("   4. Click 'Refresh Creative Data' button")
        print("   5. See high-resolution results with quality badges!")
    else:
        print()
        print("❌ Upgrade failed. Please check the error messages above.")
        print("💡 Try running manually:")
        print("   cd c:/D/crm")
        print("   python odoo/odoo-bin --addons-path=custom_addons,odoo/addons -d crm_db -u custom_crm_integration")

if __name__ == "__main__":
    main()