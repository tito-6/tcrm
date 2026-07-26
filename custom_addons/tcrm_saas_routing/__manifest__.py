# -*- coding: utf-8 -*-
{
    'name': 'TCRM SaaS Routing',
    'version': '1.0.0',
    'summary': 'Host-based tenant database routing (tenantN.tcrm.online -> dedicated DB)',
    'description': """
TCRM SaaS Routing
=================
Enables true DB-per-tenant isolation by routing incoming HTTP hosts to the
correct PostgreSQL database:

* ``tcrm.online`` / ``www.tcrm.online`` -> control-plane DB (TCRM Master)
* ``<tenant>.tcrm.online``              -> dedicated tenant DB ``<tenant>``

Loaded as a *server-wide module* so the host->db resolver is active before any
request is dispatched. It wraps ``tcrm.http.db_filter`` and falls back to the
original behaviour on any error, so it is safe/reversible: remove the module
from ``server_wide_modules`` and restart to revert.

Configuration (tcrm.conf ``[options]``):
    tcrm_control_db    = tcrm_master        ; control-plane database name
    tcrm_control_hosts = tcrm.online        ; comma-separated bare control hosts
    tcrm_base_domain   = tcrm.online        ; apex domain for tenant subdomains
""",
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
