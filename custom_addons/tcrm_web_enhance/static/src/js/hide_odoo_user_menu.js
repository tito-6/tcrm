/** @odoo-module **/

/**
 * Strip external Odoo/Chrome-extension/Help buy links from the user menu.
 */
import { registry } from "@web/core/registry";

const userMenu = registry.category("user_menuitems");

// External Help / buy / account promo items
for (const id of ["support", "account", "documentation", "odoo_account"]) {
    if (userMenu.contains(id)) {
        userMenu.remove(id);
    }
}
