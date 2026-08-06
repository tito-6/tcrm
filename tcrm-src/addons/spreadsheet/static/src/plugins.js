import { CorePlugin, CoreViewPlugin, UIPlugin } from "@tcrm/o-spreadsheet";

/**
 * An o-spreadsheet core plugin with access to all custom Tcrm plugins
 * @type {import("@spreadsheet").tcrmCorePluginConstructor}
 **/
export const tcrmCorePlugin = CorePlugin;

/**
 * An o-spreadsheet CoreView plugin with access to all custom Tcrm plugins
 * @type {import("@spreadsheet").tcrmUIPluginConstructor}
 **/
export const tcrmCoreViewPlugin = CoreViewPlugin;

/**
 * An o-spreadsheet UI plugin with access to all custom Tcrm plugins
 * @type {import("@spreadsheet").tcrmUIPluginConstructor}
 **/
export const tcrmUIPlugin = UIPlugin;
