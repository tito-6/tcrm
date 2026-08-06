import { describe, expect, test } from "@tcrm/hoot";
import { createSpreadsheetWithChart } from "@spreadsheet/../tests/helpers/chart";
import { createBasicChart } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeMockEnv } from "@web/../tests/web_test_helpers";

import { Model } from "@tcrm/o-spreadsheet";

const chartId = "uuid1";

describe.current.tags("headless");

defineSpreadsheetModels();

test("Links between charts and ir.menus are correctly imported/exported", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_tcrm_MENU_TO_CHART", {
        chartId,
        tcrmMenuId: 1,
    });
    const exportedData = model.exportData();
    expect(exportedData.charttcrmMenusReferences[chartId]).toBe(1, {
        message: "Link to tcrm menu is exported",
    });
    const importedModel = new Model(exportedData, { custom: { env } });
    const chartMenu = importedModel.getters.getCharttcrmMenu(chartId);
    expect(chartMenu.id).toBe(1, { message: "Link to tcrm menu is imported" });
});

test("Can undo-redo a LINK_tcrm_MENU_TO_CHART", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_tcrm_MENU_TO_CHART", {
        chartId,
        tcrmMenuId: 1,
    });
    expect(model.getters.getCharttcrmMenu(chartId).id).toBe(1);
    model.dispatch("REQUEST_UNDO");
    expect(model.getters.getCharttcrmMenu(chartId)).toBe(undefined);
    model.dispatch("REQUEST_REDO");
    expect(model.getters.getCharttcrmMenu(chartId).id).toBe(1);
});

test("link is removed when figure is deleted", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    createBasicChart(model, chartId);
    model.dispatch("LINK_tcrm_MENU_TO_CHART", {
        chartId,
        tcrmMenuId: 1,
    });
    expect(model.getters.getCharttcrmMenu(chartId).id).toBe(1);
    model.dispatch("DELETE_FIGURE", {
        sheetId: model.getters.getActiveSheetId(),
        figureId: model.getters.getFigureIdFromChartId(chartId),
    });
    expect(model.getters.getCharttcrmMenu(chartId)).toBe(undefined);
});

test("Links of Tcrm charts are duplicated when duplicating a sheet", async function () {
    const { model } = await createSpreadsheetWithChart({ type: "tcrm_pie" });
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("DUPLICATE_SHEET", {
        sheetId,
        sheetIdTo: secondSheetId,
        sheetNameTo: "Next Name",
    });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getCharttcrmMenu(newChartId)).toEqual(
        model.getters.getCharttcrmMenu(chartId)
    );
});

test("Links of standard charts are duplicated when duplicating a sheet", async function () {
    const env = await makeMockEnv();
    const model = new Model({}, { custom: { env } });
    const sheetId = model.getters.getActiveSheetId();
    const secondSheetId = "mySecondSheetId";
    createBasicChart(model, chartId);
    model.dispatch("LINK_tcrm_MENU_TO_CHART", {
        chartId,
        tcrmMenuId: 1,
    });
    model.dispatch("DUPLICATE_SHEET", {
        sheetId,
        sheetIdTo: secondSheetId,
        sheetNameTo: "Next Name",
    });
    const newChartId = model.getters.getChartIds(secondSheetId)[0];
    expect(model.getters.getCharttcrmMenu(newChartId)).toEqual(
        model.getters.getCharttcrmMenu(chartId)
    );
});
