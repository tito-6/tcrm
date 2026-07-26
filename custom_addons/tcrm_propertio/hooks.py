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
