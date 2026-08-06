# -*- coding: utf-8 -*-
"""Force green Won ribbon label: Kazanıldı → Satış Yapıldı."""
import logging

_logger = logging.getLogger(__name__)

_RIBBON_TERM_MAP = {
    'Won': 'Satış Yapıldı',
    'Kazanıldı': 'Satış Yapıldı',
    'KAZANILDI': 'SATIŞ YAPILDI',
}


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    _patch_won_ribbon_translations(env)
    _patch_won_selection_translations(env)
    try:
        env.registry.clear_cache()
    except Exception:
        pass


def _patch_won_ribbon_translations(env):
    """Override CRM view arch terms so the green ribbon is Satış Yapıldı."""
    xmlids = (
        'crm.crm_lead_view_form',
        'crm.crm_lead_view_kanban_forecast',
        'tcrm_propertio.crm_lead_view_form_won_label',
    )
    for xmlid in xmlids:
        view = env.ref(xmlid, raise_if_not_found=False)
        if not view:
            continue
        for lang in ('tr_TR', 'tr', 'en_US'):
            try:
                view.with_context(lang=lang).update_field_translations(
                    'arch_db', {lang: dict(_RIBBON_TERM_MAP)}
                )
            except Exception as exc:
                _logger.debug('arch_db term patch skip %s lang=%s: %s', xmlid, lang, exc)
            # Hard replace in rendered arch when term API is insufficient
            try:
                arch = view.with_context(lang=lang).arch_db or ''
                if not arch:
                    continue
                new_arch = arch
                for old, new in (
                    ('title="Won"', 'title="Satış Yapıldı"'),
                    ("title='Won'", "title='Satış Yapıldı'"),
                    ('title="Kazanıldı"', 'title="Satış Yapıldı"'),
                    ("title='Kazanıldı'", "title='Satış Yapıldı'"),
                    ('title="KAZANILDI"', 'title="Satış Yapıldı"'),
                ):
                    new_arch = new_arch.replace(old, new)
                if new_arch != arch:
                    view.with_context(lang=lang).write({'arch_db': new_arch})
            except Exception as exc:
                _logger.debug('arch_db write skip %s lang=%s: %s', xmlid, lang, exc)


def _patch_won_selection_translations(env):
    """Align won_status selection label with Satış Yapıldı (chatter / filters)."""
    Field = env['ir.model.fields'].sudo()
    field = Field.search([
        ('model', '=', 'crm.lead'),
        ('name', '=', 'won_status'),
    ], limit=1)
    if not field:
        return
    try:
        # Selection translations live on the field; best-effort rename of Won.
        field.update_field_translations('selection', {
            'tr_TR': {'Won': 'Satış Yapıldı', 'Kazanıldı': 'Satış Yapıldı'},
            'tr': {'Won': 'Satış Yapıldı', 'Kazanıldı': 'Satış Yapıldı'},
            'en_US': {'Won': 'Satış Yapıldı'},
        })
    except Exception as exc:
        _logger.debug('won_status selection translation skip: %s', exc)
