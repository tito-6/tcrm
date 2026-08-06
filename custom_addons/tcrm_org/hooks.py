# -*- coding: utf-8 -*-


def _hide_crm_org_menus(env):
    """Remove HR org screens from CRM; they belong under Çalışanlar."""
    xmlids = (
        "crm.sales_team_menu_team_pipeline",
        "crm.crm_team_config",
        "crm.crm_team_member_config",
        "tcrm_org.menu_tcrm_org_chart",
        "tcrm_org.menu_tcrm_org_departments",
        "tcrm_org.menu_tcrm_org_teams",
        "tcrm_org.menu_tcrm_org_users",
    )
    for xmlid in xmlids:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu and menu.active:
            menu.sudo().write({"active": False})

    # Ensure access menu sits under CRM configuration (not the hidden hub).
    access = env.ref("tcrm_org.menu_tcrm_org_access", raise_if_not_found=False)
    config = env.ref("crm.crm_menu_config", raise_if_not_found=False)
    if access and config:
        access.sudo().write({
            "parent_id": config.id,
            "active": True,
            "sequence": 90,
        })


def post_init_hook(env):
    _hide_crm_org_menus(env)
