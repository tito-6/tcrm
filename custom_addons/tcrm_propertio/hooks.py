# -*- coding: utf-8 -*-
"""Module hooks for Propertio."""

# Demo / master-data English labels → Turkish (DB records, not field strings).
_MASTER_DATA_TR = {
    'Ready to Move': 'Yerleşime Hazır',
    'Under Construction': 'İnşaat Halinde',
    'Kaba İnşaat': 'Kaba İnşaat',
    '2+1 Apartment': '2+1 Daire',
    '3+1 Apartment': '3+1 Daire',
    '1+1 Apartment': '1+1 Daire',
    'Studio': 'Stüdyo',
    'Stüdyo': 'Stüdyo',
    'Shop': 'Dükkan',
    'Dükkan': 'Dükkan',
    'Villa': 'Villa',
    'Penthouse': 'Penthouse',
}


def post_init_hook(env):
    _force_inventory_menu_label(env)
    _translate_master_data_labels(env)
    _force_sold_ribbon_label(env)
    _force_apps_sidebar_order(env)
    _force_lead_havuzu_home(env)
    _force_istanbul_timezone(env)


def _force_istanbul_timezone(env):
    """Align account timezone with Istanbul (GMT+3)."""
    from .models.tcrm_timezone import tcrm_ensure_istanbul_tz
    tcrm_ensure_istanbul_tz(env)


def _force_lead_havuzu_home(env):
    """All internal users land on Lead Havuzu after login (list on mobile too)."""
    action = env.ref('tcrm_propertio.action_lead_havuzu', raise_if_not_found=False)
    if not action:
        return
    _force_lead_havuzu_mobile_list(env)
    users = env['res.users'].sudo().search([
        ('share', '=', False),
        ('active', '=', True),
        '|', ('action_id', '=', False), ('action_id', '!=', action.id),
    ])
    if users:
        users.write({'action_id': action.id})


def _force_lead_havuzu_mobile_list(env):
    """Prefer list (not kanban) when Lead Havuzu opens on small screens."""
    xmlids = (
        'tcrm_propertio.action_lead_havuzu',
        'crm.crm_lead_all_leads',
        'crm.crm_lead_action_pipeline',
    )
    for xmlid in xmlids:
        action = env.ref(xmlid, raise_if_not_found=False)
        if action and action.mobile_view_mode != 'list':
            action.write({'mobile_view_mode': 'list'})


def _force_apps_sidebar_order(env):
    """CRM → Propertio → Santral → Marketing Hub → Takvim → Yapılacaklar."""
    order = (
        ('crm.crm_menu_root', 1),
        ('tcrm_propertio.menu_propertio_root', 2),
        ('tcrm_call_center.menu_santral_root', 3),
        ('tcrm_marketing_hub.menu_tcrm_marketing_root', 4),
        ('calendar.mail_menu_calendar', 5),
        ('project_todo.menu_todo_todos', 6),
        # Keep Discuss after the core real-estate stack
        ('mail.menu_root_discuss', 10),
    )
    Menu = env['ir.ui.menu'].sudo()
    for xmlid, sequence in order:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu and menu.sequence != sequence:
            menu.write({'sequence': sequence})
    try:
        env.registry.clear_cache()
    except Exception:
        pass
    try:
        Menu.clear_caches()
    except Exception:
        pass


def _force_sold_ribbon_label(env):
    """Ensure CRM Won ribbon says Satış Yapıldı (not Kazanıldı)."""
    view = env.ref('crm.crm_lead_view_form', raise_if_not_found=False)
    if not view:
        return
    for lang in ('tr_TR', 'tr', 'en_US'):
        try:
            view.with_context(lang=lang).update_field_translations(
                'arch_db',
                {lang: {'Won': 'Satış Yapıldı', 'Kazanıldı': 'Satış Yapıldı'}},
            )
        except Exception:
            pass
        try:
            arch = view.with_context(lang=lang).arch_db or ''
            new_arch = (
                arch.replace('title="Won"', 'title="Satış Yapıldı"')
                .replace("title='Won'", "title='Satış Yapıldı'")
                .replace('title="Kazanıldı"', 'title="Satış Yapıldı"')
                .replace("title='Kazanıldı'", "title='Satış Yapıldı'")
            )
            if new_arch != arch:
                view.with_context(lang=lang).write({'arch_db': new_arch})
        except Exception:
            pass


def _force_inventory_menu_label(env):
    """Ensure inventory section label is Proje stok ve takibi in all langs."""
    menu = env.ref('tcrm_propertio.menu_propertio_inventory', raise_if_not_found=False)
    if not menu:
        return
    label = 'Proje stok ve takibi'
    if menu.name != label:
        menu.write({'name': label})
    try:
        menu.update_field_translations('name', {
            'en_US': label,
            'tr_TR': label,
            'tr': label,
        })
    except Exception:
        pass


def _translate_master_data_labels(env):
    """Rename English category/status demo names to Turkish."""
    for model_name in ('propertio.unit.category', 'propertio.unit.status'):
        if model_name not in env:
            continue
        Model = env[model_name].sudo()
        for en, tr in _MASTER_DATA_TR.items():
            recs = Model.search([('name', '=', en)])
            if recs:
                recs.write({'name': tr})
