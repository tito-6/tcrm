# Restore missing / broken root-menu icons for the red-star apps dropdown.
# Run via:  PYTHONPATH=d:/tcrm/tcrm-src venv/Scripts/python.exe tcrm-src/tcrm-bin shell -c tcrm.conf -d tcrm_master < fix_menu_icons.py
# Or paste into an interactive Odoo shell.

ICON_BY_XMLID = {
    "base.menu_administration": "base,static/description/settings.png",
    "base.menu_management": "base,static/description/modules.png",
    "base.menu_tests": "base,static/description/exception.png",
    "tcrm_saas_core.menu_tcrm_root": "tcrm_saas_core,static/description/icon.png",
    "tcrm_ai.menu_tcrm_ai_root": "tcrm_ai,static/description/icon.png",
    "tcrm_ai_research.menu_tcrm_ai_research_root": "tcrm_ai_research,static/description/icon.png",
    "tcrm_research_hub.menu_research_hub_root": "tcrm_research_hub,static/description/icon.png",
    "tcrm_propertio.menu_propertio_root": "tcrm_propertio,static/description/icon.png",
}

Menu = env["ir.ui.menu"].sudo()
fixed = []
for xmlid, web_icon in ICON_BY_XMLID.items():
    menu = env.ref(xmlid, raise_if_not_found=False)
    if not menu:
        print(f"SKIP missing xmlid: {xmlid}")
        continue
    # Force rewrite so web_icon_data is recomputed from module files
    menu.write({"web_icon": web_icon})
    fixed.append(f"{menu.display_name} -> {web_icon}")
    print(f"OK {xmlid}: {menu.display_name}")

env.registry.clear_cache()
env.cr.commit()
print(f"Done. Restored {len(fixed)} menu icons.")
