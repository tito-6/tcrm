/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PhoneField } from "@web/views/fields/phone/phone_field";
import { useService } from "@web/core/utils/hooks";

patch(PhoneField.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.callCenter = useService("call_center");
    },
    
    onClickCall(ev) {
        const model = this.props.record.resModel;
        const resId = this.props.record.resId;
        
        if ((model === 'crm.lead' || model === 'res.partner') && resId) {
            ev.preventDefault();
            ev.stopPropagation();

            const state = this.callCenter.state;
            if (state.inCall || state.connecting) {
                this.action.doAction({
                    type: 'ir.actions.client',
                    tag: 'tcrm_call_center.dialer',
                    name: 'Santral (Aktif Arama)',
                    target: 'new',
                });
                return;
            }

            this.action.doAction({
                type: 'ir.actions.client',
                tag: 'tcrm_call_center.dialer',
                name: 'Santral',
                target: 'new',
                context: {
                    lead_id: model === 'crm.lead' ? resId : false,
                    partner_id: model === 'res.partner' ? resId : false,
                    record_name: this.props.record.data.display_name || this.props.record.data.name || "",
                }
            });
        }
    }
});
