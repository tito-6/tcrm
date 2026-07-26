/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TcrmCommandCenter } from "./command_center";

registry
    .category("actions")
    .add("tcrm_master.command_center", TcrmCommandCenter, { force: true });
registry
    .category("actions")
    .add("tcrm_master.advanced_analytics", TcrmCommandCenter, { force: true });
