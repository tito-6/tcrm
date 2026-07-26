/** @odoo-module **/
/**
 * TCRM Research Hub — in-app library of synced NotebookLM researches.
 *
 * Primary UX: browse researches stored in TCRM DB.
 * Connect Google (In-Page / Docked) only to establish cookies for sync.
 */

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Layout } from "@web/search/layout";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart, onWillUnmount } from "@tcrm/owl";

const NOTEBOOK_URL = "https://notebooklm.google.com";
const DEFAULT_IFRAME_URL = "/tcrm/research/proxy/h/notebooklm.google.com/";

export class NotebookContainer extends Component {
    static template = "tcrm_research_hub.NotebookContainer";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this._dockedWin = null;
        this._dockTimer = null;
        this._onResize = () => this._syncDockedWindow();

        this.state = useState({
            statusChecked: false,
            accessDenied: false,
            proxyAvailable: false,
            tenantEntitled: false,
            googleConnected: false,
            syncedCount: 0,
            lastSyncAt: null,
            lastSyncMessage: null,
            syncing: false,

            // library | connect | proxy | docked
            panel: "library",
            viewMode: "split",

            notebooks: [],
            notebookSearch: "",
            notebooksLoading: false,

            notebookOpen: false,
            iframeLoaded: false,
            iframeUrl: DEFAULT_IFRAME_URL,

            contextType: "leads",
            contextSearch: "",
            contextLoading: false,
            leads: [],
            units: [],
            projects: [],
            selectedContextId: null,
            researchBrief: "",
        });

        onWillStart(async () => {
            await this._checkAccess();
            if (this.state.tenantEntitled) {
                await this._loadNotebooks();
                await this._loadContextData();
                // Auto-sync when Google session already present
                if (this.state.googleConnected) {
                    await this.syncNow({ silent: true });
                }
            }
        });

        onWillUnmount(() => {
            this._stopDockSync();
            window.removeEventListener("resize", this._onResize);
        });

        window.addEventListener("resize", this._onResize);
    }

    get iframeSandbox() {
        // Reduced sandbox so Google Identity can complete multi-step login.
        return [
            "allow-forms",
            "allow-modals",
            "allow-popups",
            "allow-popups-to-escape-sandbox",
            "allow-same-origin",
            "allow-scripts",
            "allow-downloads",
            "allow-storage-access-by-user-activation",
            "allow-top-navigation",
            "allow-top-navigation-by-user-activation",
        ].join(" ");
    }

    get contextItems() {
        if (this.state.contextType === "leads") {
            return this.state.leads;
        }
        if (this.state.contextType === "projects") {
            return this.state.projects;
        }
        return this.state.units;
    }

    get selectedItem() {
        return this.contextItems.find((i) => i.id === this.state.selectedContextId) || null;
    }

    get filteredNotebooks() {
        const q = (this.state.notebookSearch || "").trim().toLowerCase();
        if (!q) {
            return this.state.notebooks;
        }
        return this.state.notebooks.filter(
            (n) =>
                (n.name || "").toLowerCase().includes(q) ||
                (n.description || "").toLowerCase().includes(q)
        );
    }

    get display() {
        return { controlPanel: false };
    }

    async _checkAccess() {
        try {
            const result = await rpc("/tcrm/research/status", {});
            this.state.proxyAvailable = !!result.proxy_available;
            this.state.tenantEntitled = !!result.tenant_entitled;
            this.state.accessDenied = !result.tenant_entitled;
            this.state.googleConnected = !!result.google_connected;
            this.state.syncedCount = result.synced_count || 0;
            this.state.lastSyncAt = result.last_sync_at;
            this.state.lastSyncMessage = result.last_sync_message;
            if (result.iframe_url) {
                this.state.iframeUrl = result.iframe_url;
            }
            this.state.panel = "library";
        } catch (err) {
            const msg = err?.message || "";
            if (msg.includes("denied") || msg.includes("Access")) {
                this.state.accessDenied = true;
                this.state.tenantEntitled = false;
            } else {
                this.state.tenantEntitled = true;
                this.state.proxyAvailable = false;
                this.state.panel = "library";
            }
        } finally {
            this.state.statusChecked = true;
        }
    }

    async _loadNotebooks() {
        this.state.notebooksLoading = true;
        try {
            const result = await rpc("/tcrm/research/notebooks", {
                search: this.state.notebookSearch || "",
            });
            this.state.notebooks = result.notebooks || [];
            this.state.syncedCount = this.state.notebooks.length;
        } catch (e) {
            this.state.notebooks = [];
        } finally {
            this.state.notebooksLoading = false;
        }
    }

    async syncNow({ silent = false } = {}) {
        this.state.syncing = true;
        try {
            const result = await rpc("/tcrm/research/sync", {});
            if (result.ok) {
                this.state.googleConnected = true;
                this.state.syncedCount = result.count || 0;
                this.state.lastSyncAt = result.last_sync_at;
                this.state.lastSyncMessage = result.message;
                await this._loadNotebooks();
                if (!silent) {
                    this.notification.add(
                        _t("Synced %s researches from NotebookLM.").replace(
                            "%s",
                            String(result.count || 0)
                        ),
                        { type: "success" }
                    );
                }
            } else {
                this.state.googleConnected = false;
                this.state.lastSyncMessage = result.error;
                if (!silent) {
                    this.notification.add(result.error || _t("Sync failed."), {
                        type: "warning",
                        sticky: true,
                    });
                    this.state.panel = "connect";
                }
            }
        } catch (e) {
            if (!silent) {
                this.notification.add(`${_t("Sync failed:")} ${e.message || e}`, {
                    type: "danger",
                });
            }
        } finally {
            this.state.syncing = false;
            await this._checkAccess();
        }
    }

    setPanel(panel) {
        this.state.panel = panel;
        if (panel === "proxy") {
            this.state.iframeLoaded = false;
            this._reloadIframe();
        }
        if (panel === "library") {
            this._loadNotebooks();
        }
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
        this._syncDockedWindow();
    }

    onNotebookSearch(ev) {
        this.state.notebookSearch = ev.target.value;
        this._loadNotebooks();
    }

    openNotebookRecord(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tcrm.research.notebook",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNotebookExternal(nb) {
        const url = nb.url || `${NOTEBOOK_URL}/notebook/${nb.google_notebook_id}`;
        window.open(url, "_blank", "noopener,noreferrer");
    }

    async _loadContextData() {
        this.state.contextLoading = true;
        const domain = this.state.contextSearch
            ? [["name", "ilike", this.state.contextSearch]]
            : [];

        const [leadsResult, unitsResult, projectsResult] = await Promise.allSettled([
            this.orm.searchRead(
                "crm.lead",
                domain,
                ["name", "partner_name", "expected_revenue", "stage_id", "probability", "description"],
                { limit: 25, order: "id desc" }
            ),
            this.orm
                .searchRead(
                    "propertio.unit",
                    domain,
                    ["name", "unit_code", "state", "project_id", "list_price"],
                    { limit: 25, order: "id desc" }
                )
                .catch(() => []),
            this.orm
                .searchRead(
                    "propertio.project",
                    domain,
                    ["name", "stage_id"],
                    { limit: 25, order: "id desc" }
                )
                .catch(() => []),
        ]);

        this.state.leads = leadsResult.status === "fulfilled" ? leadsResult.value : [];
        this.state.units = unitsResult.status === "fulfilled" ? unitsResult.value || [] : [];
        this.state.projects =
            projectsResult.status === "fulfilled" ? projectsResult.value || [] : [];
        this.state.contextLoading = false;
    }

    setContextType(type) {
        this.state.contextType = type;
        this.state.selectedContextId = null;
    }

    selectContextItem(id) {
        this.state.selectedContextId =
            id === this.state.selectedContextId ? null : id;
        this._buildResearchBrief();
    }

    async onContextSearch(ev) {
        this.state.contextSearch = ev.target.value;
        await this._loadContextData();
    }

    onBriefInput(ev) {
        this.state.researchBrief = ev.target.value;
    }

    _buildResearchBrief() {
        const item = this.selectedItem;
        if (!item) {
            return;
        }
        const lines = ["TCRM Research Brief", "===================", ""];
        if (this.state.contextType === "leads") {
            lines.push(`Lead: ${item.name || ""}`);
            if (item.partner_name) {
                lines.push(`Contact: ${item.partner_name}`);
            }
        } else if (this.state.contextType === "units") {
            lines.push(`Unit: ${item.name || item.unit_code || ""}`);
        } else {
            lines.push(`Project: ${item.name || ""}`);
        }
        lines.push("", `From TCRM Research Hub — ${new Date().toISOString()}`);
        this.state.researchBrief = lines.join("\n");
    }

    async copyBrief() {
        const text = (this.state.researchBrief || "").trim();
        if (!text) {
            this.notification.add(_t("Select a record or write a brief first."), {
                type: "warning",
            });
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            this.notification.add(_t("Research brief copied."), { type: "success" });
        } catch (e) {
            this.notification.add(_t("Clipboard blocked by the browser."), {
                type: "danger",
            });
        }
    }

    _panelRect() {
        const el =
            document.querySelector(".o_rhub_dock_target") ||
            document.querySelector(".o_rhub_right") ||
            document.querySelector(".o_rhub_action");
        if (!el) {
            return null;
        }
        const r = el.getBoundingClientRect();
        const left = Math.round(window.screenX + r.left);
        const top = Math.round(window.screenY + r.top + 80);
        const width = Math.max(640, Math.round(r.width));
        const height = Math.max(480, Math.round(r.height));
        return { left, top, width, height };
    }

    _stopDockSync() {
        if (this._dockTimer) {
            clearInterval(this._dockTimer);
            this._dockTimer = null;
        }
    }

    _syncDockedWindow() {
        const win = this._dockedWin;
        if (!win || win.closed) {
            this._dockedWin = null;
            this._stopDockSync();
            this.state.notebookOpen = false;
            return;
        }
        const rect = this._panelRect();
        if (!rect) {
            return;
        }
        try {
            win.resizeTo(rect.width, rect.height);
            win.moveTo(rect.left, rect.top);
        } catch (e) {
            /* browsers may block */
        }
    }

    openDockedNotebookLM() {
        const rect = this._panelRect() || {
            width: 1100,
            height: 800,
            left: Math.max(0, (window.screen.width - 1100) / 2),
            top: Math.max(0, (window.screen.height - 800) / 2),
        };
        const features = [
            `width=${rect.width}`,
            `height=${rect.height}`,
            `left=${rect.left}`,
            `top=${rect.top}`,
            "resizable=yes",
            "scrollbars=yes",
        ].join(",");

        if (this._dockedWin && !this._dockedWin.closed) {
            this._dockedWin.focus();
            this._syncDockedWindow();
            return;
        }

        const win = window.open(NOTEBOOK_URL, "tcrm_notebooklm_docked", features);
        if (!win) {
            this.notification.add(
                _t("Popup blocked. Allow pop-ups for TCRM, then try again."),
                { type: "warning", sticky: true }
            );
            return;
        }
        this._dockedWin = win;
        this.state.notebookOpen = true;
        this.state.panel = "docked";
        this._stopDockSync();
        this._dockTimer = setInterval(() => this._syncDockedWindow(), 800);
        this.notification.add(
            _t(
                "Sign in on Google if needed. Prefer In-Page Connect so TCRM can sync your researches into the library."
            ),
            { type: "info" }
        );
    }

    async onConnectFinished() {
        // Called after user finishes In-Page login — try sync
        await this._checkAccess();
        await this.syncNow({ silent: false });
        this.state.panel = "library";
    }

    async clearGoogleSession() {
        try {
            await rpc("/tcrm/research/proxy/clear", {});
            this.state.googleConnected = false;
            this.notification.add(_t("Cleared Google proxy session."), { type: "info" });
            this._reloadIframe();
        } catch (e) {
            this.notification.add(_t("Could not clear proxy session."), { type: "danger" });
        }
    }

    onIframeLoad() {
        this.state.iframeLoaded = true;
        // After iframe navigates, cookies may have been saved — soft recheck
        this._checkAccess();
    }

    _reloadIframe() {
        const base = this.state.iframeUrl.split("?")[0] || DEFAULT_IFRAME_URL;
        this.state.iframeUrl = `${base}?t=${Date.now()}`;
        this.state.iframeLoaded = false;
    }
}
