# -*- coding: utf-8 -*-
import logging
import os

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Seed configuration and guarantee automatic Meta lead + spend sync."""
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
    ensure_daily_metrics_cron(env)
    schedule_marketing_automation(env, daily_days_back=30)


def ensure_meta_lead_cron(env):
    """Restore the recurring Meta → CRM sync when an older DB lacks its XML row."""
    return _write_meta_lead_cron(env)


def _write_meta_lead_cron(env):
    xmlid = 'tcrm_marketing_hub.ir_cron_marketing_meta_leads_auto_crm'
    cron = env.ref(xmlid, raise_if_not_found=False)
    vals = {
        'name': 'Marketing Hub: Auto sync Meta leads → CRM',
        'model_id': env['ir.model']._get_id('tcrm.marketing.meta.lead'),
        'state': 'code',
        'code': 'model._cron_sync_meta_leads_to_crm()',
        'interval_number': 10,
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


def ensure_daily_metrics_cron(env):
    """Ensure hourly spend cache sync is active."""
    xmlid = 'tcrm_marketing_hub.ir_cron_marketing_daily_metrics'
    cron = env.ref(xmlid, raise_if_not_found=False)
    vals = {
        'name': 'Marketing Hub: Günlük harcama senkronizasyonu',
        'model_id': env['ir.model']._get_id('tcrm.marketing.daily.metric'),
        'state': 'code',
        'code': 'model._cron_sync_daily_metrics()',
        'interval_number': 1,
        'interval_type': 'hours',
        'active': True,
    }
    if cron:
        cron.sudo().write(vals)
        return cron

    cron = env['ir.cron'].sudo().create(vals)
    env['ir.model.data'].sudo().create({
        'module': 'tcrm_marketing_hub',
        'name': 'ir_cron_marketing_daily_metrics',
        'model': 'ir.cron',
        'res_id': cron.id,
        'noupdate': True,
    })
    return cron


def schedule_marketing_automation(env, daily_days_back=7):
    """Queue immediate cron runs so no manual sync click is required."""
    del daily_days_back  # reserved for future backfill tuning
    for xmlid in (
        'tcrm_marketing_hub.ir_cron_marketing_meta_leads_auto_crm',
        'tcrm_marketing_hub.ir_cron_marketing_daily_metrics',
    ):
        cron = env.ref(xmlid, raise_if_not_found=False)
        if not cron:
            continue
        try:
            cron.sudo()._trigger()
            _logger.info('Triggered marketing automation cron: %s', xmlid)
        except Exception as exc:
            _logger.warning('Could not trigger cron %s: %s', xmlid, exc)

