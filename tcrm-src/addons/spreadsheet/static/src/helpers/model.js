// @ts-check

import { parse, helpers, iterateAstNodes } from "@tcrm/o-spreadsheet";
import { isLoadingError } from "@spreadsheet/o_spreadsheet/errors";
import { tcrmSpreadsheetModel } from "@spreadsheet/model";
import { tcrmDataProvider } from "@spreadsheet/data_sources/tcrm_data_provider";

const { formatValue, isDefined, toCartesian, toXC } = helpers;
import {
    isMarkdownViewUrl,
    isMarkdownIrMenuIdUrl,
    isIrMenuXmlUrl,
} from "@spreadsheet/ir_ui_menu/tcrm_menu_link_cell";

/**
 * @typedef {import("@spreadsheet").tcrmSpreadsheetModel} tcrmSpreadsheetModel
 */

export async function fetchSpreadsheetModel(env, resModel, resId) {
    const { data, revisions } = await env.services.http.get(
        `/spreadsheet/data/${resModel}/${resId}`
    );
    return createSpreadsheetModel({ env, data, revisions });
}

export function createSpreadsheetModel({ env, data, revisions }) {
    // `dataProvider` must not reuse the imported class name `tcrmDataProvider`,
    // otherwise the `const` shadows the import and `new tcrmDataProvider(env)` hits
    // a temporal-dead-zone ReferenceError. Keep the class name for `new`.
    const dataProvider = new tcrmDataProvider(env);
    const model = new tcrmSpreadsheetModel(
        data,
        { custom: { env, tcrmDataProvider: dataProvider } },
        revisions
    );
    return model;
}

/**
 * @param {tcrmSpreadsheetModel} model
 */
export async function waitFortcrmSources(model) {
    const promises = model.getters
        .gettcrmChartIds()
        .map((chartId) => model.getters.getChartDataSource(chartId).load());
    promises.push(
        ...model.getters
            .getPivotIds()
            .filter((pivotId) => model.getters.getPivotCoreDefinition(pivotId).type === "TCRM")
            .map((pivotId) => model.getters.getPivot(pivotId))
            .map((pivot) => pivot.load())
    );
    promises.push(
        ...model.getters
            .getListIds()
            .map((listId) => model.getters.getListDataSource(listId))
            .map((list) => list.load())
    );
    await Promise.all(promises);
}

/**
 * Ensure that the spreadsheet does not contains cells that are in loading state
 * @param {tcrmSpreadsheetModel} model
 * @returns {Promise<void>}
 */
export async function waitForDataLoaded(model) {
    await waitFortcrmSources(model);
    const tcrmDataProvider = model.config.custom.tcrmDataProvider;
    if (!tcrmDataProvider) {
        return;
    }
    await new Promise((resolve, reject) => {
        function check() {
            model.dispatch("EVALUATE_CELLS");
            if (isLoaded(model)) {
                tcrmDataProvider.removeEventListener("data-source-updated", check);
                resolve();
            }
        }
        tcrmDataProvider.addEventListener("data-source-updated", check);
        check();
    });
}

function containsLinkTotcrm(link) {
    if (link && link.url) {
        return (
            isMarkdownViewUrl(link.url) ||
            isIrMenuXmlUrl(link.url) ||
            isMarkdownIrMenuIdUrl(link.url)
        );
    }
}

/**
 * @param {tcrmSpreadsheetModel} model
 * @returns {Promise<object>}
 */
export async function freezetcrmData(model) {
    await waitForDataLoaded(model);
    const data = model.exportData();
    for (const sheet of Object.values(data.sheets)) {
        sheet.formats ??= {};
        for (const [xc, content] of Object.entries(sheet.cells)) {
            const { col, row } = toCartesian(xc);
            const sheetId = sheet.id;
            const position = { sheetId, col, row };
            const evaluatedCell = model.getters.getEvaluatedCell(position);
            if (containstcrmFunction(content)) {
                const pivotId = model.getters.getPivotIdFromPosition(position);
                if (pivotId && model.getters.getPivotCoreDefinition(pivotId).type !== "TCRM") {
                    continue;
                }
                sheet.cells[xc] = toFrozenContent(evaluatedCell);
                if (evaluatedCell.format) {
                    sheet.formats[xc] = getItemId(evaluatedCell.format, data.formats);
                }
                const spreadZone = model.getters.getSpreadZone(position);
                if (spreadZone) {
                    const { left, right, top, bottom } = spreadZone;
                    for (let row = top; row <= bottom; row++) {
                        for (let col = left; col <= right; col++) {
                            const xc = toXC(col, row);
                            const evaluatedCell = model.getters.getEvaluatedCell({
                                sheetId,
                                col,
                                row,
                            });
                            sheet.cells[xc] = toFrozenContent(evaluatedCell);
                            if (evaluatedCell.format) {
                                sheet.formats[xc] = getItemId(evaluatedCell.format, data.formats);
                            }
                        }
                    }
                }
            }
            if (containsLinkTotcrm(evaluatedCell.link)) {
                sheet.cells[xc] = evaluatedCell.link.label;
            }
        }
        for (const figure of sheet.figures) {
            if (
                figure.tag === "chart" &&
                (figure.data.type.startsWith("tcrm_") || figure.data.type === "geo")
            ) {
                const img = tcrmChartToImage(model, figure, figure.data.chartId);
                figure.tag = "image";
                figure.data = {
                    path: img,
                    size: { width: figure.width, height: figure.height },
                };
            } else if (figure.tag === "carousel") {
                const hasImageChart = figure.data.items.some((item) => {
                    if (item.type !== "chart") {
                        return false;
                    }
                    const chartDefinition = model.getters.getChartDefinition(item.chartId);
                    return (
                        chartDefinition.type.startsWith("tcrm_") || chartDefinition.type === "geo"
                    );
                });
                if (hasImageChart) {
                    const chartId = figure.data.items.find((item) => item.type === "chart").chartId;
                    figure.tag = "image";
                    figure.data = {
                        path: tcrmChartToImage(model, figure, chartId),
                        size: { width: figure.width, height: figure.height },
                    };
                }
            }
        }
    }
    if (data.pivots) {
        data.pivots = Object.fromEntries(
            Object.entries(data.pivots).filter(([id, def]) => def.type !== "TCRM")
        );
    }
    data.lists = {};
    exportGlobalFiltersToSheet(model, data);
    return data;
}

function toFrozenContent(evaluatedCell) {
    const value = evaluatedCell.value;
    if (value === "") {
        return '=""';
    }
    return value.toString();
}

/**
 * @param {tcrmSpreadsheetModel} model
 * @returns {object}
 */
function exportGlobalFiltersToSheet(model, data) {
    model.getters.exportSheetWithActiveFilters(data);
    const locale = model.getters.getLocale();
    for (const filter of data.globalFilters) {
        const content = model.getters.getFilterDisplayValue(filter.label);
        filter["value"] = content
            .flat()
            .filter(isDefined)
            .map(({ value, format }) => formatValue(value, { format, locale }))
            .filter((formattedValue) => formattedValue !== "")
            .join(", ");
    }
}

/**
 * copy-pasted from o-spreadsheet. Should be exported
 * Get the id of the given item (its key in the given dictionnary).
 * If the given item does not exist in the dictionary, it creates one with a new id.
 */
export function getItemId(item, itemsDic) {
    for (const [key, value] of Object.entries(itemsDic)) {
        if (value === item) {
            return parseInt(key, 10);
        }
    }

    // Generate new Id if the item didn't exist in the dictionary
    const ids = Object.keys(itemsDic);
    const maxId = ids.length === 0 ? 0 : Math.max(...ids.map((id) => parseInt(id, 10)));

    itemsDic[maxId + 1] = item;
    return maxId + 1;
}

/**
 *
 * @param {string | undefined} content
 * @returns {boolean}
 */
function containstcrmFunction(content) {
    if (
        !content ||
        !content.startsWith("=") ||
        (!content.toUpperCase().includes("TCRM.") &&
            !content.toUpperCase().includes("_T") &&
            !content.toUpperCase().includes("PIVOT"))
    ) {
        return false;
    }
    try {
        const ast = parse(content);
        return iterateAstNodes(ast).some(
            (ast) =>
                ast.type === "FUNCALL" &&
                (ast.value.toUpperCase().startsWith("TCRM.") ||
                    ast.value.toUpperCase().startsWith("_T") ||
                    ast.value.toUpperCase().startsWith("PIVOT"))
        );
    } catch {
        return false;
    }
}

/**
 * @param {tcrmSpreadsheetModel} model
 * @returns {boolean}
 */
function isLoaded(model) {
    for (const sheetId of model.getters.getSheetIds()) {
        for (const cell of Object.values(model.getters.getEvaluatedCells(sheetId))) {
            if (cell.type === "error" && isLoadingError(cell)) {
                return false;
            }
        }
    }
    return true;
}

/**
 * Return the chart figure as a base64 image.
 * "data:image/png;base64,iVBORw0KGg..."
 * @param {tcrmSpreadsheetModel} model
 * @param {object} figure
 * @param {string} chartId
 * @returns {string}
 */
function tcrmChartToImage(model, figure, chartId) {
    const runtime = model.getters.getChartRuntime(chartId);
    // wrap the canvas in a div with a fixed size because chart.js would
    // fill the whole page otherwise
    const div = document.createElement("div");
    div.style.width = `${figure.width}px`;
    div.style.height = `${figure.height}px`;
    const canvas = document.createElement("canvas");
    div.append(canvas);
    canvas.setAttribute("width", figure.width);
    canvas.setAttribute("height", figure.height);
    // we have to add the canvas to the DOM otherwise it won't be rendered
    document.body.append(div);
    if (!("chartJsConfig" in runtime)) {
        return "";
    }
    runtime.chartJsConfig.plugins = [backgroundColorPlugin];
    // @ts-ignore
    const chart = new Chart(canvas, runtime.chartJsConfig);
    const img = chart.toBase64Image();
    chart.destroy();
    div.remove();
    return img;
}

/**
 * Custom chart.js plugin to set the background color of the canvas
 * https://github.com/chartjs/Chart.js/blob/8fdf76f8f02d31684d34704341a5d9217e977491/docs/configuration/canvas-background.md
 */
const backgroundColorPlugin = {
    id: "customCanvasBackgroundColor",
    beforeDraw: (chart, args, options) => {
        const { ctx } = chart;
        ctx.save();
        ctx.globalCompositeOperation = "destination-over";
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, chart.width, chart.height);
        ctx.restore();
    },
};
