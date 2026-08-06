import * as spreadsheet from "@tcrm/o-spreadsheet";
import { tcrmChartCorePlugin } from "./plugins/tcrm_chart_core_plugin";
import { CharttcrmMenuPlugin } from "./plugins/chart_tcrm_menu_plugin";
import { tcrmChartCoreViewPlugin } from "./plugins/tcrm_chart_core_view_plugin";
import { _t } from "@web/core/l10n/translation";
import { charttcrmMenuPlugin } from "./odoo_menu/tcrm_menu_chartjs_plugin";

const { chartComponentRegistry, chartSubtypeRegistry, chartJsExtensionRegistry } =
    spreadsheet.registries;
const { ChartJsComponent, ZoomableChartJsComponent } = spreadsheet.components;

chartComponentRegistry.add("tcrm_bar", ZoomableChartJsComponent);
chartComponentRegistry.add("tcrm_line", ZoomableChartJsComponent);
chartComponentRegistry.add("tcrm_pie", ChartJsComponent);
chartComponentRegistry.add("tcrm_radar", ChartJsComponent);
chartComponentRegistry.add("tcrm_sunburst", ChartJsComponent);
chartComponentRegistry.add("tcrm_treemap", ChartJsComponent);
chartComponentRegistry.add("tcrm_waterfall", ZoomableChartJsComponent);
chartComponentRegistry.add("tcrm_pyramid", ChartJsComponent);
chartComponentRegistry.add("tcrm_scatter", ZoomableChartJsComponent);
chartComponentRegistry.add("tcrm_combo", ZoomableChartJsComponent);
chartComponentRegistry.add("tcrm_geo", ChartJsComponent);
chartComponentRegistry.add("tcrm_funnel", ChartJsComponent);

chartSubtypeRegistry.add("tcrm_line", {
    matcher: (definition) =>
        definition.type === "tcrm_line" && !definition.stacked && !definition.fillArea,
    subtypeDefinition: { stacked: false, fillArea: false },
    displayName: _t("Line"),
    chartSubtype: "tcrm_line",
    chartType: "tcrm_line",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.LINE_CHART",
});
chartSubtypeRegistry.add("tcrm_stacked_line", {
    matcher: (definition) =>
        definition.type === "tcrm_line" && definition.stacked && !definition.fillArea,
    subtypeDefinition: { stacked: true, fillArea: false },
    displayName: _t("Stacked Line"),
    chartSubtype: "tcrm_stacked_line",
    chartType: "tcrm_line",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.STACKED_LINE_CHART",
});
chartSubtypeRegistry.add("tcrm_area", {
    matcher: (definition) =>
        definition.type === "tcrm_line" && !definition.stacked && definition.fillArea,
    subtypeDefinition: { stacked: false, fillArea: true },
    displayName: _t("Area"),
    chartSubtype: "tcrm_area",
    chartType: "tcrm_line",
    category: "area",
    preview: "o-spreadsheet-ChartPreview.AREA_CHART",
});
chartSubtypeRegistry.add("tcrm_stacked_area", {
    matcher: (definition) =>
        definition.type === "tcrm_line" && definition.stacked && definition.fillArea,
    subtypeDefinition: { stacked: true, fillArea: true },
    displayName: _t("Stacked Area"),
    chartSubtype: "tcrm_stacked_area",
    chartType: "tcrm_line",
    category: "area",
    preview: "o-spreadsheet-ChartPreview.STACKED_AREA_CHART",
});
chartSubtypeRegistry.add("tcrm_bar", {
    matcher: (definition) =>
        definition.type === "tcrm_bar" && !definition.stacked && !definition.horizontal,
    subtypeDefinition: { stacked: false, horizontal: false },
    displayName: _t("Column"),
    chartSubtype: "tcrm_bar",
    chartType: "tcrm_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.COLUMN_CHART",
});
chartSubtypeRegistry.add("tcrm_stacked_bar", {
    matcher: (definition) =>
        definition.type === "tcrm_bar" && definition.stacked && !definition.horizontal,
    subtypeDefinition: { stacked: true, horizontal: false },
    displayName: _t("Stacked Column"),
    chartSubtype: "tcrm_stacked_bar",
    chartType: "tcrm_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.STACKED_COLUMN_CHART",
});
chartSubtypeRegistry.add("tcrm_horizontal_bar", {
    matcher: (definition) =>
        definition.type === "tcrm_bar" && !definition.stacked && definition.horizontal,
    subtypeDefinition: { stacked: false, horizontal: true },
    displayName: _t("Bar"),
    chartSubtype: "tcrm_horizontal_bar",
    chartType: "tcrm_bar",
    category: "bar",
    preview: "o-spreadsheet-ChartPreview.BAR_CHART",
});
chartSubtypeRegistry.add("tcrm_horizontal_stacked_bar", {
    matcher: (definition) =>
        definition.type === "tcrm_bar" && definition.stacked && definition.horizontal,
    subtypeDefinition: { stacked: true, horizontal: true },
    displayName: _t("Stacked Bar"),
    chartSubtype: "tcrm_horizontal_stacked_bar",
    chartType: "tcrm_bar",
    category: "bar",
    preview: "o-spreadsheet-ChartPreview.STACKED_BAR_CHART",
});
chartSubtypeRegistry.add("tcrm_combo", {
    displayName: _t("Combo"),
    chartSubtype: "tcrm_combo",
    chartType: "tcrm_combo",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.COMBO_CHART",
});
chartSubtypeRegistry.add("tcrm_pie", {
    displayName: _t("Pie"),
    matcher: (definition) => definition.type === "tcrm_pie" && !definition.isDoughnut,
    subtypeDefinition: { isDoughnut: false },
    chartSubtype: "tcrm_pie",
    chartType: "tcrm_pie",
    category: "pie",
    preview: "o-spreadsheet-ChartPreview.PIE_CHART",
});
chartSubtypeRegistry.add("tcrm_doughnut", {
    matcher: (definition) => definition.type === "tcrm_pie" && definition.isDoughnut,
    subtypeDefinition: { isDoughnut: true },
    displayName: _t("Doughnut"),
    chartSubtype: "tcrm_doughnut",
    chartType: "tcrm_pie",
    category: "pie",
    preview: "o-spreadsheet-ChartPreview.DOUGHNUT_CHART",
});
chartSubtypeRegistry.add("tcrm_scatter", {
    displayName: _t("Scatter"),
    chartType: "tcrm_scatter",
    chartSubtype: "tcrm_scatter",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.SCATTER_CHART",
});
chartSubtypeRegistry.add("tcrm_waterfall", {
    displayName: _t("Waterfall"),
    chartSubtype: "tcrm_waterfall",
    chartType: "tcrm_waterfall",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.WATERFALL_CHART",
});
chartSubtypeRegistry.add("tcrm_pyramid", {
    displayName: _t("Population Pyramid"),
    chartSubtype: "tcrm_pyramid",
    chartType: "tcrm_pyramid",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.POPULATION_PYRAMID_CHART",
});
chartSubtypeRegistry.add("tcrm_radar", {
    matcher: (definition) => definition.type === "tcrm_radar" && !definition.fillArea,
    displayName: _t("Radar"),
    chartSubtype: "tcrm_radar",
    chartType: "tcrm_radar",
    subtypeDefinition: { fillArea: false },
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.RADAR_CHART",
});
chartSubtypeRegistry.add("tcrm_filled_radar", {
    matcher: (definition) => definition.type === "tcrm_radar" && !!definition.fillArea,
    displayName: _t("Filled Radar"),
    chartType: "tcrm_radar",
    chartSubtype: "tcrm_filled_radar",
    subtypeDefinition: { fillArea: true },
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.FILLED_RADAR_CHART",
});
chartSubtypeRegistry.add("tcrm_geo", {
    displayName: _t("Geo chart"),
    chartType: "tcrm_geo",
    chartSubtype: "tcrm_geo",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.GEO_CHART",
});
chartSubtypeRegistry.add("tcrm_funnel", {
    matcher: (definition) => definition.type === "tcrm_funnel",
    displayName: _t("Funnel"),
    chartType: "tcrm_funnel",
    chartSubtype: "tcrm_funnel",
    subtypeDefinition: { cumulative: true },
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.FUNNEL_CHART",
});
chartSubtypeRegistry.add("tcrm_treemap", {
    displayName: _t("Treemap"),
    chartType: "tcrm_treemap",
    chartSubtype: "tcrm_treemap",
    category: "hierarchical",
    preview: "o-spreadsheet-ChartPreview.TREE_MAP_CHART",
});
chartSubtypeRegistry.add("tcrm_sunburst", {
    displayName: _t("Sunburst"),
    chartType: "tcrm_sunburst",
    chartSubtype: "tcrm_sunburst",
    category: "hierarchical",
    preview: "o-spreadsheet-ChartPreview.SUNBURST_CHART",
});

chartJsExtensionRegistry.add("charttcrmMenuPlugin", {
    register: (Chart) => Chart.register(charttcrmMenuPlugin),
    unregister: (Chart) => Chart.unregister(charttcrmMenuPlugin),
});

export { tcrmChartCorePlugin, CharttcrmMenuPlugin, tcrmChartCoreViewPlugin };
