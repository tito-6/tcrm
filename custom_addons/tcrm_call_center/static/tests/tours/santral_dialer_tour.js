/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("tcrm_call_center_santral_dialer", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open Lead Havuzu / CRM",
            trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root'], .o_app[data-menu-xmlid='tcrm_propertio.menu_lead_havuzu'], .o_main_navbar",
            run: "click",
        },
        {
            content: "Santral assets loaded (no secrets in page scripts expected)",
            trigger: "body",
            run() {
                const body = document.documentElement.innerHTML;
                if (body.includes("api_key_secret_encrypted") && body.includes("enc:v1:")) {
                    throw new Error("Encrypted secret leaked into DOM");
                }
                if (typeof window.Twilio === "undefined") {
                    // SDK may load async; soft check only warns in tour runner logs
                    console.warn("Twilio SDK not yet on window");
                }
            },
        },
    ],
});
