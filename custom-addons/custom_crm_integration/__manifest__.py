{
    'name': 'Custom CRM Integration',
    'version': '17.0.8.0.0',
    'category': 'CRM',
    'summary': 'Webhook endpoints for Meta and Google lead integration',
    'description': """
        Advanced CRM Integration Module with High-Resolution Creative Fetching
        ====================================================================
        
        Features:
        - Meta (Facebook/Instagram) Lead Ads webhook with enhanced creative support
        - Advanced high-resolution image/video fetching using Meta Graph API
        - Multi-tier waterfall strategy for maximum resolution achievement
        - Support for Dynamic Creative and Advantage+ Catalog ads
        - Video embed HTML and high-quality poster extraction
        - Google Ads lead webhook
        - Automatic lead creation from external sources
        - UTM tracking support
        - Creative quality assessment and reporting
        
        Enhanced Creative Capabilities:
        - Direct creative image analysis with quality detection
        - Object story spec extraction (link_data.picture, video_data.image_url)
        - Effective object story ID Page Post fallback (full_picture access)
        - Asset feed spec parsing for dynamic ad assets
        - AdImage endpoint access for original resolution images
        - Comprehensive video handling with embed_html
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['crm', 'website', 'utm'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'views/crm_lead_views.xml',
        'views/res_config_settings_views.xml',
        'data/server_actions.xml',
        'data/cron_jobs.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
