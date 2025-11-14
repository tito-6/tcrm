# 🔗 Connecting Meta (Facebook/Instagram) & Google Leads to Odoo CRM

## 📋 Overview

This guide explains how to connect your Meta (Facebook/Instagram) Lead Ads and Google Ads leads directly into your Odoo CRM system.

## 🎯 Integration Methods

### Method 1: Website Contact Forms (✅ Already Set Up)

**Your Odoo has `website_crm` installed** - this creates web forms that capture leads automatically.

#### Setup Steps:
1. Go to **Website → Configuration → Pages**
2. Create a "Contact Us" or "Get a Quote" page
3. Add a contact form snippet
4. Forms automatically create leads in CRM

#### Use this form URL in your ads:
- **Form URL**: `http://localhost:8069/contactus` (or `/page/contactus`)
- Facebook/Google ads can redirect to this form

---

### Method 2: Meta Lead Ads Integration (Webhook)

Meta Lead Ads can send leads directly to Odoo via webhooks.

#### Step 1: Create Custom Webhook Endpoint

Create a custom Odoo controller to receive Meta leads:

**File**: `odoo/addons/custom_crm_integration/controllers/meta_webhook.py`

```python
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class MetaWebhook(http.Controller):
    
    @http.route('/webhook/meta/leads', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_meta_lead(self, **kwargs):
        """Receive leads from Meta (Facebook/Instagram) Lead Ads"""
        try:
            data = request.jsonrequest
            _logger.info(f"Received Meta lead: {data}")
            
            # Extract lead data
            lead_data = {
                'name': data.get('full_name', 'Meta Lead'),
                'email_from': data.get('email'),
                'phone': data.get('phone_number'),
                'description': f"Source: Meta Lead Ads\nAd ID: {data.get('ad_id')}\nForm ID: {data.get('form_id')}",
                'source_id': request.env.ref('utm.utm_source_facebook').id,
                'medium_id': request.env.ref('utm.utm_medium_paid').id,
            }
            
            # Create lead in CRM
            lead = request.env['crm.lead'].sudo().create(lead_data)
            
            return {'success': True, 'lead_id': lead.id}
            
        except Exception as e:
            _logger.error(f"Error processing Meta lead: {e}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/webhook/meta/verify', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_meta_webhook(self, **kwargs):
        """Verify webhook for Meta"""
        verify_token = "YOUR_VERIFY_TOKEN_HERE"
        
        if kwargs.get('hub.verify_token') == verify_token:
            return kwargs.get('hub.challenge', '')
        return 'Error, wrong validation token'
```

#### Step 2: Configure Meta Business Suite

1. Go to **Meta Business Suite** → **Lead Ads**
2. Select your ad account
3. Go to **Settings** → **CRM Integration**
4. Add **Webhook URL**: `https://your-domain.com/webhook/meta/leads`
5. Set **Verify Token**: (use same as in code above)
6. Subscribe to `leadgen` events

---

### Method 3: Google Ads Lead Form Extensions

Google Ads can send leads via:

#### Option A: Google Sheets + Zapier/Make (Easiest)

1. **Set up Google Lead Form** in Google Ads
2. **Export leads to Google Sheets**
3. **Use Zapier or Make.com** to:
   - Watch for new rows in Google Sheets
   - Send to Odoo API endpoint

#### Option B: Custom Webhook (Similar to Meta)

**File**: `odoo/addons/custom_crm_integration/controllers/google_webhook.py`

```python
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class GoogleWebhook(http.Controller):
    
    @http.route('/webhook/google/leads', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_google_lead(self, **kwargs):
        """Receive leads from Google Ads"""
        try:
            data = request.jsonrequest
            _logger.info(f"Received Google lead: {data}")
            
            lead_data = {
                'name': f"{data.get('firstName', '')} {data.get('lastName', '')}".strip() or 'Google Lead',
                'email_from': data.get('email'),
                'phone': data.get('phoneNumber'),
                'description': f"Source: Google Ads\nCampaign: {data.get('campaignId')}\nAd Group: {data.get('adGroupId')}",
                'source_id': request.env.ref('utm.utm_source_adwords').id,
                'medium_id': request.env.ref('utm.utm_medium_cpc').id,
            }
            
            lead = request.env['crm.lead'].sudo().create(lead_data)
            
            return {'success': True, 'lead_id': lead.id}
            
        except Exception as e:
            _logger.error(f"Error processing Google lead: {e}")
            return {'success': False, 'error': str(e)}
```

---

### Method 4: Odoo API (Most Flexible)

Use Odoo's external API to create leads from any source:

```python
import xmlrpc.client

# Odoo connection
url = "http://localhost:8069"
db = "crm"
username = "admin"
password = "admin"

# Authenticate
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

# Create lead
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
lead_id = models.execute_kw(db, uid, password, 'crm.lead', 'create', [{
    'name': 'John Doe',
    'email_from': 'john@example.com',
    'phone': '+1234567890',
    'description': 'Lead from Facebook Ad Campaign',
}])

print(f"Lead created with ID: {lead_id}")
```

---

### Method 5: Email to Lead

Odoo can convert emails to leads automatically:

1. Go to **Settings → Technical → Incoming Mail Servers**
2. Set up email account (e.g., `leads@yourdomain.com`)
3. Configure **Create a new record** → Choose `CRM Lead`
4. Any email to this address becomes a lead

**For Meta/Google:**
- Set up lead notification emails to go to `leads@yourdomain.com`
- Odoo automatically creates leads

---

## 🔧 Quick Setup (Without Code)

### For Both Meta & Google:

1. **Enable Website Forms**:
   - Go to **Website → Edit**
   - Add "Contact Form" snippet
   - Publish the page

2. **Get Public URL** (using ngrok):
   ```bash
   # Add ngrok token to .env file
   NGROK_AUTHTOKEN=your_token_here
   
   # Restart ngrok
   docker compose restart ngrok
   ```

3. **Use Form URL in Ads**:
   - Set ad destination to your Odoo contact form
   - Leads automatically enter CRM

4. **Use UTM Parameters** to track source:
   - Facebook: `?utm_source=facebook&utm_medium=cpc&utm_campaign=property_ads`
   - Google: `?utm_source=google&utm_medium=cpc&utm_campaign=real_estate`

---

## 📊 Tracking Lead Sources

### Set Up UTM Tracking in Odoo:

1. Go to **CRM → Configuration → Lead Sources**
2. Create sources:
   - Facebook Ads
   - Instagram Ads
   - Google Ads
   - Google Search

3. Go to **CRM → Configuration → Campaigns**
4. Create campaigns for each ad campaign

---

## 🚀 Recommended Approach

**For immediate setup (No coding):**

1. ✅ Use **Website Contact Forms** (already installed)
2. ✅ Add **ngrok** public URL for testing
3. ✅ Set ad traffic to Odoo contact form
4. ✅ Use **UTM parameters** to track sources

**For advanced integration:**

1. Create custom Odoo module with webhook endpoints
2. Configure Meta/Google to send to webhooks
3. Automate lead enrichment and routing

---

## 🔐 Security Notes

- Always use HTTPS in production (not http)
- Implement webhook verification tokens
- Use API keys for authentication
- Validate incoming data
- Log all webhook attempts

---

## 📞 Next Steps

1. Get ngrok auth token and add to `.env`
2. Restart ngrok: `docker compose restart ngrok`
3. Get public URL: `docker logs odoo-ngrok`
4. Test contact form at: `https://your-ngrok-url.ngrok.io/contactus`
5. Configure Meta/Google ads to redirect to this URL

---

## 💡 Testing

Create a test lead manually:

```bash
curl -X POST http://localhost:8069/webhook/meta/leads \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Lead",
    "email": "test@example.com",
    "phone_number": "+1234567890",
    "ad_id": "123456",
    "form_id": "789012"
  }'
```

Check in Odoo CRM → Leads to see if it appeared!
