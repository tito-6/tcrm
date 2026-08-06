/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleActionHelper } from "@sale/js/sale_action_helper/sale_action_helper";

patch(SaleActionHelper.prototype, {
    openVideoPreview() {
        // Drop Odoo/YouTube promo video on empty Sales screens.
    },
});
