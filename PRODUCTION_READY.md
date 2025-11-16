# 🚀 PRODUCTION DEPLOYMENT GUIDE

## ✅ System is Production-Ready!

### Features Implemented:
1. **Automated Lead Fetching** - Runs every 2 minutes
2. **Settings UI** - Configure from Odoo Settings panel
3. **Manual Fetch Button** - Test anytime
4. **Lead Fields**: Platform, Campaign, Submitted On, Ad Set
5. **Statistics Tracking** - Last fetch time, total leads

---

## 📋 Quick Start

### 1. Access Settings
1. Login to Odoo: http://localhost:8069
2. Go to: **Settings** (⚙️ icon)
3. Look for: **Meta Lead Integration** section

### 2. Configure Facebook Integration
- **Facebook Page ID**: `542033395659747` (QUEEN VILLA - already set)
- **Access Token**: Already configured from .env
- **Auto-Fetch**: ✅ Enabled (fetches every 2 minutes)

### 3. Test the Integration
- Click **"Fetch Leads Now"** button
- Check notification for results
- Go to **CRM > Leads** to see new leads

---

## 🔄 Automatic Fetching

### How It Works:
- **Frequency**: Every 2 minutes
- **What it does**: Checks for new leads from all forms on the Facebook page
- **Duplicate Prevention**: Automatically skips leads already in system
- **Logging**: All fetch operations logged in Odoo logs

### To Enable/Disable:
- Go to **Settings > Meta Lead Integration**
- Toggle: **"Enable Automatic Lead Fetching"**
- Click **Save**

---

## 📊 View Leads

### Available Columns (customize via ☰ menu):
- **Submitted On** - When lead submitted on Facebook
- **Platform** - Facebook/Instagram/Messenger  
- **Campaign** - Facebook campaign name
- **Contact Name** - Lead's name
- **Email** - Lead's email
- **Phone** - Lead's phone number

### Access Leads:
```
CRM > Leads
or
http://localhost:8069/web#action=168&model=crm.lead&view_type=list
```

---

## 🔧 Update Facebook Token

### When token expires (every 60 days):

1. **Get New Token**:
   - Visit: https://developers.facebook.com/tools/explorer
   - Select your app
   - Click "Generate Access Token"
   - Grant permissions: `leads_retrieval`, `pages_read_engagement`, `pages_show_list`

2. **Update in Odoo**:
   - Go to: **Settings > Meta Lead Integration**
   - Paste new token in **"Facebook User Access Token"**
   - Click **Save**

3. **Or Update .env** (requires restart):
   ```bash
   # Edit .env file
   META_USER_ACCESS_TOKEN=your_new_token_here
   
   # Restart Odoo
   docker-compose restart odoo
   
   # Re-initialize settings
   python scripts/initialize_meta_settings.py
   ```

---

## 📈 Monitor Performance

### Check Statistics:
- **Settings > Meta Lead Integration**
- View:
  - **Last Fetch Time**: When leads were last fetched
  - **Total Leads Fetched**: Cumulative count

### Check Cron Job:
1. Enable Developer Mode: **Settings > Activate Developer Mode**
2. Go to: **Settings > Technical > Automation > Scheduled Actions**
3. Find: **"Fetch Facebook Leads"**
4. Check:
   - ✅ Active
   - Interval: 2 Minutes
   - Last Run
   - Next Run

---

## 🐛 Troubleshooting

### Leads Not Fetching?

1. **Check Token**:
   - Settings > Meta Lead Integration
   - Verify token is set
   - Click "Fetch Leads Now" to test

2. **Check Cron Job**:
   - Settings > Technical > Scheduled Actions
   - Ensure "Fetch Facebook Leads" is Active
   - Check "Next Execution Date"

3. **Check Logs**:
   ```bash
   docker logs odoo-web --tail 100 | grep -i "meta\|fetch\|lead"
   ```

4. **Manually Test**:
   ```bash
   python scripts/fetch_queen_villa_leads_only.py
   ```

### Token Expired?
- Error: "Session has expired" or "user logged out"
- Solution: Get new token (see "Update Facebook Token" above)

### No New Leads?
- Normal if all leads already imported
- Check Facebook Lead Ads Manager for new submissions

---

## 🔐 Security Best Practices

1. **Access Token**:
   - Keep token secret
   - Rotate every 60 days
   - Use long-lived tokens

2. **Odoo Security**:
   - Change default admin password
   - Use HTTPS in production
   - Restrict Settings access to admin users

3. **Database Backups**:
   ```bash
   # Backup database
   docker exec odoo-db pg_dump -U odoo crm > backup.sql
   
   # Restore database
   docker exec -i odoo-db psql -U odoo crm < backup.sql
   ```

---

## 📁 File Structure

### Production Files:
```
custom-addons/custom_crm_integration/
├── models/
│   ├── crm_lead.py              # Lead model with Meta fields
│   ├── crm_lead_fetcher.py      # Auto-fetch service
│   └── res_config_settings.py   # Settings panel
├── views/
│   ├── crm_lead_views.xml       # Lead list columns
│   └── res_config_settings_views.xml  # Settings UI
├── data/
│   ├── cron_jobs.xml            # 2-minute cron job
│   └── server_actions.xml       # Refresh creative action
└── __manifest__.py              # Module definition
```

### Scripts (for maintenance):
```
scripts/
├── fetch_queen_villa_leads_only.py  # Manual fetch
├── initialize_meta_settings.py      # Setup config
├── delete_all_leads.py              # Clean database
└── test_token.py                    # Verify token
```

---

## 🚀 Production Checklist

- [x] Automated fetching every 2 minutes
- [x] Settings UI in Odoo
- [x] Manual fetch button
- [x] Platform, Campaign, Submitted On fields
- [x] Token configuration
- [x] Statistics tracking
- [x] Duplicate prevention
- [x] Error handling
- [x] Logging
- [x] Production-ready deployment

---

## 📞 Support

### Current Setup:
- **Page**: QUEEN VILLA (542033395659747)
- **Forms**: 12 forms monitored
- **Current Leads**: 110
- **Auto-Fetch**: ✅ Enabled
- **Interval**: 2 minutes

### Need Changes?
- Update **Page ID** in Settings
- Add more pages by modifying `crm_lead_fetcher.py`
- Change fetch interval in cron job

---

**🎉 Your CRM is now production-ready and will automatically sync leads from Facebook every 2 minutes!**
