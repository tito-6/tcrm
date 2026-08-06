# -*- coding: utf-8 -*-
{
    "name": "TCRM Organizasyon",
    "version": "1.0.2",
    "category": "Sales/CRM",
    "summary": "Organizasyon bağları ve CRM erişim yönetimi",
    "description": """
Tenant-friendly organization links for TCRM:
- Departments / teams / personnel are managed under Çalışanlar (HR)
- CRM keeps only access-management configuration
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
