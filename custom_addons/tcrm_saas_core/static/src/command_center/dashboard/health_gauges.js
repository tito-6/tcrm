/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@tcrm/owl";

const TAU = 2 * Math.PI;
const R = 38;
const C = TAU * R;

export class TcrmHealthGauges extends Component {
    static template = "tcrm_saas_core.HealthGauges";
    static props = {
        vps: { type: Object, optional: true },
        title: String,
    };

    get host() {
        return this.props.vps?.host || "—";
    }

    get gauges() {
        const v = this.props.vps || {};
        const cpu = Number(v.cpu_pct) || 0;
        const ramUsed = Number(v.ram_used_gb) || 0;
        const ramTotal = Number(v.ram_total_gb) || 8;
        const ramPct = ramTotal ? Math.min(100, (ramUsed / ramTotal) * 100) : 0;
        const lat = Number(v.ai_latency_ms) || 0;
        const latPct = Math.min(100, (lat / 500) * 100);
        return [
            {
                key: "cpu",
                label: _t("CPU"),
                display: `${cpu.toFixed(0)}%`,
                dashOffset: C * (1 - cpu / 100),
            },
            {
                key: "ram",
                label: _t("RAM"),
                display: `${ramUsed.toFixed(1)}G`,
                dashOffset: C * (1 - ramPct / 100),
            },
            {
                key: "lat",
                label: _t("DB ms"),
                display: `${lat.toFixed(0)}`,
                dashOffset: C * (1 - latPct / 100),
            },
        ];
    }
}
