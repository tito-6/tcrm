import base64
import logging
from odoo import api, SUPERUSER_ID
from odoo.modules import get_module_resource

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    replace_system_branding(env)
    update_menu_icons(env)
    update_module_icons(env)
    replace_odoo_branding_text(env)

def replace_system_branding(env):
    try:
        logo_path = get_module_resource('theme_tcrm', 'static/src/img', 'logo.png')
        if logo_path:
            with open(logo_path, 'rb') as f:
                logo_content = base64.b64encode(f.read())
            env['res.company'].search([]).write({'logo': logo_content})
    except Exception as e:
        _logger.error(f"Branding Hooks: {e}")

def get_tcrm_icon_svg(short_name, bg_color="#212529", text_color="#FFFFFF"):
    """Generate generic SVG icon"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="{bg_color}" rx="15" ry="15"/>
  <text x="50" y="55" font-family="sans-serif" font-size="35" font-weight="bold" fill="{text_color}" text-anchor="middle" dominant-baseline="middle">{short_name}</text>
</svg>"""

def update_menu_icons(env):
    """Replace Main Dashboard Icons"""
    menus = env['ir.ui.menu'].search([('parent_id', '=', False)])
    for menu in menus:
        # Generate Red/Blue/Dark icons based on app
        # Default: Dark Slate BG, White Text
        short_name = (menu.name or "APP")[:3].upper()
        svg = get_tcrm_icon_svg(short_name, bg_color="#0055FF") # Blue Cards per request "very blue is ok"
        
        try:
            menu.write({'web_icon_data': base64.b64encode(svg.encode('utf-8'))})
        except:
            pass

def update_module_icons(env):
    """
    Attempt to replace module icons in the 'Apps' list.
    Realistically, these are read from files. We can't change files of other modules.
    BUT we can try to update the 'icon_image' field if Odoo stores it.
    Odoo 18 uses 'icon' path. 
    Workaround: We only affect the 'Settings' apps list if we can.
    """
    # This is often hard to do persistently without file changes.
    # We will skip modifying other modules' files to stay safe.
    pass

def replace_odoo_branding_text(env):
    """Aggressive Text Replacement"""
    # 1. Update Translations
    translations = env['ir.translation'].search([
        '|', ('src', 'ilike', 'Odoo'), ('value', 'ilike', 'Odoo')
    ])
    for trans in translations:
        # Replace Odoo with TCRM
        new_val = (trans.value or '').replace('Odoo', 'TCRM').replace('odoo', 'tcrm')
        trans.write({'value': new_val})
        
    # 2. Config Params (Web Title etc)
    params = env['ir.config_parameter'].search([
        '|', ('key', 'ilike', 'title'), ('value', 'ilike', 'Odoo')
    ])
    for param in params:
        if 'database' not in param.key:
             param.value = param.value.replace('Odoo', 'TCRM')
