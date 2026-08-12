# -*- coding: utf-8 -*-
"""Force Lead Havuzu (home) to open as list on mobile, not kanban."""
import logging

_logger = logging.getLogger(__name__)

_ACTION_XMLIDS = (
    'tcrm_propertio.action_lead_havuzu',
    'crm.crm_lead_all_leads',
    'crm.crm_lead_action_pipeline',
)


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    updated = 0
    for xmlid in _ACTION_XMLIDS:
        action = env.ref(xmlid, raise_if_not_found=False)
        if not action:
            continue
        if action.mobile_view_mode != 'list':
            action.write({'mobile_view_mode': 'list'})
            updated += 1
    _logger.info(
        'Lead Havuzu mobile_view_mode=list applied to %s action(s)', updated,
    )
