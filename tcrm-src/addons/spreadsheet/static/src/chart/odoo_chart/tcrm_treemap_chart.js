import { registries, chartHelpers } from "@tcrm/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { tcrmChart } from "./tcrm_chart";
import { ontcrmChartItemHover, onTreemaptcrmChartItemClick } from "./tcrm_chart_helpers";

const { chartRegistry } = registries;

const {
    getTreeMapChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getChartTitle,
    getTreeMapChartTooltip,
} = chartHelpers;

export class tcrmTreemapChart extends tcrmChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.showLabels = definition.showLabels;
        this.valuesDesign = definition.valuesDesign;
        this.coloringOptions = definition.coloringOptions;
        this.headerDesign = definition.headerDesign;
        this.showHeaders = definition.showHeaders;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            showLabels: this.showLabels,
            valuesDesign: this.valuesDesign,
            coloringOptions: this.coloringOptions,
            headerDesign: this.headerDesign,
            showHeaders: this.showHeaders,
        };
    }
}

chartRegistry.add("tcrm_treemap", {
    match: (type) => type === "tcrm_treemap",
    createChart: (definition, sheetId, getters) =>
        new tcrmTreemapChart(definition, sheetId, getters),
    getChartRuntime: createtcrmChartRuntime,
    validateChartDefinition: (validator, definition) =>
        tcrmTreemapChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => tcrmTreemapChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () =>
        tcrmTreemapChart.getDefinitionFromContextCreation(),
    name: _t("Treemap"),
});

function createtcrmChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getHierarchicalData();

    const definition = chart.getDefinition();
    const locale = getters.getLocale();

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
    };

    const config = {
        type: "treemap",
        data: {
            labels: chartData.labels,
            datasets: getTreeMapChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition, chartData),
            plugins: {
                title: getChartTitle(definition, getters),
                legend: { display: false },
                tooltip: getTreeMapChartTooltip(definition, chartData),
            },
            onHover: ontcrmChartItemHover(),
            onClick: onTreemaptcrmChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
