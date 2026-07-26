import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@tcrm/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class companyStateDialog extends Component {
    static components = { Dialog };
    static template = "l10n_in_pos.companyStateDialog";
    static props = {
        close: Function,
    };

    setup() {
        this.pos = usePos();
    }

    redirect() {
        window.location = "/tcrm/companies/" + this.pos.company.id;
    }

    onClose() {
        this.props.close();
    }
}
