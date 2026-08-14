# -*- coding: utf-8 -*-
import os


def post_init_hook(env):
    """Seed configuration and guarantee the automatic Meta lead sync."""
    ICP = env['ir.config_parameter'].sudo()
    if not ICP.get_param('tcrm_marketing_hub.zernio_api_key'):
        key = (os.environ.get('ZERNIO_API_KEY') or '').strip()
        if key:
            ICP.set_param('tcrm_marketing_hub.zernio_api_key', key)
    ICP.set_param(
        'tcrm_marketing_hub.zernio_base_url',
        ICP.get_param('tcrm_marketing_hub.zernio_base_url') or 'https://zernio.com/api/v1',
    )
    ensure_meta_lead_cron(env)


def ensure_meta_lead_cron(env):
    """Restore the recurring Meta → CRM sync when an older DB lacks its XML row."""
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
        return cron

    cron = env['ir.cron'].sudo().create(vals)
    env['ir.model.data'].sudo().create({
        'module': 'tcrm_marketing_hub',
        'name': 'ir_cron_marketing_meta_leads_auto_crm',
        'model': 'ir.cron',
        'res_id': cron.id,
        'noupdate': True,
    })
    return cron
