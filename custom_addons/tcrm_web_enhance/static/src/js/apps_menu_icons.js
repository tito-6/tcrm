/** @odoo-module **/

// Template override: show app icons in the desktop red-star apps dropdown.
import { xml } from "@tcrm/owl";
import { registry } from "@web/core/registry";

// Re-register by patching the NavBar template via assets XML include.
// Actual XML lives in apps_menu_icons.xml loaded as backend asset.
