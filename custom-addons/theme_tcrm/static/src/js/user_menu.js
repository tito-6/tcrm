/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, xml } from "@odoo/owl";

// Debug
console.log("[TCRM] Loading User Menu Customizations...");

// 1. Remove Odoo Branding Items
const userMenuRegistry = registry.category("user_menuitems");

// Try generic keys used in past versions as well
const keysToRemove = ["documentation", "support", "odoo_account", "about", "shortcut"];

keysToRemove.forEach(key => {
    if (userMenuRegistry.contains(key)) {
        try {
            userMenuRegistry.remove(key);
            console.log(`[TCRM] Removed user menu item: ${key}`);
        } catch (e) {
            console.error(`[TCRM] Failed to remove ${key}:`, e);
        }
    }
});

// 2. Custom About Dialog Component
class TCRMAboutDialog extends Component {
    setup() {
        this.title = _t("About TCRM");
    }
}
TCRMAboutDialog.template = "theme_tcrm.UserMenu.AboutDialog";
TCRMAboutDialog.components = { Dialog };

// 3. Add Custom About Item
function tcrmAboutItem(env) {
    return {
        type: "item",
        id: "tcrm_about",
        description: _t("About"),
        callback: () => {
            env.services.dialog.add(TCRMAboutDialog, {
                title: _t("About TCRM"),
            });
        },
        sequence: 100,
    };
}

userMenuRegistry.add("tcrm_about", tcrmAboutItem);
console.log("[TCRM] Added custom About item.");
