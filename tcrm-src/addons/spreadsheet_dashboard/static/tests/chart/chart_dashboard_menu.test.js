import { describe, expect, test } from "@tcrm/hoot";
import { Model } from "@tcrm/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { tcrmDataProvider } from "@spreadsheet/data_sources/tcrm_data_provider";
import { createDashboardActionWithData } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("can change granularity", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { tcrmDataProvider: new tcrmDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "tcrm_line", {
        metaData: {
            groupBy: ["date:month"],
            resModel: "partner",
            measure: "__count",
            order: null,
        },
    });
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect("select.o-chart-dashboard-item").toHaveValue("month");
    await contains("select.o-chart-dashboard-item", { visible: false }).select("quarter");
    expect(model.getters.getChartGranularity(chartId)).toEqual({
        fieldName: "date",
        granularity: "quarter",
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
});
