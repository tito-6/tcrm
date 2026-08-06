import { registries, chartHelpers } from "@tcrm/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { tcrmChart } from "./tcrm_chart";
import { ontcrmChartItemHover, ontcrmChartItemClick } from "./tcrm_chart_helpers";

const { chartRegistry } = registries;

const {
    getFunnelChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getChartTitle,
    getChartShowValues,
    getFunnelChartScales,
    getFunnelChartTooltip,
    makeDatasetsCumulative,
} = chartHelpers;

export class tcrmFunnelChart extends tcrmChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.cumulative = definition.cumulative;
        this.funnelColors = definition.funnelColors;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            cumulative: this.cumulative,
            funnelColors: this.funnelColors,
        };
    }
}

chartRegistry.add("tcrm_funnel", {
    match: (type) => type === "tcrm_funnel",
    createChart: (definition, sheetId, getters) =>
        new tcrmFunnelChart(definition, sheetId, getters),
    getChartRuntime: createtcrmChartRuntime,
    validateChartDefinition: (validator, definition) =>
        tcrmFunnelChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => tcrmFunnelChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => tcrmFunnelChart.getDefinitionFromContextCreation(),
    name: _t("Funnel"),
});

function createtcrmChartRuntime(chart, getters) {
    const definition = chart.getDefinition();
    const background = chart.background || "#FFFFFF";
    let { datasets, labels } = chart.dataSource.getData();
    if (definition.cumulative) {
        datasets = makeDatasetsCumulative(datasets, "desc");
    }

    const locale = getters.getLocale();

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
    };

    const config = {
        type: "funnel",
        data: {
            labels: chartData.labels,
            datasets: getFunnelChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            indexAxis: "y",
            layout: getChartLayout(definition, chartData),
            scales: getFunnelChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition, getters),
                legend: { display: false },
                tooltip: getFunnelChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            onHover: ontcrmChartItemHover(),
            onClick: ontcrmChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
