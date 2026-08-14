# -*- coding: utf-8 -*-
"""Restore the automated Meta lead sync cron on upgraded databases."""


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlid = 'tcrm_marketing_hub.ir_cron_marketing_meta_leads_auto_crm'
    cron = env.ref(xmlid, raise_if_not_found=False)
    vals = {
        'name': 'Marketing Hub: Auto sync Meta leads → CRM',
        'model_id': env['ir.model']._get_id('tcrm.marketing.meta.lead'),
        'state': 'code',
        'code': 'model._cron_sync_meta_leads_to_crm()',
        'interval_number': 15,
        'interval_type': 'minutes',
        'active': True,
    }
    if cron:
        cron.sudo().write(vals)
    else:
        cron = env['ir.cron'].sudo().create(vals)
        env['ir.model.data'].sudo().create({
            'module': 'tcrm_marketing_hub',
            'name': 'ir_cron_marketing_meta_leads_auto_crm',
            'model': 'ir.cron',
            'res_id': cron.id,
            'noupdate': True,
        })
