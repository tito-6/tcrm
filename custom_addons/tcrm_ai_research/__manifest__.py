# Part of TCRM AI Research. See LICENSE for details.
{
    'name': 'TCRM AI Research',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Native RAGFlow-backed AI research assistant for CRM',
    'description': """
TCRM AI Research
================
Native OWL research assistant integrated with a self-hosted RAGFlow instance.

* Server-to-server RAGFlow API (API key never exposed to the browser)
* Workspaces, conversations, citations, and document sync
* CRM context from leads, opportunities, and partners
* Save research answers as internal CRM notes
    """,
    'author': 'TCRM',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'web',
        'mail',
        'crm',
    ],
    'data': [
        'security/ai_research_security.xml',
        'security/ir.model.access.csv',
        'data/ai_research_sequence.xml',
        'data/ai_research_cron.xml',
        'views/ai_conversation_views.xml',
        'views/ai_document_views.xml',
        'views/ai_workspace_views.xml',
        'views/res_config_settings_views.xml',
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
        'views/ai_research_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_ai_research/static/src/services/ai_research_service.js',
            'tcrm_ai_research/static/src/components/research_assistant/research_assistant.scss',
            'tcrm_ai_research/static/src/components/research_assistant/research_assistant.xml',
            'tcrm_ai_research/static/src/components/research_assistant/research_assistant.js',
        ],
    },
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': True,
}
