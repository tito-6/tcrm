# -*- coding: utf-8 -*-
{
    "name": "TCRM Organizasyon",
    "version": "1.0.1",
    "category": "Sales/CRM",
    "summary": "Organizasyon şeması, ekipler, departmanlar ve ekran erişimi",
    "description": """
Tenant-friendly organization management for TCRM:
- Create and configure sales teams (Ekipler) from CRM
- Hierarchical departments linked to teams and users
- Tenant admin module/screen access grants
- Assigned-only visibility for leads, sales, tasks
    """,
    "author": "Tcrm S.A.",
    "license": "LGPL-3",
    "depends": [
        "crm",
        "sales_team",
        "hr",
        "mail",
        "tcrm_propertio",
        "tcrm_saas_core",
    ],
    "data": [
        "security/org_security.xml",
        "security/ir.model.access.csv",
        "security/org_rules.xml",
        "views/hr_department_views.xml",
        "views/crm_team_views.xml",
        "views/org_access_views.xml",
        "views/res_users_views.xml",
        "views/org_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tcrm_org/static/src/scss/org.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
