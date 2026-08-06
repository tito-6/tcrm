import { CorePlugin, Model, UID } from "@tcrm/o-spreadsheet";
import { CharttcrmMenuPlugin, tcrmChartCorePlugin, tcrmChartCoreViewPlugin } from "@spreadsheet/chart";
import { CurrencyPlugin } from "@spreadsheet/currency/plugins/currency";
import { AccountingPlugin } from "addons/spreadsheet_account/static/src/plugins/accounting_plugin";
import { GlobalFiltersCorePlugin, GlobalFiltersCoreViewPlugin } from "@spreadsheet/global_filters";
import { ListCorePlugin, ListCoreViewPlugin } from "@spreadsheet/list";
import { IrMenuPlugin } from "@spreadsheet/ir_ui_menu/ir_ui_menu_plugin";
import { PivottcrmCorePlugin } from "@spreadsheet/pivot";
import { PivotCoreGlobalFilterPlugin } from "@spreadsheet/pivot/plugins/pivot_core_global_filter_plugin";

type Getters = Model["getters"];
type CoreGetters = CorePlugin["getters"];

/**
 * Union of all getter names of a plugin.
 *
 * e.g. With the following plugin
 * @example
 * class MyPlugin {
 *   static getters = [
 *     "getCell",
 *     "getCellValue",
 *   ] as const;
 *   getCell() { ... }
 *   getCellValue() { ... }
 * }
 * type Names = GetterNames<typeof MyPlugin>
 * // is equivalent to "getCell" | "getCellValue"
 */
type GetterNames<Plugin extends { getters: readonly string[] }> = Plugin["getters"][number];

/**
 * Extract getter methods from a plugin, based on its `getters` static array.
 * @example
 * class MyPlugin {
 *   static getters = [
 *     "getCell",
 *     "getCellValue",
 *   ] as const;
 *   getCell() { ... }
 *   getCellValue() { ... }
 * }
 * type MyPluginGetters = PluginGetters<typeof MyPlugin>;
 * // MyPluginGetters is equivalent to:
 * // {
 * //   getCell: () => ...,
 * //   getCellValue: () => ...,
 * // }
 */
type PluginGetters<Plugin extends { new (...args: unknown[]): any; getters: readonly string[] }> =
    Pick<InstanceType<Plugin>, GetterNames<Plugin>>;

declare module "@spreadsheet" {
    /**
     * Add getters from custom plugins defined in tcrm
     */

    interface tcrmCoreGetters extends CoreGetters {}
    interface tcrmCoreGetters extends PluginGetters<typeof GlobalFiltersCorePlugin> {}
    interface tcrmCoreGetters extends PluginGetters<typeof ListCorePlugin> {}
    interface tcrmCoreGetters extends PluginGetters<typeof tcrmChartCorePlugin> {}
    interface tcrmCoreGetters extends PluginGetters<typeof CharttcrmMenuPlugin> {}
    interface tcrmCoreGetters extends PluginGetters<typeof IrMenuPlugin> {}
    interface tcrmCoreGetters extends PluginGetters<typeof PivottcrmCorePlugin> {}
    interface tcrmCoreGetters extends PluginGetters<typeof PivotCoreGlobalFilterPlugin> {}

    interface tcrmGetters extends Getters {}
    interface tcrmGetters extends tcrmCoreGetters {}
    interface tcrmGetters extends PluginGetters<typeof GlobalFiltersCoreViewPlugin> {}
    interface tcrmGetters extends PluginGetters<typeof ListCoreViewPlugin> {}
    interface tcrmGetters extends PluginGetters<typeof tcrmChartCoreViewPlugin> {}
    interface tcrmGetters extends PluginGetters<typeof CurrencyPlugin> {}
    interface tcrmGetters extends PluginGetters<typeof AccountingPlugin> {}
}
