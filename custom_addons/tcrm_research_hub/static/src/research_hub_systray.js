/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@tcrm/owl";

export class ResearchHubSystray extends Component {
    static template = "tcrm_research_hub.Systray";
    static props = {};

    setup() {
        this.action = useService("action");
    }

    openResearchHub() {
        this.action.doAction("tcrm_research_hub.action_tcrm_research_hub");
    }
}

registry.category("systray").add(
    "tcrm_research_hub.systray",
    { Component: ResearchHubSystray },
    { sequence: 25 }
);
