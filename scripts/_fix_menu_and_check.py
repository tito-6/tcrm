# -*- coding: utf-8 -*-
menu = env.ref('tcrm_propertio.menu_propertio_inventory')
print('raw', repr(menu.name))
print('tr', repr(menu.with_context(lang='tr_TR').name))
print('en', repr(menu.with_context(lang='en_US').name))
try:
    print('translations', menu.get_field_translations('name'))
except Exception as exc:
    print('get_field_translations failed', exc)
menu.write({'name': 'Proje Stok ve Takibi'})
# Update JSON translations on the field if present (Odoo 16+)
try:
    menu.update_field_translations('name', {
        'en_US': 'Proje Stok ve Takibi',
        'tr_TR': 'Proje Stok ve Takibi',
    })
except Exception as exc:
    print('update_field_translations failed', exc)
env.cr.commit()
menu.invalidate_recordset()
print('final tr', repr(menu.with_context(lang='tr_TR').name))
print('final raw', repr(menu.name))
