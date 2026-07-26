/** @odoo-module **/

import { Component } from "@tcrm/owl";
import { buildSparklinePath } from "./sparkline_utils";

export class TcrmStatCard extends Component {
    static template = "tcrm_saas_core.StatCard";
    static props = {
        label: String,
        value: String,
        sub: { type: String, optional: true },
        spark: { type: Array, optional: true },
        deltaText: { type: String, optional: true },
        deltaPositive: { type: Boolean, optional: true },
        iconClass: String,
        accent: { type: String, optional: true },
    };

    get sparkPath() {
        return buildSparklinePath(this.props.spark || [], 120, 36);
    }

    get deltaClass() {
        if (!this.props.deltaText) {
            return "";
        }
        if (this.props.deltaPositive === undefined || this.props.deltaPositive === null) {
            return "text-muted";
        }
        return this.props.deltaPositive ? "o_tcrm_delta--up" : "o_tcrm_delta--down";
    }
}
