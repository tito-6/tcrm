# CRM Lead Integration System

A comprehensive Odoo 17.0 CRM integration system with Meta (Facebook) Ads, Google Ads, and WhatsApp Business API integration for lead management and automated communication.

## 🚀 Features

### Core Integrations
- **Meta (Facebook) Ads API**: Automated lead import from Facebook campaigns
- **Google Ads API**: Lead tracking and campaign management
- **WhatsApp Business API**: Send messages directly from CRM leads and contacts
- **Real-time Lead Processing**: Webhook-based instant lead synchronization
- **Creative Tracking**: Facebook ad creative performance monitoring

### Lead Management
- **Automated Lead Import**: Real-time lead capture from Facebook forms
- **Lead Enrichment**: Automatic data enhancement with form responses
- **Campaign Tracking**: Link leads to specific ad campaigns and creatives
- **Lead Scoring**: Built-in lead qualification system
- **WhatsApp Integration**: Send messages to leads directly from Odoo

### Technical Features
- **Docker-based Deployment**: Complete containerized setup
- **Ngrok Integration**: Easy webhook testing and development
- **Webhook Processing**: Real-time lead and message processing
- **Multi-environment Support**: Development and production configurations
- **Comprehensive Logging**: Full audit trail and debugging support

## 📋 Prerequisites

- **Docker & Docker Compose**: Latest version installed
- **Git**: For cloning the repository
- **Meta Developer Account**: With WhatsApp Business API access
- **Google Ads Account**: With API access (optional)
- **Ngrok Account**: For webhook development (optional for production)

## 🛠️ Quick Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/tito-6/crm_lead_integration.git
cd crm_lead_integration
```

### 2. Environment Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
# Database Configuration
POSTGRES_DB=postgres
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo
ODOO_ADMIN_PASSWORD=admin

# Meta (Facebook) API Configuration
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_USER_ACCESS_TOKEN=your_meta_access_token
META_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token

# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER=your_phone_number
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id

# Google Ads Configuration (Optional)
GOOGLE_DEVELOPER_TOKEN=your_google_developer_token
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Ngrok Configuration (Development)
NGROK_AUTHTOKEN=your_ngrok_auth_token
NGROK_REGION=us
```

### 3. Start the Application

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f odoo-web
```

### 4. Access the Application

- **Odoo CRM**: http://localhost:8069
- **Default Login**: admin / admin
- **Database**: crm (auto-created)

### 5. Install Custom Modules

1. Go to **Apps** menu in Odoo
2. Click **Update Apps List**
3. Search for and install:
   - **Custom CRM Integration** (Meta Ads integration)
   - **WhatsApp Business Integration** (WhatsApp messaging)

## 📁 Project Structure

```
crm_lead_integration/
├── custom-addons/                 # Custom Odoo modules
│   ├── custom_crm_integration/    # Meta Ads integration
│   │   ├── models/               # Data models
│   │   ├── controllers/          # API controllers
│   │   ├── views/                # UI views
│   │   ├── security/             # Access permissions
│   │   └── data/                 # Initial data
│   └── whatsapp_business_integration/  # WhatsApp integration
│       ├── models/               # WhatsApp models
│       ├── services/             # WhatsApp API services
│       ├── controllers/          # Webhook controllers
│       ├── views/                # WhatsApp UI views
│       └── security/             # WhatsApp permissions
├── config/                       # Configuration files
│   ├── odoo.conf                # Odoo configuration
│   └── ngrok.yml               # Ngrok configuration
├── scripts/                     # Utility scripts
│   ├── setup_admin.py          # Admin setup
│   ├── import_leads.py         # Lead import tools
│   └── test_integration.py     # Integration tests
├── docs/                       # Documentation
│   └── LEAD_INTEGRATION_GUIDE.md
├── docker-compose.yml          # Docker services configuration
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## 🔧 Configuration Details

### Meta (Facebook) Integration Setup

1. **Create Meta App**:
   - Go to https://developers.facebook.com/apps/
   - Create new app with "Business" type
   - Add "WhatsApp" and "Webhooks" products

2. **Configure WhatsApp Business**:
   - Go to WhatsApp > API Setup
   - Add phone number and complete verification
   - Generate access token (select "never expires")
   - Note your Business Account ID and Phone Number ID

3. **Setup Webhooks**:
   - Configure webhook URL: `https://your-domain.com/whatsapp/webhook`
   - Subscribe to message events
   - Use the verify token from your `.env` file

### Google Ads Integration Setup (Optional)

1. **Enable Google Ads API**:
   - Go to Google Cloud Console
   - Enable Google Ads API
   - Create OAuth 2.0 credentials

2. **Get Developer Token**:
   - Apply for Google Ads API access
   - Get your developer token

### Database and Lead Flow

The system automatically:
1. **Receives leads** from Facebook via webhooks
2. **Creates CRM leads** with form data
3. **Links to campaigns** and ad creatives
4. **Enables WhatsApp messaging** for follow-up
5. **Tracks engagement** and conversion

## 📱 WhatsApp Integration Usage

### Send Messages from CRM

1. **From Lead/Contact**:
   - Open any lead or contact
   - Click "Send WhatsApp Message" button
   - Compose and send message

2. **From Conversations**:
   - Go to WhatsApp > Conversations
   - View message history
   - Send follow-up messages

### Message Templates

Pre-configured templates available:
- Welcome message for new leads
- Follow-up messages
- Appointment reminders
- Custom templates

## 🔍 Troubleshooting

### Common Issues

1. **Module Installation Fails**:
   ```bash
   # Restart Odoo container
   docker restart odoo-web
   
   # Check logs
   docker logs odoo-web
   ```

2. **WhatsApp API Errors**:
   - Verify phone number is registered and approved
   - Check access token validity
   - Ensure webhook URL is accessible

3. **Database Connection Issues**:
   ```bash
   # Reset database
   docker-compose down
   docker volume rm crm_odoo-db-data
   docker-compose up -d
   ```

4. **Permission Errors**:
   - Check user groups in Odoo
   - Verify security rules are loaded
   - Update module if needed

### Log Files

- **Odoo Logs**: `docker logs odoo-web`
- **PostgreSQL Logs**: `docker logs odoo-db`
- **Ngrok Logs**: `docker logs odoo-ngrok`

## 🧪 Testing

### Test Scripts Available

```bash
# Test Meta API connection
python scripts/test_integration.py

# Test WhatsApp messaging
python scripts/test_whatsapp_service.py

# Import test leads
python scripts/import_test_leads.py

# Check module status
python scripts/check_module_status.py
```

### Integration Tests

1. **Meta Webhook Test**:
   - Send test webhook from Meta
   - Verify lead creation in Odoo

2. **WhatsApp Message Test**:
   - Send message from CRM
   - Check delivery status

3. **Lead Processing Test**:
   - Submit Facebook lead form
   - Verify real-time import

## 🚀 Production Deployment

### Using Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml crm-stack
```

### Environment Variables for Production

```env
# Use production database
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432

# Use HTTPS URLs
ODOO_BASE_URL=https://your-domain.com

# Production secrets
META_WEBHOOK_VERIFY_TOKEN=secure-random-token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=another-secure-token
```

### SSL and Domain Setup

1. **Configure reverse proxy** (nginx/traefik)
2. **Setup SSL certificates** (Let's Encrypt)
3. **Update webhook URLs** in Meta Developer Console
4. **Test webhook delivery**

## 📚 Advanced Configuration

### Custom Lead Processing

Modify lead processing logic in:
- `custom_crm_integration/models/crm_lead.py`
- `custom_crm_integration/controllers/webhook_controller.py`

### WhatsApp Message Templates

Add custom templates in:
- `whatsapp_business_integration/data/whatsapp_message_templates.xml`

### UI Customization

Customize views in:
- `custom_crm_integration/views/`
- `whatsapp_business_integration/views/`

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the LGPL-3 License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- **Issues**: GitHub Issues
- **Documentation**: Check `/docs` folder
- **Logs**: Use `docker-compose logs` for debugging

## 🎯 Next Steps After Setup

1. **Configure Meta Webhooks** with your domain
2. **Complete WhatsApp Business verification**
3. **Import existing leads** using provided scripts
4. **Setup automated campaigns** and message templates
5. **Train users** on the new CRM features

---

**🎉 Congratulations!** Your CRM Lead Integration system is ready to capture leads from Facebook and engage customers through WhatsApp automatically!