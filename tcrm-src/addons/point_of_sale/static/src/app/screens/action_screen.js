import { Component, xml } from "@tcrm/owl";
import { registry } from "@web/core/registry";
import { ActionContainer } from "@web/webclient/actions/action_container";

export class ActionScreen extends Component {
    static components = { ActionContainer };
    static props = {
        actionName: String,
    };
    static storeOnOrder = false;
    static template = xml`
        <div class="o_web_client">
            <ActionContainer/>
        </div>
    `;
}

registry.category("pos_pages").add("ActionScreen", {
    name: "ActionScreen",
    component: ActionScreen,
    route: `/pos/ui/${tcrm.pos_config_id}/action/{string:actionName}`,
    params: {},
});
