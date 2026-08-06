import { components } from "@tcrm/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.ChartJsComponent.prototype, {
    createChart(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addtcrmMenuPluginToChartData(chartData);
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addtcrmMenuPluginToChartData(chartData);
        }
        super.updateChartJs(chartData);
    },
    addtcrmMenuPluginToChartData(chartData) {
        chartData.chartJsConfig.options.plugins.charttcrmMenuPlugin = {
            env: this.env,
            menu: this.env.model.getters.getCharttcrmMenu(this.props.chartId),
        };
        return chartData;
    },
});
