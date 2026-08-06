# -*- coding: utf-8 -*-
"""Force CRM Won ribbon / labels: Kazanıldı → Satış Yapıldı."""


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        from tcrm.addons.tcrm_propertio.hooks import _force_sold_ribbon_label
        _force_sold_ribbon_label(env)
    except Exception:
        pass

    stage = env.ref('crm.stage_lead4', raise_if_not_found=False)
    if stage:
        if stage.with_context(lang=None).name != 'Satış Yapıldı':
            stage.with_context(lang=None).write({'name': 'Satış Yapıldı'})
        try:
            stage.update_field_translations('name', {
                'en_US': 'Satış Yapıldı',
                'tr_TR': 'Satış Yapıldı',
                'tr': 'Satış Yapıldı',
            })
        except Exception:
            pass

    term_map = {
        'Won': 'Satış Yapıldı',
        'Kazanıldı': 'Satış Yapıldı',
        'KAZANILDI': 'SATIŞ YAPILDI',
    }
    for xmlid in (
        'crm.crm_lead_view_form',
        'crm.crm_lead_view_kanban_forecast',
        'tcrm_propertio.crm_lead_view_form_won_label',
        'tcrm_marketing_hub.view_crm_lead_form_won_satis_yapildi',
    ):
        view = env.ref(xmlid, raise_if_not_found=False)
        if not view:
            continue
        for lang in ('tr_TR', 'tr', 'en_US'):
            try:
                view.with_context(lang=lang).update_field_translations(
                    'arch_db', {lang: dict(term_map)},
                )
            except Exception:
                pass

    try:
        env.registry.clear_cache()
    except Exception:
        pass
