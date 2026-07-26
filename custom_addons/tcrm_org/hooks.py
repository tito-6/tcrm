# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Force Turkish menu labels for the Organizasyon hub."""
    menu = env.ref("crm.sales_team_menu_team_pipeline", raise_if_not_found=False)
    if menu:
        menu.with_context(lang=None).write(
            {
                "name": "Organizasyon",
            }
        )
        # Clear stale TR translation "Ekipler" from stock CRM
        env["ir.ui.menu"].browse(menu.id).update_field_translations(
            "name",
            {"tr_TR": "Organizasyon", "en_US": "Organization"},
        )

    action = env.ref("sales_team.crm_team_action_pipeline", raise_if_not_found=False)
    if action:
        action.with_context(lang=None).write({"name": "Ekipler"})
        action.update_field_translations(
            "name",
            {"tr_TR": "Ekipler", "en_US": "Teams"},
        )
