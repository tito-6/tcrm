/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("tcrm_ai_settings_tour", {
    test: true,
    url: "/web",
    steps: () => [
        {
            content: "Open app menu",
            trigger: ".o_navbar_apps_menu button, .o_menu_toggle",
            run: "click",
        },
        {
            content: "Open TCRM AI if present",
            trigger: ".o_app[data-menu-xmlid='tcrm_ai.menu_tcrm_ai_root'], a:contains('TCRM AI')",
            run: "click",
            isCheck: false,
        },
    ],
});
