# -*- coding: utf-8 -*-
{
    'name': 'TCRM SaaS Provisioning',
    'version': '1.1.2',
    'summary': 'Secure tenant provisioning (signed jobs + privileged background worker)',
    'description': """
TCRM SaaS Provisioning
======================
Safe, auditable tenant provisioning for the DB-per-tenant architecture.

Security model:

* Control-plane UI (Command Center / tenant form) creates a signed provisioning
  job with domain, db name, and optional admin credentials. It never creates a
  database or runs install commands inside the HTTP request.
* A privileged background worker claims queued jobs under a PostgreSQL advisory
  lock and provisions using fixed subprocess argv (no shell interpolation).
* On failure the tenant/job is marked failed and can be retried idempotently.
* Partially provisioned tenants are never activated publicly.

``list_db`` stays False. Public database manager stays disabled.
""",
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': ['base', 'tcrm_saas_core'],
    'data': [
        'security/ir.model.access.csv',
        'data/provisioning_config.xml',
        'views/provisioning_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
