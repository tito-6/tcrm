/** @odoo-module **/

/**
 * Kill TCRM/Odoo Enterprise upsell dialogs (YouTube promo + upgrade CTA).
 */
import { patch } from "@web/core/utils/patch";
import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { UpgradeBooleanField } from "@web/webclient/settings_form_view/fields/upgrade_boolean_field";

patch(UpgradeBooleanField.prototype, {
    async onChange(newValue) {
        // Never open the Enterprise / YouTube upsell dialog.
        return BooleanField.prototype.onChange.call(this, newValue);
    },
});
