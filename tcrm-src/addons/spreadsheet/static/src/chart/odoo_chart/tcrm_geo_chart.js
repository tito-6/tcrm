import { registries, chartHelpers } from "@tcrm/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { tcrmChart } from "./tcrm_chart";
import { onGeotcrmChartItemHover, onGeotcrmChartItemClick } from "./tcrm_chart_helpers";

const { chartRegistry } = registries;

const {
    getGeoChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getChartTitle,
    getGeoChartScales,
    getGeoChartTooltip,
} = chartHelpers;

export class tcrmGeoChart extends tcrmChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.colorScale = definition.colorScale;
        this.missingValueColor = definition.missingValueColor;
        this.region = definition.region;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            colorScale: this.colorScale,
            missingValueColor: this.missingValueColor,
            region: this.region,
        };
    }
}

chartRegistry.add("tcrm_geo", {
    match: (type) => type === "tcrm_geo",
    createChart: (definition, sheetId, getters) => new tcrmGeoChart(definition, sheetId, getters),
    getChartRuntime: createtcrmChartRuntime,
    validateChartDefinition: (validator, definition) =>
        tcrmGeoChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => tcrmGeoChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => tcrmGeoChart.getDefinitionFromContextCreation(),
    name: _t("Geo"),
});

function createtcrmChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();

    const definition = chart.getDefinition();
    const locale = getters.getLocale();

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
        availableRegions: getters.getGeoChartAvailableRegions(),
        geoFeatureNameToId: getters.geoFeatureNameToId,
        getGeoJsonFeatures: getters.getGeoJsonFeatures,
    };

    const config = {
        type: "choropleth",
        data: {
            datasets: getGeoChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition, chartData),
            scales: getGeoChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition, getters),
                tooltip: getGeoChartTooltip(definition, chartData),
                legend: { display: false },
            },
            onHover: onGeotcrmChartItemHover(),
            onClick: onGeotcrmChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
