# -*- coding: utf-8 -*-
import logging
import re

_logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(
    r'^\s*\[(?:Instagram|Facebook|Meta|IG|FB)\]\s*',
    re.IGNORECASE,
)


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID
    from tcrm.addons.tcrm_propertio.hooks import (
        _force_inventory_menu_label,
        _translate_master_data_labels,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    _force_inventory_menu_label(env)
    _translate_master_data_labels(env)

    # Won stage → Satış Yapıldı
    stage = env.ref('crm.stage_lead4', raise_if_not_found=False)
    if stage and stage.name != 'Satış Yapıldı':
        stage.with_context(lang=None).write({'name': 'Satış Yapıldı'})
        try:
            stage.update_field_translations('name', {
                'en_US': 'Satış Yapıldı',
                'tr_TR': 'Satış Yapıldı',
                'tr': 'Satış Yapıldı',
            })
        except Exception:
            pass

    # Strip platform prefixes + auto-opportunity + clear zero-noise revenue display
    Lead = env['crm.lead'].sudo()
    leads = Lead.search([('name', '=like', '[%')])
    for lead in leads:
        clean = _PREFIX_RE.sub('', lead.name or '').strip()
        vals = {}
        if clean and clean != lead.name:
            vals['name'] = clean
        if lead.type == 'lead':
            vals['type'] = 'opportunity'
        if vals:
            lead.write(vals)
    # Convert remaining type=lead records to opportunity
    Lead.search([('type', '=', 'lead')]).write({'type': 'opportunity'})

    # Home action → Lead Havuzu for all internal users
    action = env.ref('tcrm_propertio.action_lead_havuzu', raise_if_not_found=False)
    if action:
        users = env['res.users'].search([('share', '=', False), ('active', '=', True)])
        users.write({'action_id': action.id})

    # Pin CRM
    crm_root = env.ref('crm.crm_menu_root', raise_if_not_found=False)
    if crm_root:
        crm_root.write({'sequence': 1})

    # Refresh Meta ad creatives (best-effort)
    try:
        MetaAd = env['tcrm.marketing.meta.ad'].sudo()
        ads = MetaAd.search([])
        if ads:
            ads.action_refresh_creative_from_zernio()
            _logger.info('Refreshed creatives for %s cached ads', len(ads))
        # Also ensure creatives for meta leads whose ad_id is not yet cached
        MetaLead = env['tcrm.marketing.meta.lead'].sudo()
        for meta in MetaLead.search([('ad_id', '!=', False)], limit=200):
            meta._ensure_ad_creative_cached(meta.ad_id)
            if meta.crm_lead_id:
                crm_name = meta.crm_lead_id.name or ''
                clean = meta._strip_platform_prefix(crm_name)
                w = {}
                if clean != crm_name:
                    w['name'] = clean
                if meta.crm_lead_id.type == 'lead':
                    w['type'] = 'opportunity'
                if w:
                    meta.crm_lead_id.write(w)
    except Exception as exc:
        _logger.warning('Creative / meta lead cleanup skipped: %s', exc)
