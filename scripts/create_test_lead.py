#!/usr/bin/env python3
"""
Create a test lead with creative data manually
"""
import odoorpc
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def create_test_lead_with_creative():
    """Create a test lead with creative data"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    Lead = odoo.env['crm.lead']
    
    # Create lead with creative data
    lead_data = {
        'name': 'Test Lead with Creative',
        'email_from': 'test@example.com',
        'phone': '+1234567890',
        'description': 'Test lead created with Meta creative data',
        'meta_creative_id': '1774137209928613',
        'meta_creative_type': 'image', 
        'meta_creative_media_url': 'https://scontent.fada1-14.fna.fbcdn.net/v/t15.13418-10/482685948_625808200236588_2390073536849632317_n.jpg?_nc_cat=104&ccb=1-7&_nc_ohc=tVjfdgBqVPQQ7kNvwEiFI4A&_nc_oc=AdlRCmEqsDVAk-DgtdnO59F9xWBbct8f9E8L-Ze6bPNQKbTJaiXwoj4yxU5yA8MOdi4&_nc_zt=23&_nc_ht=scontent.fada1-14.fna&edm=AAT1rw8EAAAA&_nc_gid=j7unlFfL5rqAr3nsY2yM1w&_nc_tpa=Q5bMBQHqesXoTomA5FHPZ20egCXzXRcKV00zespSc__Fz70eRNggs2t9D2JqNrRFo8q2Kbr_vgBOKhQFtA&stp=c0.5000x0.5000f_dst-emg0_p64x64_q75_tt6&ur=c3b633&_nc_sid=58080a&oh=00_AfgAQtDkY3Nbcd9EkPyk3DmTg74hYdJBq4zNvdJE8YTRIQ&oe=691761BC',
        'meta_creative_title': 'Sample Creative Title',
        'meta_creative_body': 'This is a sample creative body text that shows in the ad.',
        'meta_creative_cta': 'Learn More'
    }
    
    try:
        lead = Lead.create(lead_data)
        print(f'✅ Created test lead with ID: {lead}')
        
        # Verify the data
        created_lead = Lead.browse(lead)
        print(f'\\nLead Details:')
        print(f'  Name: {created_lead.name}')
        print(f'  Creative ID: {created_lead.meta_creative_id}')
        print(f'  Creative Type: {created_lead.meta_creative_type}')
        print(f'  Media URL: {created_lead.meta_creative_media_url[:100]}...')
        print(f'  Title: {created_lead.meta_creative_title}')
        print(f'  Body: {created_lead.meta_creative_body}')
        print(f'  CTA: {created_lead.meta_creative_cta}')
        
        print(f'\\n🎉 SUCCESS! Now open Odoo CRM and check lead "{created_lead.name}"')
        print(f'   You should see a "Meta Creative" tab with all the creative information!')
        
    except Exception as e:
        print(f'❌ Error creating lead: {e}')

if __name__ == '__main__':
    create_test_lead_with_creative()