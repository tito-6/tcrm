/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { deserializeDate, serializeDate, today } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@tcrm/owl";

/**
 * Period filter: two single-date `DateTimePicker` instances with the same props as
 * `web.CalendarSidePanel.datePickerProps` (no `range` mode — that uses a different
 * selection style than the Events calendar mini-picker).
 */
export class PropertioDashboard extends Component {
    static template = "tcrm_propertio.PropertioDashboard";
    static components = { DateTimePicker };
    static props = { ...standardActionServiceProps };

    REFRESH_INTERVAL_MS = 5 * 60 * 1000;

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.periodService = useService("propertio_period");
        this.state = useState({
            data: null,
            loading: true,
            error: null,
            /** Luxon DateTime | false */
            dateFrom: false,
            dateTo: false,
        });
        this._refreshTimer = null;
        this._debounceApplyTimer = null;
        this._periodSyncToken = Symbol("propertio_dashboard_period");

        const shared = this.periodService.getPeriod();
        if (shared.date_from) {
            this.state.dateFrom = deserializeDate(shared.date_from);
        }
        if (shared.date_to) {
            this.state.dateTo = deserializeDate(shared.date_to);
        }

        onWillStart(async () => {
            await this._loadData();
        });

        onMounted(() => {
            this._refreshTimer = setInterval(() => this._loadData(), this.REFRESH_INTERVAL_MS);
            this._unsubscribePeriod = this.periodService.subscribe(async (period, source) => {
                if (source === this._periodSyncToken) {
                    return;
                }
                this.state.dateFrom = period.date_from ? deserializeDate(period.date_from) : false;
                this.state.dateTo = period.date_to ? deserializeDate(period.date_to) : false;
                await this._loadData();
            });
            this._onKeydown = (ev) => {
                if (ev.ctrlKey && ev.key === "d") {
                    ev.preventDefault();
                    this.action.doAction({ type: "ir.actions.client", tag: "propertio.dashboard" });
                }
            };
            document.addEventListener("keydown", this._onKeydown);
        });

        onWillUnmount(() => {
            if (this._refreshTimer) {
                clearInterval(this._refreshTimer);
            }
            if (this._debounceApplyTimer) {
                clearTimeout(this._debounceApplyTimer);
            }
            if (this._unsubscribePeriod) {
                this._unsubscribePeriod();
            }
            if (this._onKeydown) {
                document.removeEventListener("keydown", this._onKeydown);
            }
        });
    }

    /** Mirrors `web.CalendarSidePanel.datePickerProps` (single date, not range mode). */
    get dateFromPickerProps() {
        return {
            type: "date",
            showWeekNumbers: false,
            maxPrecision: "days",
            daysOfWeekFormat: "narrow",
            value: this.state.dateFrom || false,
            onSelect: (date) => {
                this.state.dateFrom = date;
                this._scheduleApplyPeriod();
            },
        };
    }

    get dateToPickerProps() {
        return {
            type: "date",
            showWeekNumbers: false,
            maxPrecision: "days",
            daysOfWeekFormat: "narrow",
            value: this.state.dateTo || false,
            onSelect: (date) => {
                this.state.dateTo = date;
                this._scheduleApplyPeriod();
            },
        };
    }

    _scheduleApplyPeriod() {
        if (this._debounceApplyTimer) {
            clearTimeout(this._debounceApplyTimer);
        }
        this._debounceApplyTimer = setTimeout(() => this._loadData(), 350);
    }

    /**
     * Build RPC payload. Empty UI → omit both (server: month-start → today).
     * Partial UI → fill missing bound so backend gets a consistent range.
     */
    _payloadForPeriod() {
        let fromDt = this.state.dateFrom;
        let toDt = this.state.dateTo;
        if (!fromDt && !toDt) {
            return {};
        }
        const todayDt = today();
        if (!fromDt && toDt) {
            fromDt = toDt.startOf("month");
        }
        if (fromDt && !toDt) {
            toDt = todayDt;
        }
        if (fromDt > toDt) {
            const tmp = fromDt;
            fromDt = toDt;
            toDt = tmp;
            this.notification.add(
                _t("Date range was adjusted so the start date is not after the end date."),
                { type: "info", sticky: false }
            );
        }
        return {
            date_from: serializeDate(fromDt),
            date_to: serializeDate(toDt),
        };
    }

    async _loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const payload = this._payloadForPeriod();
            this.periodService.setPeriod(payload, this._periodSyncToken);
            const data = await rpc("/propertio/dashboard/data", payload);
            this.state.data = data;
            if (data.period_from) {
                this.state.dateFrom = deserializeDate(data.period_from);
            }
            if (data.period_to) {
                this.state.dateTo = deserializeDate(data.period_to);
            }
        } catch (e) {
            this.state.error = e.message || String(e);
            this.state.data = null;
        } finally {
            this.state.loading = false;
        }
    }

    async applyPeriodFilter() {
        await this._loadData();
    }

    async resetPeriodFilter() {
        this.state.dateFrom = false;
        this.state.dateTo = false;
        this.periodService.setPeriod({}, this._periodSyncToken);
        await this._loadData();
    }

    async setPeriodThisMonth() {
        const t = today();
        this.state.dateFrom = t.startOf("month");
        this.state.dateTo = t;
        await this._loadData();
    }

    async setPeriodLastMonth() {
        const t = today();
        const startThis = t.startOf("month");
        const endPrev = startThis.minus({ days: 1 });
        this.state.dateFrom = endPrev.startOf("month");
        this.state.dateTo = endPrev;
        await this._loadData();
    }

    async setThisYearToDate() {
        const t = today();
        this.state.dateFrom = t.startOf("year");
        this.state.dateTo = t;
        await this._loadData();
    }

    get role() {
        return this.state.data ? this.state.data.role : "sales";
    }

    _periodDomain(fieldName) {
        const payload = this._payloadForPeriod();
        const domain = [];
        if (payload.date_from) {
            domain.push([fieldName, ">=", payload.date_from]);
        }
        if (payload.date_to) {
            domain.push([fieldName, "<=", payload.date_to]);
        }
        return domain;
    }

    openAction(model, resId, view = "form") {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: resId,
            views: [[false, view]],
            target: "current",
        });
    }

    openPaymentForm(partnerId, saleId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "propertio.payment",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_partner_id: partnerId || undefined,
                default_sale_id: saleId || undefined,
                default_payment_date: serializeDate(today()),
            },
        });
    }

    openRedAlerts() {
        this.action.doAction("tcrm_propertio.action_report_kirmizi_alarm", {
            domain: [["overdue_days", ">=", 15], ["is_paid", "=", false], ...this._periodDomain("date_due")],
        });
    }

    openPayments() {
        this.action.doAction("tcrm_propertio.action_propertio_payment", {
            domain: this._periodDomain("payment_date"),
        });
    }

    openSales() {
        this.action.doAction("tcrm_propertio.action_propertio_sale", {
            domain: this._periodDomain("date_sale"),
        });
    }

    openUnits() {
        this.action.doAction("tcrm_propertio.action_propertio_unit", {
            domain: [["state", "=", "available"]],
        });
    }

    openNewSale() {
        this.action.doAction("tcrm_propertio.action_propertio_sale_wizard");
    }

    openReportsCenter() {
        this.action.doAction("tcrm_propertio.action_propertio_reports_center_hub");
    }

    formatNumber(n) {
        if (n === undefined || n === null) return "0";
        return Number(n).toLocaleString();
    }

    formatMoney(amount, currency = "") {
        if (amount === undefined || amount === null) return "0 " + currency;
        return (
            Number(amount).toLocaleString(undefined, {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }) +
            " " +
            (currency || "")
        );
    }
}

registry.category("actions").add("propertio.dashboard", PropertioDashboard);
