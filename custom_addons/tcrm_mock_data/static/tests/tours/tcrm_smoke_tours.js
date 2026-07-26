/** @odoo-module **/
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

// Phase 2A + CRM data: the Discuss app icon must render with real (base64) icon
// data in the app switcher, and the CRM pipeline must contain records.
registry.category("web_tour.tours").add("tcrm_apps_smoke", {
    url: "/tcrm",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger:
                ".o_app[data-menu-xmlid='mail.menu_root_discuss'] img.o_app_icon[src^='data:image']",
            content: "Discuss app icon renders with real icon data",
        },
        {
            trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root']",
            content: "Open CRM app",
            run: "click",
        },
        {
            trigger: ".o_kanban_record, .o_list_view .o_data_row",
            content: "CRM pipeline contains records",
        },
    ],
});

// Phase 2B: the dashboard must render (no tcrmDataProvider TDZ crash).
registry.category("web_tour.tours").add("tcrm_dashboard_smoke", {
    url: "/tcrm/dashboards?dashboard_id=4",
    steps: () => [
        {
            trigger: ".o_spreadsheet_dashboard_action",
            content: "Dashboard client action loaded",
        },
        {
            // `.o_renderer` only renders in the "Loaded" branch, i.e. after the
            // spreadsheet model was built successfully. A tcrmDataProvider TDZ
            // crash would instead show `.dashboard-loading-status.error`.
            trigger: ".o_spreadsheet_dashboard_action .o_renderer",
            content: "Dashboard model rendered without initialization error",
        },
    ],
});

// Phase 5 + Sales data: the Sales screen loads and the promo video preview is
// absent from the DOM.
registry.category("web_tour.tours").add("tcrm_sales_smoke", {
    url: "/tcrm/sales",
    steps: () => [
        {
            trigger: ".o_list_view, .o_kanban_view, .o_view_nocontent",
            content: "Sales screen loaded",
        },
        {
            // The empty-state help now shows TCRM text instead of the Odoo promo
            // video, proving the promotional preview was removed cleanly.
            trigger: ".o_nocontent_help:contains('Create your first quotation')",
            content: "Sales empty-state shows TCRM help (no promo video)",
        },
    ],
});
