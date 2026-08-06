/** @odoo-module **/

/**
 * Prefer the user's Home Action over the first app menu when no URL action is present.
 */
import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

patch(WebClient.prototype, {
    _loadDefaultApp() {
        if (user.homeActionId) {
            return this.actionService.doAction(user.homeActionId, {
                clearBreadcrumbs: true,
                viewType: "list",
            });
        }
        return super._loadDefaultApp(...arguments);
    },
});
