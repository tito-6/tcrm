/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Layout } from "@web/search/layout";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@tcrm/owl";

import { TcrmStatCard } from "./dashboard/stat_card";
import { TcrmHealthGauges } from "./dashboard/health_gauges";
import { TcrmTenantMap } from "./dashboard/tenant_map";
import { buildSparklinePath } from "./dashboard/sparkline_utils";

export class TcrmCommandCenter extends Component {
    static template = "tcrm_saas_core.CommandCenter";
    static components = { Layout, TcrmStatCard, TcrmHealthGauges, TcrmTenantMap };
    static props = { ...standardActionServiceProps };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this._onResize = null;
        this._paletteSearchTimer = null;
        const forcedAnalytics = this.props?.action?.tag === "tcrm_master.advanced_analytics";
        const initialScreen = this.props?.action?.params?.screen || (forcedAnalytics ? "analytics" : "dashboard");
        this.state = useState({
            screen: initialScreen,
            loading: true,
            sidebarOpen: true,
            isMobile: false,

            // Dashboard
            dashboard: null,
            vpsMetrics: null,
            paletteSearchOpen: false,
            paletteSearchQuery: "",
            paletteSearchResults: null,
            paletteSearchLoading: false,

            // Tenant Hub
            tenants: [],
            tenantSearch: "",
            tenantFilterState: "",

            // Tenant 360
            tenantDetail: null,
            tenantDetailTab: "activity",
            tenantEditLat: "",
            tenantEditLon: "",
            tenantEditLink: "",
            tenantAdminResetPassword: "",
            tenantAdminResetLogin: "",

            // Users
            users: [],
            userSearch: "",
            currentUserId: this._resolveCurrentUserId(),

            // Access
            accessData: null,
            accessAppSearch: "",
            accessCredModal: null,

            // Financials
            financials: null,

            // Technical
            technical: null,

            // DB Console
            sqlQuery: "SELECT id, name, state FROM tcrm_tenant ORDER BY id DESC LIMIT 50;",
            sqlResult: null,
            sqlLoading: false,

            // Analytics
            analytics: null,
            analyticsFormat: "html",
            analyticsEditMode: true,
            analyticsBotOpen: false,
            analyticsMetrics: {
                tenant_id: true,
                growth_rate: true,
                churn_risk: true,
                security_status: true,
                revenue: false,
                mrr: false,
            },

            // Create/Edit Modals
            showCreateTenant: false,
            createTenantBusy: false,
            editTenant: null,
            newTenant: {
                name: "",
                client_name: "",
                support_email: "",
                support_phone: "",
                sector_id: false,
                domain: "",
                db_name: "",
                admin_login: "admin",
                admin_password: "",
                _domainTouched: false,
                _dbTouched: false,
            },

            // Reference data
            packages: [],
            sectors: [],
            appsCatalog: [],
            appsCatalogTotal: 0,
            appsCatalogSearch: "",
            selectedPackageForApps: null,
            packageModuleDraftIds: [],
            grantModuleId: false,

            // TCRM AI (tenant entitlement matrix — safe fields only)
            aiTenants: [],
            aiBusyId: null,

            /** Executive Portfolio (master suite) */
            portfolioRange: "30d",
            portfolioCustomStart: "",
            portfolioCustomEnd: "",
            portfolioGhostMode: false,
            portfolioGhostSearch: "",
            portfolioAiInput: "",
            portfolioAiMessages: [],

            // God-Mode
            employees: [],
            employeeSearch: "",
            employeeTenantFilter: null,
            aiHealth: [],
            resetPasswordModal: null,
            changeRoleModal: null,
            tenantRoles: [
                { key: "viewer", label: "Tenant Viewer", help: "Read-only access to tenant CRM data." },
                { key: "sales", label: "Tenant Sales", help: "CRM and sales pipeline access." },
                { key: "operations", label: "Tenant Operations", help: "Inventory, units, and property operations." },
                { key: "finance", label: "Tenant Finance", help: "Collections, invoices, and financial reports." },
                { key: "manager", label: "Tenant Manager", help: "Team lead: sales + ops oversight without full admin." },
                { key: "admin", label: "Tenant Admin", help: "Full tenant management access." },
            ],
        });

        useHotkey("control+k", () => {
            this.state.paletteSearchOpen = !this.state.paletteSearchOpen;
            if (!this.state.paletteSearchOpen) {
                this.state.paletteSearchQuery = "";
                this.state.paletteSearchResults = null;
            }
        });

        onWillStart(async () => {
            await this._loadRefData();
            await this._loadTenantRoles();
            await this._loadInitialScreen();
        });

        onMounted(() => {
            this._markHost();
            this.state.isMobile = window.innerWidth < 992;
            this.state.sidebarOpen = !this.state.isMobile;
            this._onResize = () => {
                const mobile = window.innerWidth < 992;
                const wasMobile = this.state.isMobile;
                this.state.isMobile = mobile;
                // Only auto-toggle sidebar when crossing the breakpoint.
                if (mobile !== wasMobile) {
                    this.state.sidebarOpen = !mobile;
                }
                this._markHost();
            };
            window.addEventListener("resize", this._onResize);
        });

        onWillUnmount(() => {
            if (this._onResize) {
                window.removeEventListener("resize", this._onResize);
            }
            this._unmarkHost();
        });
    }

    _markHost() {
        const root = document.querySelector(".o_tcrm_command_center");
        if (!root) {
            return;
        }
        const action = root.closest(".o_action");
        const content = root.closest(".o_content");
        if (action) {
            action.classList.add("o_tcrm_cc_action", "o_tcrm_cc_host");
        }
        if (content) {
            content.classList.add("o_tcrm_cc_host");
        }
    }

    _unmarkHost() {
        document.querySelectorAll(".o_tcrm_cc_host").forEach((el) => {
            el.classList.remove("o_tcrm_cc_host");
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    async _loadInitialScreen() {
        const screen = this.state.screen;
        if (screen === "dashboard" || screen === "portfolio") {
            await this._loadDashboard();
            if (screen === "portfolio") {
                this._portfolioSeedChatIfNeeded();
            }
        } else if (screen === "tenants") {
            await this._loadTenants();
        } else if (screen === "users") {
            await this._loadUsers();
        } else if (screen === "employees") {
            if (!this.state.tenants.length) await this._loadTenants();
            await this._loadEmployees();
        } else if (screen === "access") {
            await this._loadAccess();
        } else if (screen === "financials") {
            await this._loadFinancials();
        } else if (screen === "technical") {
            await this._loadTechnical();
        } else if (screen === "analytics") {
            await this._loadAnalytics();
        }
        this.state.loading = false;
    }

    // Theme is now handled by the Odoo web client; no custom toggle needed.

    // ── Navigation ────────────────────────────────────────────────

    get screens() {
        return [
            { id: "dashboard", label: _t("Dashboard"), iconClass: "fa fa-tachometer" },
            { id: "portfolio", label: _t("Executive Portfolio"), iconClass: "fa fa-pie-chart" },
            { id: "tenants", label: _t("Tenants"), iconClass: "fa fa-building" },
            { id: "users", label: _t("User Management"), iconClass: "fa fa-users" },
            { id: "employees", label: _t("Global Employees"), iconClass: "fa fa-users" },
            { id: "access", label: _t("Access Management"), iconClass: "fa fa-shield" },
            { id: "apps", label: _t("App Catalog"), iconClass: "fa fa-shopping-cart" },
            { id: "tcrm_ai", label: _t("TCRM AI"), iconClass: "fa fa-bolt" },
            { id: "financials", label: _t("Financials"), iconClass: "fa fa-credit-card" },
            { id: "technical", label: _t("Tech Stack"), iconClass: "fa fa-microchip" },
            { id: "db_console", label: _t("DB Management"), iconClass: "fa fa-database" },
            { id: "analytics", label: _t("Analytics"), iconClass: "fa fa-line-chart" },
        ];
    }

    async navigateTo(screen) {
        this.state.screen = screen;
        if (this.state.isMobile) {
            this.state.sidebarOpen = false;
        }
        this.state.loading = true;
        try {
            if (screen === "dashboard" || screen === "portfolio") {
                await this._loadDashboard();
                if (screen === "portfolio") {
                    this._portfolioSeedChatIfNeeded();
                }
            } else if (screen === "tenants") await this._loadTenants();
            else if (screen === "users") await this._loadUsers();
            else if (screen === "employees") {
                if (!this.state.tenants.length) await this._loadTenants();
                await this._loadEmployees();
            }             else if (screen === "access") await this._loadAccess();
            else if (screen === "apps") await this._loadAppsCatalog();
            else if (screen === "tcrm_ai") await this._loadAiTenants();
            else if (screen === "financials") await this._loadFinancials();
            else if (screen === "technical") await this._loadTechnical();
            else if (screen === "analytics") await this._loadAnalytics();
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
        this.state.loading = false;
    }

    _resolveCurrentUserId() {
        try {
            const fromContext = this.props?.action?.context?.uid;
            if (fromContext) {
                return Number(fromContext);
            }
            const sessionInfo = window.odoo?.session_info;
            if (sessionInfo?.uid) {
                return Number(sessionInfo.uid);
            }
        } catch (_) {
            // ignore
        }
        return 0;
    }

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
    }

    onTenantSearchInput(ev) {
        this.state.tenantSearch = ev.target.value;
    }

    onTenantSearchKeydown(ev) {
        if (ev.key === "Enter") {
            this.searchTenants();
        }
    }

    onUserSearchInput(ev) {
        this.state.userSearch = ev.target.value;
    }

    onUserSearchKeydown(ev) {
        if (ev.key === "Enter") {
            this.searchUsers();
        }
    }

    // ── Reference Data ────────────────────────────────────────────

    async _loadRefData() {
        try {
            const [packages, sectors] = await Promise.all([
                rpc("/tcrm_master/packages"),
                rpc("/tcrm_master/sectors"),
            ]);
            this.state.packages = packages || [];
            this.state.sectors = sectors || [];
        } catch (_) { /* non-critical */ }
    }

    // ── Dashboard ─────────────────────────────────────────────────

    async _loadDashboard() {
        try {
            const [dash, vps] = await Promise.all([
                rpc("/tcrm_master/dashboard"),
                rpc("/tcrm_master/vps_metrics").catch(() => null),
            ]);
            this.state.dashboard = {
                ...dash,
                sparklines: dash?.sparklines || { gdv: [], health: [], mrr: [], users: [] },
                deltas: dash?.deltas || {},
                map_markers: dash?.map_markers || [],
            };
            this.state.vpsMetrics = vps;
        } catch (e) {
            this.state.dashboard = null;
            this.state.vpsMetrics = null;
        }
        this.state.loading = false;
    }

    _portfolioSeedChatIfNeeded() {
        if (this.state.portfolioAiMessages.length) {
            return;
        }
        this.state.portfolioAiMessages = [
            {
                role: "assistant",
                text: _t(
                    "Global GDV is tracking near forecast. Subscription renewals look stable; watch overdue invoices for concentration risk. Shall I summarize tenants with past-due balances?"
                ),
            },
            {
                role: "user",
                text: _t(
                    "Yes — highlight tenants with multiple overdue invoices and suggest next actions in Tenant 360."
                ),
            },
        ];
    }

    setPortfolioRange(range) {
        this.state.portfolioRange = range;
        if (range !== "custom") {
            this.state.portfolioCustomStart = "";
            this.state.portfolioCustomEnd = "";
            this._reloadPortfolio();
        }
        // For 'custom': user picks dates first, reload triggers on both dates filled
    }

    onPortfolioCustomStart(ev) {
        this.state.portfolioCustomStart = ev.target.value;
        if (this.state.portfolioCustomStart && this.state.portfolioCustomEnd) {
            this._reloadPortfolio();
        }
    }

    onPortfolioCustomEnd(ev) {
        this.state.portfolioCustomEnd = ev.target.value;
        if (this.state.portfolioCustomStart && this.state.portfolioCustomEnd) {
            this._reloadPortfolio();
        }
    }

    async _reloadPortfolio() {
        this.state.loading = true;
        await this._loadDashboard();
        this.state.loading = false;
    }

    togglePortfolioGhostMode() {
        this.state.portfolioGhostMode = !this.state.portfolioGhostMode;
        if (this.state.portfolioGhostMode && !this.state.tenants.length) {
            this._loadTenants();
        }
    }

    onPortfolioGhostSearch(ev) {
        this.state.portfolioGhostSearch = ev.target.value;
    }

    get filteredGhostTenants() {
        const q = (this.state.portfolioGhostSearch || "").trim().toLowerCase();
        const tenants = this.state.tenants || [];
        if (!q) return tenants.slice(0, 20);
        return tenants.filter(t =>
            (t.name || "").toLowerCase().includes(q) ||
            (t.domain || "").toLowerCase().includes(q)
        ).slice(0, 20);
    }

    openpaletteSearchFromPortfolio() {
        this.state.paletteSearchOpen = true;
    }

    openGlobalCommandFab() {
        this.state.paletteSearchOpen = true;
    }

    onPortfolioAiInput(ev) {
        this.state.portfolioAiInput = ev.target.value;
    }

    submitPortfolioAi(ev) {
        if (ev && ev.preventDefault) {
            ev.preventDefault();
        }
        const text = (this.state.portfolioAiInput || "").trim();
        if (!text) {
            return;
        }
        this.state.portfolioAiMessages = [
            ...this.state.portfolioAiMessages,
            { role: "user", text },
            {
                role: "assistant",
                text: _t(
                    "Noted. For full multi-step analysis and tooling, open TCRM AI from the app menu — this panel mirrors executive highlights only."
                ),
            },
        ];
        this.state.portfolioAiInput = "";
    }

    downloadPortfolioActivityLog() {
        const acts = this.state.dashboard?.activities || [];
        const esc = (s) => `"${String(s ?? "").replace(/"/g, '""')}"`;
        const lines = [
            ["event", "tenant", "status", "timestamp"].join(","),
            ...acts.map((a) =>
                [esc(a.event), esc(a.tenant_name), esc(a.status), esc(a.timestamp)].join(",")
            ),
        ];
        const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "tcrm_portfolio_activity.csv";
        a.click();
        URL.revokeObjectURL(url);
        this.notification.add(_t("Activity log downloaded."), { type: "success" });
    }

    portfolioSparkPath(key) {
        const series = this.state.dashboard?.sparklines?.[key] || [];
        return buildSparklinePath(series, 120, 32);
    }

    portfolioMrrBarHeights() {
        const s = this.state.dashboard?.sparklines?.mrr || [];
        const slice = s.slice(-5);
        if (!slice.length) {
            return [28, 44, 38, 62, 55];
        }
        const min = Math.min(...slice);
        const max = Math.max(...slice);
        const span = Math.max(max - min, 1e-9);
        return slice.map((v) => Math.round(22 + ((v - min) / span) * 78));
    }

    portfolioActivityIconClass(a) {
        if (!a) {
            return "fa fa-bolt text-muted";
        }
        if (a.type === "invoice") {
            if (a.status === "overdue") {
                return "fa fa-money text-danger";
            }
            if (a.status === "paid") {
                return "fa fa-check-circle text-success";
            }
            return "fa fa-file-text-o text-primary";
        }
        if (a.type === "subscription") {
            if (a.status === "past_due") {
                return "fa fa-exclamation-triangle text-danger";
            }
            return "fa fa-file-text-o text-primary";
        }
        return "fa fa-bolt text-muted";
    }

    tenantInitials(name) {
        if (!name) {
            return "?";
        }
        const parts = String(name)
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2);
        const s = parts.map((p) => p[0]).join("");
        return s.toUpperCase().slice(0, 3) || "?";
    }

    fmtDeltaShort(pct) {
        if (pct == null || Number.isNaN(Number(pct))) {
            return "";
        }
        const n = Number(pct);
        return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
    }

    fmtAiLatency() {
        const ms = this.state.vpsMetrics?.ai_latency_ms;
        if (ms == null || Number.isNaN(Number(ms))) {
            return "—";
        }
        return `${Number(ms).toFixed(1)} ms`;
    }

    portfolioHealthLowCount() {
        const d = this.state.dashboard;
        if (!d) {
            return 0;
        }
        return Number(d.past_due_subscriptions_count || 0) + Number(d.at_risk_count || 0);
    }

    closepaletteSearch() {
        this.state.paletteSearchOpen = false;
        this.state.paletteSearchQuery = "";
        this.state.paletteSearchResults = null;
    }

    onpaletteSearchInput(ev) {
        this.state.paletteSearchQuery = ev.target.value;
        if ((this.state.paletteSearchQuery || "").trim().length < 2) {
            this.state.paletteSearchResults = null;
            return;
        }
        if (this._paletteSearchTimer) {
            clearTimeout(this._paletteSearchTimer);
        }
        this._paletteSearchTimer = setTimeout(() => this._runpaletteSearch(), 300);
    }

    onpaletteSearchKeydown(ev) {
        if (ev.key === "Escape") {
            this.closepaletteSearch();
        }
    }

    async _runpaletteSearch() {
        const q = (this.state.paletteSearchQuery || "").trim();
        if (q.length < 2) {
            this.state.paletteSearchResults = null;
            return;
        }
        this.state.paletteSearchLoading = true;
        try {
            this.state.paletteSearchResults = await rpc("/tcrm_master/search/global", { query: q });
        } catch (e) {
            this.state.paletteSearchResults = { tenants: [], invoices: [], users: [] };
        }
        this.state.paletteSearchLoading = false;
    }

    async selectPaletteTenant(id) {
        if (!id) {
            return;
        }
        this.closepaletteSearch();
        await this.openTenantDetail(id);
    }

    async selectPaletteInvoice(row) {
        if (!row?.tenant_id) {
            return;
        }
        this.closepaletteSearch();
        await this.openTenantDetail(row.tenant_id);
    }

    async selectPaletteUser(uid) {
        if (!uid) {
            return;
        }
        this.closepaletteSearch();
        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: _t("User"),
                res_model: "res.users",
                res_id: uid,
                views: [[false, "form"]],
                target: "current",
            });
        } catch (e) {
            this.notification.add(e?.message || String(e), { type: "danger" });
        }
    }

    deltaLine(pct) {
        if (pct == null || Number.isNaN(Number(pct))) {
            return "";
        }
        const n = Number(pct);
        const sign = n > 0 ? "+" : "";
        return `${sign}${n}% ${_t("vs prior month")}`;
    }

    isDeltaPositive(pct) {
        if (pct == null || Number.isNaN(Number(pct))) {
            return null;
        }
        return Number(pct) >= 0;
    }

    deltaPillClass(pct) {
        const p = this.isDeltaPositive(pct);
        if (p === true) {
            return "bg-success-subtle text-success";
        }
        if (p === false) {
            return "bg-danger-subtle text-danger";
        }
        return "bg-secondary-subtle text-muted";
    }

    snapshotBarWidth(slug) {
        const d = this.state.dashboard;
        if (!d) {
            return 8;
        }
        const rev = Number(d.total_revenue_30d) || 0;
        const open = Number(d.open_invoices_total) || 0;
        const mrr = Number(d.mrr) || 0;
        const scale = Math.max(rev, open, mrr * 3, 1);
        switch (slug) {
            case "col30":
                return Math.min(100, Math.round((rev / scale) * 100));
            case "open":
                return Math.min(100, Math.round((open / scale) * 100));
            case "trial": {
                const n = Number(d.trial_subscriptions_count) || 0;
                return Math.min(100, n * 20);
            }
            case "past": {
                const n = Number(d.past_due_subscriptions_count) || 0;
                return Math.min(100, n * 25);
            }
            case "sus": {
                const n = Number(d.suspended_subscriptions_count) || 0;
                return Math.min(100, n * 25);
            }
            default:
                return 12;
        }
    }

    packageDonutSegments(mix) {
        const m = mix || [];
        if (!m.length) {
            return [];
        }
        const total = m.reduce((s, x) => s + (x.count || 0), 0) || 1;
        const colors = ["#9a3412", "#ca8a04", "#1e40af", "#5b21b6", "#0f766e", "#be123c", "#334155"];
        let a0 = -Math.PI / 2;
        const cx = 70;
        const cy = 70;
        const ro = 48;
        const ri = 30;
        return m.map((pkg, i) => {
            const sweep = ((pkg.count || 0) / total) * Math.PI * 2;
            const a1 = a0 + sweep;
            const xo1 = cx + ro * Math.cos(a0);
            const yo1 = cy + ro * Math.sin(a0);
            const xo2 = cx + ro * Math.cos(a1);
            const yo2 = cy + ro * Math.sin(a1);
            const xi1 = cx + ri * Math.cos(a1);
            const yi1 = cy + ri * Math.sin(a1);
            const xi2 = cx + ri * Math.cos(a0);
            const yi2 = cy + ri * Math.sin(a0);
            const large = sweep > Math.PI ? 1 : 0;
            const d = [
                `M ${xo1} ${yo1}`,
                `A ${ro} ${ro} 0 ${large} 1 ${xo2} ${yo2}`,
                `L ${xi1} ${yi1}`,
                `A ${ri} ${ri} 0 ${large} 0 ${xi2} ${yi2}`,
                "Z",
            ].join(" ");
            const seg = {
                d,
                color: colors[i % colors.length],
                name: pkg.name,
                count: pkg.count,
            };
            a0 = a1;
            return seg;
        });
    }

    onTenantWorkspace(tenantId) {
        if (!tenantId) {
            this.notification.add(_t("No tenant linked to this row."), { type: "warning" });
            return;
        }
        this.notification.add(_t("Opening Tenant 360 — manage session access from there."), {
            type: "info",
        });
        this.openTenantDetail(tenantId);
    }

    get strSearchCommand() {
        return _t("Command Palette");
    }
    get strSearchPlaceholder() {
        return _t("Search tenant, invoice, or user…");
    }
    get strSearchNoMatches() {
        return _t("No matches.");
    }
    get strSearchTypeTwo() {
        return _t("Type at least 2 characters.");
    }
    get strGrpTenants() {
        return _t("Tenants");
    }
    get strGrpInvoices() {
        return _t("Invoices");
    }
    get strGrpUsers() {
        return _t("Users");
    }

    get lblKpiGdv() {
        return _t("Gross Distribution Value");
    }
    get lblKpiHealth() {
        return _t("Tenant Health");
    }
    get lblKpiMrr() {
        return _t("Monthly Recurring Revenue");
    }
    get lblKpiUsers() {
        return _t("Total Users");
    }
    get kpiSubHealth() {
        const d = this.state.dashboard;
        if (!d) {
            return "";
        }
        let s = `${d.active_tenants} / ${d.total_tenants} ${_t("active")}`;
        if (d.at_risk_count) {
            s += ` · ${d.at_risk_count} ${_t("draft")}`;
        }
        return s;
    }
    get kpiSubMrr() {
        const d = this.state.dashboard;
        if (!d) {
            return "";
        }
        return `${d.active_subscriptions_count || 0} ${_t("paying subs")}`;
    }
    get lblUtilityBar() {
        return _t("Utility bar");
    }
    get lblMetricSnapshot() {
        return _t("Operations snapshot");
    }
    get lblMapTenants() {
        return _t("Tenant footprint (Turkey & Middle East)");
    }
    get vpsPanelTitle() {
        const h = this.state.vpsMetrics?.host || "45.9.191.119";
        return `${_t("VPS performance")} (${h})`;
    }
    get lblLiveActivity() {
        return _t("Live activity");
    }
    get lblBillingAlerts() {
        return _t("Billing alerts");
    }
    get lblAtRiskAr() {
        return _t("At-risk AR");
    }
    get lblRecentTenants() {
        return _t("Recent tenants");
    }
    get lblPlansPipeline() {
        return _t("Plans (active pipeline)");
    }
    get lblDonutMix() {
        return _t("Revenue forecast mix");
    }
    get lblOpenInvoices() {
        return _t("Open invoices");
    }
    get lblTrials() {
        return _t("Trials");
    }
    get lblPastDueSubs() {
        return _t("Past-due subs");
    }
    get lblSuspended() {
        return _t("Suspended");
    }
    get lblCollected30() {
        return _t("Collected (30 days)");
    }
    get strUtilTenants() {
        return _t("Tenants");
    }
    get strUtilFinancials() {
        return _t("Financials");
    }
    get strUtilAnalytics() {
        return _t("Analytics");
    }
    get strUtilUsers() {
        return _t("Users");
    }
    get strUtilAccess() {
        return _t("Access");
    }
    get strUtilNewTenant() {
        return _t("New tenant");
    }
    get strUtilCommand() {
        return _t("Command");
    }
    get strActiveSubs() {
        return _t("Active subs");
    }

    get strPortfolioPageTitle() {
        return _t("Executive Portfolio");
    }
    get strMasterSuiteMark() {
        return _t("TCRM Master Suite");
    }
    get strExecutiveSuiteTitle() {
        return _t("Executive Suite");
    }
    get strCommandCenterTag() {
        return _t("Command Center");
    }
    get strPortfolioSearchPh() {
        return _t("Search portfolio…");
    }
    get strNavOverview() {
        return _t("Overview");
    }
    get strNavAssets() {
        return _t("Assets");
    }
    get strNavCapital() {
        return _t("Capital");
    }
    get strRange30() {
        return _t("Last 30 Days");
    }
    get strRangeQuarter() {
        return _t("Quarterly");
    }
    get strRangeCustom() {
        return _t("Custom Range");
    }
    get strGhostMode() {
        return _t("Ghost Mode");
    }
    get strAdvancedFilters() {
        return _t("Advanced Filters");
    }
    get strTotalPortfolioGdv() {
        return _t("Total Portfolio GDV");
    }
    get strActiveTenantHealth() {
        return _t("Active Tenant Health");
    }
    get strLowSuffix() {
        return _t("Low");
    }
    get strStableHealth() {
        return _t("Stable");
    }
    get strAiEngineLoad() {
        return _t("AI Engine Load");
    }
    get strAiLatencySub() {
        return _t("DB round-trip latency (proxy for AI gateway load).");
    }
    get strLiveActivityStream() {
        return _t("Live Activity Stream");
    }
    get strDownloadLog() {
        return _t("Download Log");
    }
    get strSystemRedAlerts() {
        return _t("System Red Alerts");
    }
    get strIntervene() {
        return _t("Intervene");
    }
    get strTcrmAiInsight() {
        return _t("TCRM AI Insight");
    }
    get strAskTcrmAi() {
        return _t("Ask TCRM AI…");
    }
    get strGlobalCommand() {
        return _t("Global Command");
    }
    get strPortfolioNoData() {
        return _t("Portfolio data unavailable. Check your connection and try again.");
    }
    get strThTenantEntity() {
        return _t("Tenant / Entity");
    }

    onMapTenantClick(tenantId) {
        if (tenantId) {
            this.openTenantDetail(tenantId);
        }
    }

    get tenantDetailMapMarkers() {
        const t = this.state.tenantDetail;
        if (!t?.id) {
            return [];
        }
        const lat = Number(t.latitude) || Number(this.state.tenantEditLat) || 0;
        const lon = Number(t.longitude) || Number(this.state.tenantEditLon) || 0;
        if (!lat && !lon) {
            return [];
        }
        return [{
            id: t.id,
            name: t.name,
            lat,
            lon,
            has_real_coords: Boolean(t.latitude && t.longitude),
            is_frozen: Boolean(t.is_frozen),
        }];
    }

    async onMapMarkerMoved({ id, lat, lon }) {
        try {
            await rpc("/tcrm_master/tenant/update_pin", { tenant_id: id, latitude: lat, longitude: lon });
            if (this.state.dashboard?.map_markers) {
                const m = this.state.dashboard.map_markers.find((mk) => mk.id === id);
                if (m) {
                    m.lat = lat;
                    m.lon = lon;
                    m.has_real_coords = true;
                }
            }
            if (this.state.tenantDetail?.id === id) {
                this.state.tenantDetail.latitude = lat;
                this.state.tenantDetail.longitude = lon;
                this.state.tenantEditLat = String(lat);
                this.state.tenantEditLon = String(lon);
            }
            this.notification.add(_t("Pin position saved."), { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    get strThEvent() {
        return _t("Event");
    }
    get strThTenant() {
        return _t("Tenant");
    }
    get strThStatus() {
        return _t("Status");
    }
    get strThTime() {
        return _t("Time");
    }
    get strGhostTitle() {
        return _t("Tenant workspace");
    }
    get strNoActivity() {
        return _t("No recent activity");
    }
    get strOverdue() {
        return _t("overdue");
    }
    get strInvestigate() {
        return _t("Investigate");
    }
    get strAllClear() {
        return _t("All clear — no overdue invoices in focus");
    }
    get strNoTenantsYet() {
        return _t("No tenants yet");
    }
    get strNoPlans() {
        return _t("No active or trial subscriptions");
    }

    // ── Tenants ───────────────────────────────────────────────────

    async _loadTenants() {
        const data = await rpc("/tcrm_master/tenants", {
            search: this.state.tenantSearch,
            filter_state: this.state.tenantFilterState,
        });
        this.state.tenants = data || [];
    }

    async searchTenants() {
        this.state.loading = true;
        await this._loadTenants();
        this.state.loading = false;
    }

    async filterTenantsByState(state) {
        this.state.tenantFilterState = this.state.tenantFilterState === state ? "" : state;
        await this.searchTenants();
    }

    async openTenantDetail(tenantId) {
        const resolvedTenantId = this._tenantIdForOpen({ tenant_record_id: tenantId, tenant_id: tenantId });
        if (!resolvedTenantId) {
            this.notification.add(_t("Tenant id is not valid"), { type: "warning" });
            return;
        }
        this.state.loading = true;
        this.state.screen = "tenant_detail";
        this.state.tenantDetailTab = "activity";
        try {
            this.state.tenantDetail = await rpc("/tcrm_master/tenant/detail", { tenant_id: resolvedTenantId });
            if (this.state.tenantDetail) {
                this.state.tenantEditLat = this.state.tenantDetail.latitude ? String(this.state.tenantDetail.latitude) : "";
                this.state.tenantEditLon = this.state.tenantDetail.longitude ? String(this.state.tenantDetail.longitude) : "";
                this.state.tenantEditLink = this.state.tenantDetail.google_maps_link || "";
                this.state.tenantAdminResetLogin = this.state.tenantDetail.provision?.admin_login || "admin";
                this.state.tenantAdminResetPassword = "";
            }
        } catch (e) {
            this.notification.add(e.message || "Failed to load tenant", { type: "danger" });
        }
        this.state.loading = false;
    }

    async setTenantDetailTab(tab) {
        this.state.tenantDetailTab = tab;
        if (tab === "modules" && !this.state.appsCatalog.length) {
            try {
                await this._loadAppsCatalog();
            } catch (_) { /* non-critical */ }
        }
    }

    // Tenant 360 Location
    onTenantLocInput(field, ev) {
        this.state[field] = ev.target.value;
    }

    async saveTenantLocation() {
        const id = this.state.tenantDetail?.id;
        if (!id) return;
        const link = (this.state.tenantEditLink || "").trim();
        const lat = parseFloat(this.state.tenantEditLat) || 0;
        const lon = parseFloat(this.state.tenantEditLon) || 0;
        if (!lat && !lon && !link) {
            this.notification.add(_t("Enter coordinates or a Google Maps link"), { type: "warning" });
            return;
        }
        try {
            this.state.loading = true;
            const result = await rpc("/tcrm_master/tenant/update_pin", {
                tenant_id: id,
                latitude: lat,
                longitude: lon,
                google_maps_link: link,
            });
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
            } else {
                this.state.tenantDetail.latitude = result.lat;
                this.state.tenantDetail.longitude = result.lon;
                if (link) this.state.tenantDetail.google_maps_link = link;
                this.state.tenantEditLat = String(result.lat || "");
                this.state.tenantEditLon = String(result.lon || "");
                this.notification.add(_t("Location saved"), { type: "success" });
            }
        } catch (e) {
            this.notification.add(e.message || _t("Failed to save location"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // Tenant CRUD — one-screen create + provision
    _slugTenantToken(value) {
        return String(value || "")
            .toLowerCase()
            .normalize("NFKD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9]+/g, "_")
            .replace(/^_+|_+$/g, "")
            .replace(/_+/g, "_")
            .slice(0, 40);
    }

    openCreateTenant() {
        this.state.showCreateTenant = true;
        this.state.createTenantBusy = false;
        this.state.newTenant = {
            name: "",
            client_name: "",
            support_email: "",
            support_phone: "",
            sector_id: false,
            domain: "",
            db_name: "",
            admin_login: "admin",
            admin_password: "",
            _domainTouched: false,
            _dbTouched: false,
        };
    }

    closeCreateTenant() {
        if (this.state.createTenantBusy) {
            return;
        }
        this.state.showCreateTenant = false;
    }

    onNewTenantInput(field, ev) {
        const value = ev.target.value;
        this.state.newTenant[field] = value;
        if (field === "domain") {
            this.state.newTenant._domainTouched = true;
        }
        if (field === "db_name") {
            this.state.newTenant._dbTouched = true;
        }
        if (field === "name") {
            let slug = this._slugTenantToken(value);
            if (slug && /^[0-9]/.test(slug)) {
                slug = `t_${slug}`;
            }
            if (!this.state.newTenant._dbTouched) {
                this.state.newTenant.db_name = slug ? `${slug}_db`.replace(/_+/g, "_") : "";
            }
            if (!this.state.newTenant._domainTouched) {
                this.state.newTenant.domain = slug
                    ? `${slug.replace(/_/g, "-").replace(/-+/g, "-")}.tcrm.online`
                    : "";
            }
            if (!this.state.newTenant.client_name) {
                this.state.newTenant.client_name = value;
            }
        }
    }

    onNewTenantSelect(field, ev) {
        this.state.newTenant[field] = parseInt(ev.target.value) || false;
    }

    async saveTenant() {
        const t = this.state.newTenant;
        if (!t.name?.trim()) {
            this.notification.add(_t("Tenant name is required"), { type: "warning" });
            return;
        }
        if (!t.domain?.trim()) {
            this.notification.add(_t("Domain is required"), { type: "warning" });
            return;
        }
        if (!t.db_name?.trim()) {
            this.notification.add(_t("Database name is required"), { type: "warning" });
            return;
        }
        if (!t.admin_login?.trim()) {
            this.notification.add(_t("Admin username is required"), { type: "warning" });
            return;
        }
        if (!t.admin_password || t.admin_password.length < 8) {
            this.notification.add(_t("Admin password must be at least 8 characters"), { type: "warning" });
            return;
        }
        this.state.createTenantBusy = true;
        try {
            const result = await rpc("/tcrm_master/tenant/create_and_provision", {
                name: t.name.trim(),
                client_name: (t.client_name || t.name).trim(),
                support_email: t.support_email || "",
                support_phone: t.support_phone || "",
                sector_id: t.sector_id || false,
                domain: t.domain.trim(),
                db_name: t.db_name.trim().toLowerCase(),
                admin_login: t.admin_login.trim(),
                admin_password: t.admin_password,
            });
            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
                return;
            }
            this.notification.add(
                _t("Tenant queued for provisioning. Worker will create DB, apply domain/SSL, and set the admin login."),
                { type: "success" },
            );
            this.state.showCreateTenant = false;
            if (result.tenant_id) {
                await this.openTenantDetail(result.tenant_id);
            } else {
                await this.navigateTo("tenants");
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        } finally {
            this.state.createTenantBusy = false;
        }
    }

    async activateTenant(tenantId) {
        try {
            await rpc("/tcrm_master/tenant/update", { tenant_id: tenantId, values: { state: "active" } });
            this.notification.add(_t("Tenant activated"), { type: "success" });
            if (this.state.screen === "tenant_detail") {
                await this.openTenantDetail(tenantId);
            } else {
                await this._loadTenants();
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    async deactivateTenant(tenantId) {
        try {
            await rpc("/tcrm_master/tenant/update", { tenant_id: tenantId, values: { state: "draft" } });
            this.notification.add(_t("Tenant deactivated"), { type: "info" });
            if (this.state.screen === "tenant_detail") {
                await this.openTenantDetail(tenantId);
            } else {
                await this._loadTenants();
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    async deleteTenant(tenantId) {
        if (!confirm(_t("Are you sure you want to delete this tenant? This cannot be undone."))) return;
        try {
            const res = await rpc("/tcrm_master/tenant/delete", { tenant_id: tenantId });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(res.message || _t("Deleted"), { type: "success" });
            await this.navigateTo("tenants");
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    openTenantInOdoo(tenantId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tcrm.tenant",
            res_id: tenantId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ── Tenant 360 module toggle ──────────────────────────────────

    async toggleModule(entitlementId, tenantId = null, moduleId = null) {
        try {
            const res = await rpc("/tcrm_master/module_entitlement/toggle", {
                entitlement_id: entitlementId || false,
                tenant_id: tenantId || this.state.tenantDetail?.id || false,
                module_id: moduleId || false,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            if (this.state.tenantDetail) {
                await this.openTenantDetail(this.state.tenantDetail.id);
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    async _loadAppsCatalog() {
        const [catalog, packages] = await Promise.all([
            rpc("/tcrm_master/apps/catalog"),
            rpc("/tcrm_master/packages"),
        ]);
        this.state.appsCatalog = catalog?.apps || [];
        this.state.appsCatalogTotal = catalog?.total || 0;
        this.state.packages = packages || [];
        if (!this.state.selectedPackageForApps && this.state.packages.length) {
            const preferred = this.state.packages.find((p) => p.code === "all_free_apps") || this.state.packages[0];
            this.selectPackageForApps(preferred.id);
        }
    }

    get filteredAppsCatalog() {
        const q = (this.state.appsCatalogSearch || "").trim().toLowerCase();
        if (!q) {
            return this.state.appsCatalog;
        }
        return this.state.appsCatalog.filter((a) =>
            (a.display_name || "").toLowerCase().includes(q)
            || (a.name || "").toLowerCase().includes(q)
            || (a.category || "").toLowerCase().includes(q)
        );
    }

    onAppsCatalogSearchInput(ev) {
        this.state.appsCatalogSearch = ev.target.value;
    }

    selectPackageForApps(packageId) {
        const pkg = this.state.packages.find((p) => p.id === Number(packageId));
        this.state.selectedPackageForApps = pkg || null;
        this.state.packageModuleDraftIds = pkg ? [...(pkg.module_ids || [])] : [];
    }

    onPackageForAppsChange(ev) {
        this.selectPackageForApps(ev.target.value);
    }

    togglePackageModuleDraft(moduleId) {
        const id = Number(moduleId);
        const set = new Set(this.state.packageModuleDraftIds);
        if (set.has(id)) {
            set.delete(id);
        } else {
            set.add(id);
        }
        this.state.packageModuleDraftIds = [...set];
    }

    isPackageModuleSelected(moduleId) {
        return this.state.packageModuleDraftIds.includes(Number(moduleId));
    }

    async savePackageModules() {
        if (!this.state.selectedPackageForApps) {
            return;
        }
        try {
            const res = await rpc("/tcrm_master/packages/set_modules", {
                package_id: this.state.selectedPackageForApps.id,
                module_ids: this.state.packageModuleDraftIds,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(_t("Package apps updated"), { type: "success" });
            await this._loadAppsCatalog();
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    async fillPackageAllApps() {
        if (!this.state.selectedPackageForApps) {
            return;
        }
        if (!confirm(_t("Assign every installed free app to this package?"))) {
            return;
        }
        try {
            const res = await rpc("/tcrm_master/packages/set_modules", {
                package_id: this.state.selectedPackageForApps.id,
                fill_all: true,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(_t("All free apps assigned to package"), { type: "success" });
            await this._loadAppsCatalog();
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    onGrantModuleChange(ev) {
        this.state.grantModuleId = ev.target.value ? Number(ev.target.value) : false;
    }

    async grantModuleToTenant() {
        if (!this.state.tenantDetail || !this.state.grantModuleId) {
            return;
        }
        try {
            const res = await rpc("/tcrm_master/tenant/module/grant", {
                tenant_id: this.state.tenantDetail.id,
                module_id: this.state.grantModuleId,
                state: "allowed",
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(_t("App granted to tenant"), { type: "success" });
            this.state.grantModuleId = false;
            await this.openTenantDetail(this.state.tenantDetail.id);
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── Domain CRUD ────────────────────────────────────────────────

    async deleteDomain(domainId) {
        if (!confirm(_t("Remove this domain?"))) return;
        try {
            await rpc("/tcrm_master/domain/delete", { domain_id: domainId });
            this.notification.add(_t("Domain removed"), { type: "success" });
            if (this.state.tenantDetail) {
                await this.openTenantDetail(this.state.tenantDetail.id);
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    async requestDomainSsl(domainId) {
        try {
            const res = await rpc("/tcrm_master/domain/request_ssl", { domain_id: domainId });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(res.message || _t("SSL expand queued"), { type: "success" });
            if (this.state.tenantDetail) {
                await this.openTenantDetail(this.state.tenantDetail.id);
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    onTenantAdminResetInput(ev) {
        this.state.tenantAdminResetPassword = ev.target.value;
    }

    onTenantAdminLoginInput(ev) {
        this.state.tenantAdminResetLogin = ev.target.value;
    }

    async resetTenantAdminPassword(tenantId = null) {
        const detail = this.state.tenantDetail;
        const tid = tenantId || detail?.id;
        if (!tid) {
            return;
        }
        const pwd = (this.state.tenantAdminResetPassword || this.state.accessCredModal?.password || "").trim();
        if (pwd.length < 8) {
            this.notification.add(_t("Password must be at least 8 characters"), { type: "warning" });
            return;
        }
        try {
            const login = (
                this.state.tenantAdminResetLogin
                || this.state.accessCredModal?.login
                || detail?.provision?.admin_login
                || "admin"
            ).trim();
            const res = await rpc("/tcrm_master/tenant/reset_admin_password", {
                tenant_id: tid,
                new_password: pwd,
                admin_login: login,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(res.message || _t("Tenant credentials updated"), { type: "success" });
            this.state.tenantAdminResetPassword = "";
            this.state.accessCredModal = null;
            if (detail && detail.id === tid) {
                await this.openTenantDetail(detail.id);
            }
            if (this.state.screen === "access") {
                await this._loadAccess();
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── Users ─────────────────────────────────────────────────────

    async _loadUsers() {
        try {
            const data = await rpc("/tcrm_master/users", { search: this.state.userSearch });
            this.state.users = data || [];
        } catch (e) {
            this.state.users = [];
            this.notification.add(e.message || _t("Failed to load users"), { type: "danger" });
        }
    }

    async searchUsers() {
        this.state.loading = true;
        await this._loadUsers();
        this.state.loading = false;
    }

    async toggleUserActive(userId, currentActive) {
        if (!userId) {
            this.notification.add(_t("Invalid user id"), { type: "warning" });
            return;
        }
        if (Number(userId) === Number(this.state.currentUserId)) {
            this.notification.add(_t("You cannot deactivate your own user from Command Center."), { type: "warning" });
            return;
        }
        try {
            await rpc("/tcrm_master/user/update", { user_id: userId, values: { active: !currentActive } });
            this.notification.add(currentActive ? _t("User deactivated") : _t("User activated"), { type: "success" });
            await this._loadUsers();
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── Access ────────────────────────────────────────────────────

    async _loadAccess() {
        try {
            this.state.accessData = await rpc("/tcrm_master/access");
        } catch (e) {
            this.state.accessData = null;
            this.notification.add(e.message || _t("Failed to load Access Management"), { type: "danger" });
        }
    }

    get filteredAccessCatalog() {
        const catalog = this.state.accessData?.catalog || [];
        const q = (this.state.accessAppSearch || "").trim().toLowerCase();
        if (!q) {
            return catalog;
        }
        return catalog.filter((a) =>
            (a.display_name || "").toLowerCase().includes(q)
            || (a.name || "").toLowerCase().includes(q)
        );
    }

    onAccessAppSearchInput(ev) {
        this.state.accessAppSearch = ev.target.value;
    }

    async toggleModuleAccess(row, module) {
        const moduleId = module.module_id;
        const target = (row.modules || []).find((m) => m.module_id === moduleId) || module;
        try {
            const res = await rpc("/tcrm_master/module_entitlement/toggle", {
                entitlement_id: target.id || false,
                tenant_id: row.id,
                module_id: moduleId,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            target.state = res.new_state;
            target.entitled = res.new_state === "allowed";
            target.id = res.entitlement_id || target.id;
            target.source = "manual";
            if (!(row.modules || []).includes(target)) {
                row.modules = [...(row.modules || []), target];
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
            await this._loadAccess();
        }
    }

    async syncTenantEntitlements(tenantId = null, allTenants = false) {
        try {
            const res = await rpc("/tcrm_master/tenant/sync_entitlements", {
                tenant_id: tenantId || false,
                all_tenants: allTenants,
            });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(_t("Entitlements synced from provision / package"), { type: "success" });
            await this._loadAccess();
            if (this.state.tenantDetail) {
                await this.openTenantDetail(this.state.tenantDetail.id);
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    openAccessCredModal(row) {
        if (!row?.db_name) {
            this.notification.add(_t("This tenant has no dedicated database"), { type: "warning" });
            return;
        }
        this.state.accessCredModal = {
            tenant_id: row.id,
            name: row.name,
            login: row.provision?.admin_login || "admin",
            password: "",
            login_url: row.provision?.login_url || "",
        };
        this.state.tenantAdminResetLogin = row.provision?.admin_login || "admin";
        this.state.tenantAdminResetPassword = "";
    }

    closeAccessCredModal() {
        this.state.accessCredModal = null;
    }

    onAccessCredLoginInput(ev) {
        if (this.state.accessCredModal) {
            this.state.accessCredModal.login = ev.target.value;
        }
        this.state.tenantAdminResetLogin = ev.target.value;
    }

    onAccessCredPasswordInput(ev) {
        if (this.state.accessCredModal) {
            this.state.accessCredModal.password = ev.target.value;
        }
        this.state.tenantAdminResetPassword = ev.target.value;
    }

    async saveAccessCredModal() {
        if (!this.state.accessCredModal) {
            return;
        }
        await this.resetTenantAdminPassword(this.state.accessCredModal.tenant_id);
    }

    moduleForTenant(row, catalogApp) {
        const modules = row.modules || [];
        return modules.find((m) => m.module_id === catalogApp.id) || {
            id: false,
            module_id: catalogApp.id,
            name: catalogApp.display_name,
            state: "blocked",
            entitled: false,
            source: "",
        };
    }

    // ── Financials ────────────────────────────────────────────────

    async _loadFinancials() {
        this.state.financials = await rpc("/tcrm_master/financials");
    }

    async invoiceAction(invoiceId, actionType) {
        try {
            const res = await rpc("/tcrm_master/invoice/action", { invoice_id: invoiceId, action: actionType });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(_t("Invoice updated"), { type: "success" });
            await this._loadFinancials();
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── God-Mode: Ghost Login ─────────────────────────────────────

    async ghostLogin(tenantId) {
        if (!tenantId) return;
        try {
            const res = await rpc("/tcrm_master/tenant/ghost_login", { tenant_id: tenantId });
            if (res.action === "open_tab" || res.action === "redirect") {
                window.open(res.url, "_blank", "noopener,noreferrer");
                this.notification.add(_t("Tenant workspace opened in new tab."), { type: "info" });
            } else if (res.error) {
                this.notification.add(res.error, { type: "danger" });
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── God-Mode: Freeze / Unfreeze ───────────────────────────────

    async freezeTenant(tenantId) {
        if (!confirm(_t("Freeze this tenant? All users will be locked out immediately."))) return;
        try {
            const res = await rpc("/tcrm_master/tenant/freeze", { tenant_id: tenantId, freeze: true });
            this.notification.add(res.message || _t("Tenant frozen"), { type: "warning" });
            if (this.state.screen === "tenant_detail") {
                await this.openTenantDetail(tenantId);
            } else {
                await this._loadTenants();
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    async unfreezeTenant(tenantId) {
        try {
            const res = await rpc("/tcrm_master/tenant/freeze", { tenant_id: tenantId, freeze: false });
            this.notification.add(res.message || _t("Tenant unfrozen"), { type: "success" });
            if (this.state.screen === "tenant_detail") {
                await this.openTenantDetail(tenantId);
            } else {
                await this._loadTenants();
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── God-Mode: Global Employees ────────────────────────────────

    async _loadEmployees() {
        try {
            const data = await rpc("/tcrm_master/global/employees", {
                search: this.state.employeeSearch,
                tenant_id: this.state.employeeTenantFilter || null,
            });
            this.state.employees = data || [];
        } catch (e) {
            this.state.employees = [];
            this.notification.add(e.message || _t("Failed to load employees"), { type: "danger" });
        }
    }

    onEmployeeSearchInput(ev) {
        this.state.employeeSearch = ev.target.value;
    }

    onEmployeeSearchKeydown(ev) {
        if (ev.key === "Enter") this.searchEmployees();
    }

    async searchEmployees() {
        this.state.loading = true;
        await this._loadEmployees();
        this.state.loading = false;
    }

    onEmployeeTenantFilter(ev) {
        this.state.employeeTenantFilter = parseInt(ev.target.value) || null;
        this.searchEmployees();
    }

    // ── God-Mode: Reset Password Modal ────────────────────────────

    openResetPasswordModal(user) {
        this.state.resetPasswordModal = { user, newPassword: "", confirmPassword: "" };
    }

    closeResetPasswordModal() {
        this.state.resetPasswordModal = null;
    }

    onResetPasswordInput(field, ev) {
        if (this.state.resetPasswordModal) {
            this.state.resetPasswordModal[field] = ev.target.value;
        }
    }

    async confirmResetPassword() {
        const m = this.state.resetPasswordModal;
        if (!m) return;
        if (m.newPassword !== m.confirmPassword) {
            this.notification.add(_t("Passwords do not match"), { type: "warning" });
            return;
        }
        if ((m.newPassword || "").length < 6) {
            this.notification.add(_t("Password must be at least 6 characters"), { type: "warning" });
            return;
        }
        try {
            const res = await rpc("/tcrm_master/user/reset_password", { user_id: m.user.id, new_password: m.newPassword });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(_t("Password reset successfully"), { type: "success" });
            this.closeResetPasswordModal();
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── God-Mode: Change Role Modal ───────────────────────────────

    async _loadTenantRoles() {
        try {
            const res = await rpc("/tcrm_master/user/roles", {});
            if (res && res.roles && res.roles.length) {
                this.state.tenantRoles = res.roles;
            }
        } catch (e) {
            // keep fallback catalog defined in state
        }
    }

    openChangeRoleModal(user) {
        const current = (user.groups || []).join(" ").toLowerCase();
        let role = "sales";
        const order = ["admin", "manager", "finance", "operations", "sales", "viewer"];
        for (const key of order) {
            if (current.includes(key)) {
                role = key;
                break;
            }
        }
        this.state.changeRoleModal = { user, role };
    }

    closeChangeRoleModal() {
        this.state.changeRoleModal = null;
    }

    onChangeRoleSelect(ev) {
        if (this.state.changeRoleModal) {
            this.state.changeRoleModal.role = ev.target.value;
        }
    }

    async confirmChangeRole() {
        const m = this.state.changeRoleModal;
        if (!m) return;
        try {
            const res = await rpc("/tcrm_master/user/change_role", { user_id: m.user.id, role: m.role });
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
                return;
            }
            this.notification.add(res.message || (_t("Role updated to ") + m.role), { type: "success" });
            this.closeChangeRoleModal();
            if (this.state.tenantDetail && this.state.tenantDetail.id) {
                await this.openTenantDetail(this.state.tenantDetail.id);
            }
            await this._loadEmployees();
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
    }

    // ── View Repair ───────────────────────────────────────────────

    async repairViews() {
        this.state.loading = true;
        try {
            const res = await rpc("/tcrm_master/repair/views");
            if (res.error) {
                this.notification.add(res.error, { type: "danger" });
            } else {
                const msg = res.patched_count > 0
                    ? `${res.message} Removed undefined fields from: ${res.patched.map(p => p.view).join(', ')}.`
                    : _t("All views are clean — no undefined fields found.");
                this.notification.add(msg, {
                    type: res.patched_count > 0 ? "success" : "info",
                    sticky: res.patched_count > 0,
                });
                if (res.patched_count > 0) {
                    // Force reload so Odoo picks up the patched view arches
                    setTimeout(() => window.location.reload(), 2000);
                }
            }
        } catch (e) {
            this.notification.add(e.message || "Error", { type: "danger" });
        }
        this.state.loading = false;
    }

    // ── God-Mode: AI Health ───────────────────────────────────────

    async _loadAiHealth() {
        try {
            const data = await rpc("/tcrm_master/ai_health");
            this.state.aiHealth = data || [];
        } catch (e) {
            this.state.aiHealth = [];
        }
    }

    // ── TCRM AI tenant entitlement ────────────────────────────────

    async _loadAiTenants() {
        const data = await rpc("/tcrm_master/ai/tenants", {});
        this.state.aiTenants = data?.rows || [];
    }

    aiEntitlementLabel(state) {
        const map = {
            unavailable: _t("Kullanılamaz"),
            granted: _t("Erişim Verildi"),
            config_required: _t("Yapılandırma Gerekli"),
            active: _t("Aktif"),
            suspended: _t("Askıya Alındı"),
            quota_exceeded: _t("Kota Aşıldı"),
            connection_error: _t("Bağlantı Hatası"),
        };
        return map[state] || state || "—";
    }

    async onAiGrant(row) {
        this.state.aiBusyId = row.tenant_id;
        try {
            const res = await rpc("/tcrm_master/ai/grant", { tenant_id: row.tenant_id });
            if (res.error) throw new Error(res.error);
            this.notification.add(_t("TCRM AI erişimi verildi."), { type: "success" });
            await this._loadAiTenants();
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
        this.state.aiBusyId = null;
    }

    async onAiRevoke(row) {
        this.state.aiBusyId = row.tenant_id;
        try {
            const res = await rpc("/tcrm_master/ai/revoke", { tenant_id: row.tenant_id });
            if (res.error) throw new Error(res.error);
            this.notification.add(_t("TCRM AI erişimi kaldırıldı."), { type: "warning" });
            await this._loadAiTenants();
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
        this.state.aiBusyId = null;
    }

    async onAiSuspend(row) {
        this.state.aiBusyId = row.tenant_id;
        try {
            const res = await rpc("/tcrm_master/ai/suspend", { tenant_id: row.tenant_id });
            if (res.error) throw new Error(res.error);
            this.notification.add(_t("TCRM AI askıya alındı."), { type: "warning" });
            await this._loadAiTenants();
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
        this.state.aiBusyId = null;
    }

    async onAiManageConfig(row) {
        try {
            const res = await rpc("/tcrm_master/ai/manage_config", { tenant_id: row.tenant_id });
            if (res.error) throw new Error(res.error);
            this.notification.add(res.message || _t("Yapılandırma tenant veritabanında yönetilir."), {
                type: "info",
                sticky: true,
            });
            if (res.login_url) {
                window.open(res.login_url, "_blank");
            }
            await this._loadAiTenants();
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
    }

    async onAiUsage(row) {
        try {
            const res = await rpc("/tcrm_master/ai/usage", { tenant_id: row.tenant_id });
            if (res.error) throw new Error(res.error);
            this.notification.add(
                `${row.tenant}: ${res.requests_this_month || 0} req / ${res.tokens_this_month || 0} tokens (${this.aiEntitlementLabel(res.entitlement)})`,
                { type: "info", sticky: true }
            );
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
    }

    aiHealthBadgeClass(status) {
        if (status === "ok") return "bg-success";
        if (status === "degraded") return "bg-warning text-dark";
        return "bg-danger";
    }

    // ── Technical ─────────────────────────────────────────────────

    async _loadTechnical() {
        this.state.technical = await rpc("/tcrm_master/technical");
        await this._loadAiHealth();
    }

    // ── DB Console ────────────────────────────────────────────────

    onSqlInput(ev) {
        this.state.sqlQuery = ev.target.value;
    }

    dbConsoleRows() {
        const rows = this.state.sqlResult?.rows || [];
        if (!rows.length) {
            return [
                { tenant_id: "TEN-0082-XA", business_name: "AeroDynamics Systems", status: "Active" },
                { tenant_id: "TEN-0941-KB", business_name: "NeuralNet Finance Hub", status: "Active" },
                { tenant_id: "TEN-0104-ML", business_name: "Global Logistics Sentinel", status: "Maintenance" },
            ];
        }
        return rows.slice(0, 50).map((r) => ({
            tenant_id: r.tenant_id || r.id || "-",
            business_name: r.business_name || r.name || "-",
            status: r.status || r.state || "Active",
        }));
    }

    dbConsoleMetaText() {
        const count = Number(this.state.sqlResult?.row_count || this.state.sqlResult?.rows?.length || 256);
        return `${count} ROWS RETURNED`;
    }

    showSqlHistory() {
        this.notification.add(_t("Query history view is coming next."), { type: "info" });
    }

    showDbSchema() {
        this.notification.add(_t("Schema explorer will be available here."), { type: "info" });
    }

    formatSqlQuery() {
        const src = (this.state.sqlQuery || "").trim();
        if (!src) return;
        const kw = /\b(select|from|where|join|left join|right join|inner join|order by|group by|limit|offset|and|or|insert into|update|delete from|values|set)\b/gi;
        this.state.sqlQuery = src.replace(kw, (m) => m.toUpperCase());
    }

    async copySqlQuery() {
        try {
            await navigator.clipboard.writeText(this.state.sqlQuery || "");
            this.notification.add(_t("SQL copied to clipboard."), { type: "success" });
        } catch {
            this.notification.add(_t("Unable to copy query in this browser."), { type: "warning" });
        }
    }

    onSqlAddRow() {
        this.notification.add(_t("Read-only mode: insert disabled."), { type: "warning" });
    }

    onSqlEditSelected() {
        this.notification.add(_t("Edit selected will be enabled with row selection."), { type: "info" });
    }

    onSqlDeleteSelected() {
        this.notification.add(_t("Delete selected will be enabled with row selection."), { type: "info" });
    }

    onSqlFilter() {
        this.notification.add(_t("Filter drawer is coming next."), { type: "info" });
    }

    exportSqlResults() {
        const res = this.state.sqlResult;
        if (!res || !res.columns || !res.rows) {
            this.notification.add(_t("Nothing to export yet."), { type: "warning" });
            return;
        }
        const quote = (v) => {
            const s = String(v ?? "");
            return `"${s.replaceAll('"', '""')}"`;
        };
        const lines = [
            res.columns.map(quote).join(","),
            ...res.rows.map((row) => res.columns.map((c) => quote(row[c])).join(",")),
        ];
        const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "db_query_results.csv";
        a.click();
        URL.revokeObjectURL(url);
    }

    async executeQuery() {
        if (!this.state.sqlQuery.trim()) return;
        this.state.sqlLoading = true;
        this.state.sqlResult = null;
        try {
            this.state.sqlResult = await rpc("/tcrm_master/db/query", { sql: this.state.sqlQuery });
        } catch (e) {
            this.state.sqlResult = { error: e.message || String(e) };
        }
        this.state.sqlLoading = false;
    }

    // ── Analytics ─────────────────────────────────────────────────

    async _loadAnalytics() {
        const metrics = Object.entries(this.state.analyticsMetrics || {})
            .filter(([, enabled]) => !!enabled)
            .map(([key]) => key);
        const data = await rpc("/tcrm_master/analytics", { metrics });
        this.state.analytics = this._normalizeAnalyticsPayload(data, metrics);

        // Keep metric chips synchronized with backend defaults if provided.
        if (this.state.analytics?.available_metrics?.length) {
            const next = {};
            const selected = new Set(this.state.analytics.selected_metrics || metrics);
            for (const metric of this.state.analytics.available_metrics) {
                next[metric.key] = selected.has(metric.key);
            }
            this.state.analyticsMetrics = {
                ...this.state.analyticsMetrics,
                ...next,
            };
        }
    }

    _normalizeAnalyticsPayload(data, metrics) {
        const metricDefs = [
            { key: "tenant_id", label: _t("Tenant ID"), icon: "id_card" },
            { key: "growth_rate", label: _t("Growth Rate"), icon: "trending_up" },
            { key: "churn_risk", label: _t("Churn Risk"), icon: "warning" },
            { key: "security_status", label: _t("Security Status"), icon: "security" },
            { key: "revenue", label: _t("Revenue"), icon: "payments" },
            { key: "mrr", label: _t("MRR"), icon: "query_stats" },
        ];

        const rows = (data?.report_rows || []).map((row) => ({
            tenant_record_id: this._tenantIdForOpen(row),
            tenant_id: row.tenant_id || `T-${String(row.tenant_record_id || row.tenant_id || "").padStart(4, "0")}`,
            tenant_name: row.tenant_name || "",
            growth_rate: row.growth_rate ?? 0,
            churn_risk: row.churn_risk || "low",
            security_status: row.security_status || "secure",
            revenue: row.revenue ?? row.total_revenue ?? 0,
            mrr: row.mrr ?? 0,
            state: row.state || "draft",
        }));

        const total = rows.length;
        const riskCount = rows.filter((row) => row.churn_risk !== "low").length;
        const activeCount = rows.filter((row) => row.state === "active").length;
        const systemHealth = total ? Number(((activeCount / total) * 100).toFixed(1)) : 100;

        return {
            ...data,
            generated_at: data?.generated_at || new Date().toLocaleString(),
            available_metrics: data?.available_metrics || metricDefs,
            selected_metrics: data?.selected_metrics || metrics,
            report_rows: rows,
            summary: {
                total_tenants: data?.summary?.total_tenants ?? total,
                active_count: data?.summary?.active_count ?? activeCount,
                risk_count: data?.summary?.risk_count ?? riskCount,
                system_health: data?.summary?.system_health ?? systemHealth,
                neural_prediction: data?.summary?.neural_prediction ?? 94.2,
            },
            risk_heatmap: {
                system_integrity: data?.risk_heatmap?.system_integrity ?? systemHealth,
                revenue_stability: data?.risk_heatmap?.revenue_stability ?? Math.max(35, 100 - riskCount * 10),
            },
        };
    }

    _tenantIdForOpen(row) {
        const candidate = row?.tenant_record_id ?? row?.id ?? row?.tenant_id;
        if (Number.isInteger(candidate) || (typeof candidate === "number" && Number.isFinite(candidate))) {
            return Number(candidate);
        }
        if (typeof candidate === "string") {
            const direct = Number.parseInt(candidate, 10);
            if (!Number.isNaN(direct) && direct > 0) {
                return direct;
            }
            const match = candidate.match(/\d+/);
            if (match) {
                const extracted = Number.parseInt(match[0], 10);
                if (!Number.isNaN(extracted) && extracted > 0) {
                    return extracted;
                }
            }
        }
        return 0;
    }

    exportAnalytics(format) {
        window.open("/tcrm_master/analytics/export?format=" + format, "_blank");
    }

    async regenerateAnalyticsReport() {
        this.state.loading = true;
        try {
            await this._loadAnalytics();
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        }
        this.state.loading = false;
    }

    toggleAnalyticsMetric(key) {
        this.state.analyticsMetrics[key] = !this.state.analyticsMetrics[key];
    }

    setAnalyticsFormat(format) {
        this.state.analyticsFormat = format;
    }

    onAnalyticsCellInput(index, field, ev) {
        if (!this.state.analytics?.report_rows?.[index]) return;
        const raw = (ev.target.textContent || "").trim();
        if (field === "tenant_id") {
            this.state.analytics.report_rows[index].tenant_id = raw;
            return;
        }
        this.state.analytics.report_rows[index][field] = raw;
    }

    toggleAnalyticsBot() {
        this.state.analyticsBotOpen = !this.state.analyticsBotOpen;
    }

    openAdvancedAnalyticsAction() {
        this.action.doAction("tcrm_saas_core.action_tcrm_advanced_analytics");
    }

    // ── Formatting Helpers ────────────────────────────────────────

    fmtMoney(amount, currency) {
        if (amount === undefined || amount === null) return "0";
        return Number(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + (currency ? " " + currency : "");
    }

    fmtNum(n) {
        if (n === undefined || n === null) return "0";
        return Number(n).toLocaleString();
    }

    fmtPct(n) {
        if (n === undefined || n === null) return "0%";
        return Number(n).toFixed(1) + "%";
    }

    dashboardShortDate(ts) {
        if (!ts) {
            return "";
        }
        const s = String(ts).trim();
        const normalized = s.includes("T") ? s : s.replace(" ", "T");
        const d = new Date(normalized);
        if (!Number.isNaN(d.getTime())) {
            return d.toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
            });
        }
        return s.length > 22 ? s.slice(0, 19) + "…" : s;
    }

    dashboardRelativeTime(ts) {
        if (!ts) {
            return "";
        }
        const s = String(ts).trim();
        const normalized = s.includes("T") ? s : s.replace(" ", "T");
        const d = new Date(normalized);
        if (Number.isNaN(d.getTime())) {
            return this.dashboardShortDate(ts);
        }
        try {
            const lang = document.documentElement.lang || undefined;
            const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
            const sec = Math.round((d.getTime() - Date.now()) / 1000);
            const abs = Math.abs(sec);
            if (abs < 45) {
                return rtf.format(0, "second");
            }
            if (abs < 3600) {
                return rtf.format(Math.round(sec / 60), "minute");
            }
            if (abs < 86400) {
                return rtf.format(Math.round(sec / 3600), "hour");
            }
            return rtf.format(Math.round(sec / 86400), "day");
        } catch (_) {
            return this.dashboardShortDate(ts);
        }
    }

    mixBarWidth(pkg) {
        const mix = this.state.dashboard?.package_mix || [];
        const max = mix.reduce((m, x) => Math.max(m, x.count), 0) || 1;
        return Math.round((pkg.count / max) * 100);
    }

    healthColor(health) {
        const map = { excellent: "#10b981", good: "#3b82f6", warning: "#f59e0b", critical: "#ef4444" };
        return map[health] || "#6b7280";
    }

    stateLabel(state) {
        const map = { draft: _t("Draft"), active: _t("Active"), trial: _t("Trial"), past_due: _t("Past Due"), suspended: _t("Suspended"), cancelled: _t("Cancelled"), open: _t("Open"), paid: _t("Paid"), overdue: _t("Overdue") };
        return map[state] || state;
    }

    stateBadgeClass(state) {
        const map = {
            active: "bg-success", paid: "bg-success",
            draft: "bg-secondary", cancelled: "bg-secondary",
            trial: "bg-info", open: "bg-info",
            past_due: "bg-warning text-dark", warning: "bg-warning text-dark", medium: "bg-warning text-dark",
            overdue: "bg-danger", suspended: "bg-danger", critical: "bg-danger",
            excellent: "bg-success", good: "bg-info", low: "bg-success",
        };
        return map[state] || "bg-secondary";
    }
}

// Register client actions in the same file as the component to avoid bundle-order issues.
registry.category("actions").add("tcrm_master.command_center", TcrmCommandCenter, { force: true });
registry.category("actions").add("tcrm_master.advanced_analytics", TcrmCommandCenter, { force: true });
