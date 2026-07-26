{
    'name': 'TCRM Research Hub',
    'version': '1.3.0',
    'summary': 'NotebookLM researches synced into TCRM — browse in-app',
    'description': """
        TCRM Research Hub
        ─────────────────
        Syncs researches from the user's real Google NotebookLM account into
        the TCRM database, then lets users browse them inside TCRM (navbar /
        Research Hub) instead of staying on Google's site.

        Also keeps an experimental In-Page proxy for Google login / cookie jar.
    """,
    'depends': [
        'web',
        'tcrm_saas_core',
    ],
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'category': 'TCRM',
    'data': [
        'security/tcrm_research_hub_groups.xml',
        'security/ir.model.access.csv',
        'security/tcrm_research_hub_rules.xml',
        'views/research_hub_views.xml',
        'views/research_notebook_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_research_hub/static/src/research_hub.scss',
            'tcrm_research_hub/static/src/notebook_container.xml',
            'tcrm_research_hub/static/src/notebook_container.js',
            'tcrm_research_hub/static/src/research_hub_entry.js',
            'tcrm_research_hub/static/src/research_hub_systray.xml',
            'tcrm_research_hub/static/src/research_hub_systray.js',
        ],
    },
    # Removed from product surface (Research Hub / Araştırma). Keep code for later.
    'installable': False,
    'application': False,
    'web_icon': 'tcrm_research_hub,static/description/icon.png',
}
