import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@tcrm/o-spreadsheet";
import { useService } from "@web/core/utils/hooks";
import { navigateTotcrmMenu } from "../odoo_chart/tcrm_chart_helpers";

patch(spreadsheet.components.FigureComponent.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    get chartId() {
        if (this.props.figureUI.tag !== "chart" && this.props.figureUI.tag !== "carousel") {
            return undefined;
        }
        return this.env.model.getters.getChartIdFromFigureId(this.props.figureUI.id);
    },
    async navigateTotcrmMenu(newWindow) {
        const menu = this.env.model.getters.getCharttcrmMenu(this.chartId);
        await navigateTotcrmMenu(menu, this.actionService, this.notificationService, newWindow);
    },
    get hastcrmMenu() {
        return this.chartId && this.env.model.getters.getCharttcrmMenu(this.chartId) !== undefined;
    },
});

patch(spreadsheet.components.ScorecardChart.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    async navigateTotcrmMenu(newWindow) {
        const menu = this.env.model.getters.getCharttcrmMenu(this.props.chartId);
        await navigateTotcrmMenu(menu, this.actionService, this.notificationService, newWindow);
    },
    get hastcrmMenu() {
        return this.env.model.getters.getCharttcrmMenu(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.isDashboard() && this.hastcrmMenu) {
            await this.navigateTotcrmMenu();
        }
    },
});

patch(spreadsheet.components.GaugeChartComponent.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.notificationService = useService("notification");
    },
    async navigateTotcrmMenu(newWindow) {
        const menu = this.env.model.getters.getCharttcrmMenu(this.props.chartId);
        await navigateTotcrmMenu(menu, this.actionService, this.notificationService, newWindow);
    },
    get hastcrmMenu() {
        return this.env.model.getters.getCharttcrmMenu(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.isDashboard() && this.hastcrmMenu) {
            await this.navigateTotcrmMenu();
        }
    },
});
