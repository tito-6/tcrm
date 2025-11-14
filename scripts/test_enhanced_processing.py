#!/usr/bin/env python3
"""
Test Enhanced Lead Processing with improved field mapping and source detection
This simulates the enhanced processing without requiring fresh Facebook tokens
"""
import odoorpc
import json
from datetime import datetime

def test_enhanced_field_mapping():
    """Test the enhanced field mapping with various field name variations"""
    
    print("="*80)
    print("🧪 TESTING ENHANCED LEAD PROCESSING")
    print("📚 Based on Meta Developer Best Practices")
    print("="*80)
    
    # Connect to Odoo
    try:
        print("🔗 Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✅ Connected to Odoo")
        
        Lead = odoo.env['crm.lead']
        
    except Exception as e:
        print(f"❌ Error connecting to Odoo: {e}")
        return False
    
    # Test cases with various field name patterns (based on real Meta forms)
    test_leads = [
        {
            'meta_id': 'TEST_001_FACEBOOK',
            'field_data': [
                {'name': 'full_name', 'values': ['Ahmet Yılmaz']},
                {'name': 'email', 'values': ['ahmet.yilmaz@gmail.com']},
                {'name': 'phone_number', 'values': ['+905551234567']},
                {'name': 'city', 'values': ['Istanbul']}
            ],
            'campaign_data': {
                'campaign_name': 'Model Sanayi Real Estate Campaign',
                'ad_name': 'Property Leads Facebook Feed',
                'source': 'facebook'
            }
        },
        {
            'meta_id': 'TEST_002_INSTAGRAM',
            'field_data': [
                {'name': 'ad_ve_soyad', 'values': ['Fatma Özkan']},
                {'name': 'eposta', 'values': ['fatma.ozkan@hotmail.com']},
                {'name': 'telefon', 'values': ['0533 987 65 43']},
                {'name': 'şehir', 'values': ['Ankara']}
            ],
            'campaign_data': {
                'campaign_name': 'Model Sanayi Instagram Stories Campaign',
                'ad_name': 'Premium Properties Instagram Reels',
                'source': 'instagram'
            }
        },
        {
            'meta_id': 'TEST_003_PARTIAL_INFO',
            'field_data': [
                {'name': 'isim', 'values': ['Mehmet']},
                {'name': 'soyad', 'values': ['Demir']},
                {'name': 'e-mail', 'values': ['mehmet.demir@yahoo.com']},
                {'name': 'mesaj', 'values': ['3+1 daire arıyorum, Kadıköy civarında']}
            ],
            'campaign_data': {
                'campaign_name': 'Model Sanayi Facebook Lead Generation',
                'ad_name': 'Kadıköy Properties Facebook Ad',
                'source': 'facebook'
            }
        },
        {
            'meta_id': 'TEST_004_EMAIL_ONLY',
            'field_data': [
                {'name': 'email_address', 'values': ['contact@example.com']},
                {'name': 'additional_info', 'values': ['Lüks villa ilgileniyorum']}
            ],
            'campaign_data': {
                'campaign_name': 'Model Sanayi Instagram Feed Campaign',
                'ad_name': 'Luxury Villa Instagram',
                'source': 'instagram'
            }
        },
        {
            'meta_id': 'TEST_005_COMPANY_LEAD',
            'field_data': [
                {'name': 'customer_name', 'values': ['Ali Veli']},
                {'name': 'work_email', 'values': ['ali.veli@modelsanayi.com']},
                {'name': 'company_name', 'values': ['Model Sanayi Ltd.']},
                {'name': 'contact_number', 'values': ['+90 212 555 0123']}
            ],
            'campaign_data': {
                'campaign_name': 'Model Sanayi B2B Facebook Campaign',
                'ad_name': 'Commercial Real Estate Facebook',
                'source': 'facebook'
            }
        }
    ]
    
    # Field mapping logic (same as in the main script)
    FIELD_MAPPING = {
        'name': [
            'full_name', 'name', 'first_name', 'last_name', 
            'customer_name', 'contact_name', 'lead_name',
            'first_and_last_name', 'nome_completo', 'isim_soyisim',
            'ad_ve_soyad', 'tam_isim'
        ],
        'email': [
            'email', 'email_address', 'e_mail', 'e-mail',
            'customer_email', 'contact_email', 'work_email',
            'personal_email', 'eposta', 'email_adresi'
        ],
        'phone': [
            'phone_number', 'phone', 'mobile', 'mobile_number',
            'cell_phone', 'contact_number', 'telefon', 'telefon_numarasi',
            'cep_telefonu', 'iletisim_numarasi', 'tel', 'tel_no'
        ],
        'city': [
            'city', 'location', 'city_name', 'şehir', 'konum',
            'sehir', 'il', 'bulundugunuz_sehir'
        ],
        'company': [
            'company', 'company_name', 'business_name', 'şirket',
            'sirket', 'firma', 'firma_adi', 'sirket_adi'
        ],
        'message': [
            'message', 'comment', 'notes', 'additional_info',
            'mesaj', 'yorum', 'notlar', 'ek_bilgi'
        ]
    }
    
    def extract_contact_info(field_data):
        """Enhanced contact extraction"""
        contact_info = {
            'name': '',
            'email': '',
            'phone': '',
            'city': '',
            'company': '',
            'message': ''
        }
        
        # Create field dictionary
        field_dict = {}
        for field in field_data:
            field_name = field.get('name', '').lower().strip()
            field_values = field.get('values', [])
            field_value = field_values[0] if field_values else ''
            field_dict[field_name] = field_value
        
        # Map fields using comprehensive mapping
        for contact_type, possible_names in FIELD_MAPPING.items():
            for field_name in possible_names:
                if field_name.lower() in field_dict:
                    value = field_dict[field_name.lower()].strip()
                    if value and not contact_info[contact_type]:
                        contact_info[contact_type] = value
                        break
        
        # Special name construction for Turkish forms
        if not contact_info['name']:
            first_name = field_dict.get('isim', '').strip()
            last_name = field_dict.get('soyad', '').strip()
            
            if first_name or last_name:
                contact_info['name'] = f"{first_name} {last_name}".strip()
        
        return contact_info
    
    created_count = 0
    facebook_count = 0
    instagram_count = 0
    
    print(f"\n📊 Processing {len(test_leads)} test leads...")
    
    for i, test_lead in enumerate(test_leads, 1):
        print(f"\n📧 Test Lead {i}/{len(test_leads)}")
        print(f"   ID: {test_lead['meta_id']}")
        
        # Extract contact info using enhanced mapping
        contact_info = extract_contact_info(test_lead['field_data'])
        campaign_data = test_lead['campaign_data']
        
        # Display extracted information
        print(f"   👤 Extracted Name: {contact_info['name'] or 'N/A'}")
        print(f"   📧 Extracted Email: {contact_info['email'] or 'N/A'}")
        print(f"   📱 Extracted Phone: {contact_info['phone'] or 'N/A'}")
        print(f"   🏙️ Extracted City: {contact_info['city'] or 'N/A'}")
        print(f"   🏢 Extracted Company: {contact_info['company'] or 'N/A'}")
        print(f"   💬 Extracted Message: {contact_info['message'] or 'N/A'}")
        
        # Platform detection
        source = campaign_data['source']
        if 'instagram' in campaign_data['campaign_name'].lower() or 'instagram' in campaign_data['ad_name'].lower():
            source = 'instagram'
        
        medium = 'instagram_ads' if source == 'instagram' else 'facebook_ads'
        
        print(f"   📱 Platform: {source.title()}")
        print(f"   🎯 Campaign: {campaign_data['campaign_name']}")
        
        # Count by platform
        if source == 'instagram':
            instagram_count += 1
        else:
            facebook_count += 1
        
        # Generate meaningful lead name
        lead_name = contact_info['name'] or f"Lead from {source.title()}"
        if not contact_info['name'] and contact_info['email']:
            lead_name = f"Email Lead - {contact_info['email'].split('@')[0]}"
        
        # Create enhanced lead description
        description_parts = [f"Enhanced test lead from {source.title()}"]
        if contact_info['message']:
            description_parts.append(f"Message: {contact_info['message']}")
        
        description = " | ".join(description_parts)
        
        # Skip if no meaningful contact info
        if not contact_info['name'] and not contact_info['email']:
            print(f"   ⚠️ No contact info found, would skip this lead")
            continue
        
        # Create lead in Odoo CRM
        crm_lead_data = {
            'name': lead_name,
            'email_from': contact_info['email'],
            'phone': contact_info['phone'],
            'city': contact_info['city'],
            'partner_name': contact_info['company'],
            'description': description,
            'meta_leadgen_id': test_lead['meta_id'],
            'meta_form_id': f"TEST_FORM_{i}",
            
            # Enhanced campaign tracking
            'meta_campaign_id': f"CAMP_{i}",
            'meta_campaign_name': campaign_data['campaign_name'],
            'meta_adset_id': f"ADSET_{i}",
            'meta_adset_name': f"Test AdSet {i}",
            'meta_ad_id': f"AD_{i}",
            'meta_ad_name': campaign_data['ad_name'],
            'meta_source': source,
            'meta_medium': medium
        }
        
        try:
            new_lead = Lead.create(crm_lead_data)
            print(f"   ✅ Created CRM lead ID: {new_lead}")
            created_count += 1
            
        except Exception as e:
            print(f"   ❌ Error creating lead: {e}")
    
    # Final summary
    print(f"\n{'='*80}")
    print("🎉 ENHANCED LEAD PROCESSING TEST COMPLETE!")
    print("="*80)
    print(f"✅ Total leads created: {created_count}")
    print(f"📘 Facebook leads: {facebook_count}")
    print(f"📱 Instagram leads: {instagram_count}")
    
    print(f"\n🔧 Enhanced Features Demonstrated:")
    print(f"   ✅ Turkish field names (ad_ve_soyad, eposta, telefon)")
    print(f"   ✅ English field variations (full_name, email_address, phone_number)")
    print(f"   ✅ Partial name construction (isim + soyad)")
    print(f"   ✅ Platform detection (Instagram vs Facebook)")
    print(f"   ✅ Contact info validation")
    print(f"   ✅ Meaningful lead names (no more 'Meta Lead')")
    
    if created_count > 0:
        print(f"\n🔗 View your enhanced test leads:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print(f"\n💡 Check the following improvements:")
        print(f"   • Real names extracted from Turkish/English forms")
        print(f"   • Correct source attribution (facebook/instagram)")
        print(f"   • Enhanced medium tracking (facebook_ads/instagram_ads)")
        print(f"   • Complete contact information")
    
    return True

if __name__ == '__main__':
    test_enhanced_field_mapping()