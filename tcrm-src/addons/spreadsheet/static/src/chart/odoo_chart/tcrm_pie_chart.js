import { registries, chartHelpers } from "@tcrm/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { tcrmChart } from "./tcrm_chart";
import { ontcrmChartItemHover, ontcrmChartItemClick } from "./tcrm_chart_helpers";

const { chartRegistry } = registries;

const {
    getPieChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getPieChartTooltip,
    getChartTitle,
    getPieChartLegend,
    getChartShowValues,
    getTopPaddingForDashboard,
} = chartHelpers;

export class tcrmPieChart extends tcrmChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.isDoughnut = definition.isDoughnut;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            isDoughnut: this.isDoughnut,
        };
    }
}

chartRegistry.add("tcrm_pie", {
    match: (type) => type === "tcrm_pie",
    createChart: (definition, sheetId, getters) => new tcrmPieChart(definition, sheetId, getters),
    getChartRuntime: createtcrmChartRuntime,
    validateChartDefinition: (validator, definition) =>
        tcrmPieChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => tcrmPieChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => tcrmPieChart.getDefinitionFromContextCreation(),
    name: _t("Pie"),
});

function createtcrmChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();
    const definition = chart.getDefinition();
    definition.dataSets = datasets.map(() => ({ trend: definition.trend }));

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale: getters.getLocale(),
        topPadding: getTopPaddingForDashboard(definition, getters),
    };

    const config = {
        type: definition.isDoughnut ? "doughnut" : "pie",
        data: {
            labels: chartData.labels,
            datasets: getPieChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition, chartData),
            plugins: {
                title: getChartTitle(definition, getters),
                legend: getPieChartLegend(definition, chartData),
                tooltip: getPieChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            onHover: ontcrmChartItemHover(),
            onClick: ontcrmChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
