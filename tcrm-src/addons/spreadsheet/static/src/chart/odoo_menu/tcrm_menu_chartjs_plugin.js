import {
    navigateTotcrmMenu,
    isChartJSMiddleClick,
} from "@spreadsheet/chart/odoo_chart/tcrm_chart_helpers";

export const charttcrmMenuPlugin = {
    id: "charttcrmMenuPlugin",
    afterEvent(chart, { event }, { env, menu }) {
        const isDashboard = env?.model.getters.isDashboard();
        event.native.target.style.cursor = menu && isDashboard ? "pointer" : "";

        const middleClick = isChartJSMiddleClick(event);
        if (
            (event.type !== "click" && !middleClick) ||
            !menu ||
            !isDashboard ||
            event.native.defaultPrevented
        ) {
            return;
        }
        navigateTotcrmMenu(menu, env.services.action, env.services.notification, middleClick);
    },
};
