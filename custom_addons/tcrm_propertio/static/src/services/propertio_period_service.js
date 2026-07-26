/** @odoo-module **/

import { registry } from "@web/core/registry";

const propertioPeriodService = {
    start() {
        let period = {
            date_from: null,
            date_to: null,
        };
        const listeners = new Set();

        function notify(source = null) {
            for (const listener of listeners) {
                listener(period, source);
            }
        }

        return {
            getPeriod() {
                return { ...period };
            },
            setPeriod(nextPeriod, source = null) {
                period = {
                    date_from: nextPeriod?.date_from || null,
                    date_to: nextPeriod?.date_to || null,
                };
                notify(source);
            },
            subscribe(listener) {
                listeners.add(listener);
                return () => listeners.delete(listener);
            },
        };
    },
};

registry.category("services").add("propertio_period", propertioPeriodService);
