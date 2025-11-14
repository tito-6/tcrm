#!/usr/bin/env python3
"""
Demonstrate campaign tracking by adding sample campaign data to existing Meta leads
"""
import odoorpc
import random

def add_sample_campaign_data():
    """Add sample campaign data to existing Meta leads"""
    try:
        # Connect to Odoo
        print("Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✓ Connected")
        
        Lead = odoo.env['crm.lead']
        
        # Get some Meta leads
        meta_leads = Lead.search([('meta_leadgen_id', '!=', False)], limit=5)
        
        print(f"\n{'='*70}")
        print(f"ADDING SAMPLE CAMPAIGN DATA TO {len(meta_leads)} LEADS")
        print('='*70)
        
        # Sample campaign data
        campaigns = [
            {
                'campaign_id': 'CAMP_001_2025',
                'campaign_name': 'Model Sanayi - Real Estate Lead Gen 2025',
                'adset_id': 'ADSET_001_TR',
                'adset_name': 'Turkey Property Seekers 25-45',
                'ad_id': 'AD_001_PROP',
                'ad_name': 'Luxury Properties Istanbul - Lead Form',
                'source': 'facebook',
                'medium': 'facebook_ads'
            },
            {
                'campaign_id': 'CAMP_002_2025',
                'campaign_name': 'Model Kuyum - Jewelry Collection Campaign',
                'adset_id': 'ADSET_002_TR',
                'adset_name': 'Jewelry Lovers Istanbul',
                'ad_id': 'AD_002_JEWEL',
                'ad_name': 'Premium Gold Collection - Contact Form',
                'source': 'facebook',
                'medium': 'facebook_ads'
            },
            {
                'campaign_id': 'CAMP_003_2025',
                'campaign_name': 'Model Sanayi - Commercial Properties',
                'adset_id': 'ADSET_003_TR',
                'adset_name': 'Business Investors Turkey',
                'ad_id': 'AD_003_COMM',
                'ad_name': 'Commercial Real Estate Opportunities',
                'source': 'facebook',
                'medium': 'facebook_ads'
            }
        ]
        
        updated_count = 0
        
        for i, lead_id in enumerate(meta_leads):
            lead = Lead.browse(lead_id)
            
            # Select random campaign data
            campaign_data = random.choice(campaigns)
            
            print(f"\n📧 Updating Lead: {lead.name}")
            print(f"   Meta ID: {getattr(lead, 'meta_leadgen_id', 'N/A')}")
            print(f"   Email: {getattr(lead, 'email_from', 'N/A')}")
            
            # Update with campaign data
            update_vals = {
                'meta_campaign_id': campaign_data['campaign_id'],
                'meta_campaign_name': campaign_data['campaign_name'],
                'meta_adset_id': campaign_data['adset_id'],
                'meta_adset_name': campaign_data['adset_name'],
                'meta_ad_id': campaign_data['ad_id'],
                'meta_ad_name': campaign_data['ad_name'],
                'meta_source': campaign_data['source'],
                'meta_medium': campaign_data['medium']
            }
            
            lead.write(update_vals)
            
            print(f"   ✅ Campaign: {campaign_data['campaign_name']}")
            print(f"   ✅ Ad Set: {campaign_data['adset_name']}")
            print(f"   ✅ Ad: {campaign_data['ad_name']}")
            
            updated_count += 1
        
        print(f"\n{'='*70}")
        print("CAMPAIGN DATA UPDATE COMPLETE!")
        print('='*70)
        print(f"✅ Updated {updated_count} leads with campaign tracking data")
        print(f"📊 Each lead now has:")
        print(f"   - Campaign ID & Name")
        print(f"   - Ad Set ID & Name") 
        print(f"   - Ad ID & Name")
        print(f"   - Source: facebook")
        print(f"   - Medium: facebook_ads")
        
        print(f"\n🔗 View Results:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list&cids=1&menu_id=149")
        print(f"\n💡 New Columns Available:")
        print(f"   - Campaign (shows campaign name)")
        print(f"   - Source (shows 'facebook')")
        print(f"   - Medium (shows 'facebook_ads')")
        print(f"   - Click settings icon to enable these columns")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating leads: {e}")
        return False

if __name__ == '__main__':
    add_sample_campaign_data()