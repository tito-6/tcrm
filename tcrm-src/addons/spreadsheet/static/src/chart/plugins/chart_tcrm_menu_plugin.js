import { tcrmCorePlugin } from "@spreadsheet/plugins";
import { coreTypes, constants } from "@tcrm/o-spreadsheet";
const { FIGURE_ID_SPLITTER } = constants;

/** Plugin that link charts with Tcrm menus. It can contain either the Id of the tcrm menu, or its xml id. */
export class CharttcrmMenuPlugin extends tcrmCorePlugin {
    static getters = /** @type {const} */ (["getCharttcrmMenu"]);
    constructor(config) {
        super(config);
        this.tcrmMenuReference = {};
    }

    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "LINK_tcrm_MENU_TO_CHART":
                this.history.update("tcrmMenuReference", cmd.chartId, cmd.tcrmMenuId);
                break;
            case "DELETE_CHART":
                this.history.update("tcrmMenuReference", cmd.chartId, undefined);
                break;
            case "DUPLICATE_SHEET":
                this.updateOnDuplicateSheet(cmd.sheetId, cmd.sheetIdTo);
                break;
        }
    }

    updateOnDuplicateSheet(sheetIdFrom, sheetIdTo) {
        for (const oldChartId of this.getters.getChartIds(sheetIdFrom)) {
            const menu = this.tcrmMenuReference[oldChartId];
            if (!menu) {
                continue;
            }
            const chartIdBase = oldChartId.split(FIGURE_ID_SPLITTER).pop();
            const newChartId = `${sheetIdTo}${FIGURE_ID_SPLITTER}${chartIdBase}`;
            this.history.update("tcrmMenuReference", newChartId, menu);
        }
    }

    /**
     * Get tcrm menu linked to the chart
     *
     * @param {string} chartId
     * @returns {object | undefined}
     */
    getCharttcrmMenu(chartId) {
        const menuId = this.tcrmMenuReference[chartId];
        return menuId ? this.getters.getIrMenu(menuId) : undefined;
    }

    import(data) {
        if (data.charttcrmMenusReferences) {
            this.tcrmMenuReference = data.charttcrmMenusReferences;
        }
    }

    export(data) {
        data.charttcrmMenusReferences = this.tcrmMenuReference;
    }
}

coreTypes.add("LINK_tcrm_MENU_TO_CHART");
