/** @odoo-module **/

/**
 * Drag-and-drop reorder for list view column headers.
 * Order is persisted per list view in localStorage.
 */
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onPatched, onWillUnmount } from "@tcrm/owl";

function storageKey(renderer) {
    return `tcrm_column_order,${renderer.keyOptionalFields || "list"}`;
}

function applySavedOrder(columns, orderNames) {
    if (!orderNames?.length || !columns?.length) {
        return columns;
    }
    const byName = new Map();
    const rest = [];
    for (const col of columns) {
        if (col.type === "field" && col.name) {
            byName.set(col.name, col);
        } else {
            rest.push(col);
        }
    }
    const ordered = [];
    for (const name of orderNames) {
        if (byName.has(name)) {
            ordered.push(byName.get(name));
            byName.delete(name);
        }
    }
    ordered.push(...byName.values(), ...rest);
    return ordered;
}

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this._tcrmColDrag = { dragging: null };
        this._tcrmOnDragStart = this._tcrmOnDragStart.bind(this);
        this._tcrmOnDragOver = this._tcrmOnDragOver.bind(this);
        this._tcrmOnDragLeave = this._tcrmOnDragLeave.bind(this);
        this._tcrmOnDrop = this._tcrmOnDrop.bind(this);
        this._tcrmOnDragEnd = this._tcrmOnDragEnd.bind(this);
        onMounted(() => this._tcrmBindColumnDrag());
        onPatched(() => this._tcrmBindColumnDrag());
        onWillUnmount(() => this._tcrmUnbindColumnDrag());
    },

    getActiveColumns() {
        const columns = super.getActiveColumns(...arguments);
        try {
            const raw = browser.localStorage.getItem(storageKey(this));
            if (!raw) {
                return columns;
            }
            return applySavedOrder(columns, JSON.parse(raw));
        } catch {
            return columns;
        }
    },

    _tcrmBindColumnDrag() {
        const root = this.rootRef?.el;
        if (!root) {
            return;
        }
        root.querySelectorAll("thead th[data-name]").forEach((th) => {
            if (th.dataset.tcrmDragBound === "1") {
                return;
            }
            th.dataset.tcrmDragBound = "1";
            th.setAttribute("draggable", "true");
            th.classList.add("o_tcrm_col_draggable");
            th.addEventListener("dragstart", this._tcrmOnDragStart);
            th.addEventListener("dragover", this._tcrmOnDragOver);
            th.addEventListener("dragleave", this._tcrmOnDragLeave);
            th.addEventListener("drop", this._tcrmOnDrop);
            th.addEventListener("dragend", this._tcrmOnDragEnd);
        });
    },

    _tcrmUnbindColumnDrag() {
        const root = this.rootRef?.el;
        if (!root) {
            return;
        }
        root.querySelectorAll("thead th[data-name]").forEach((th) => {
            th.removeEventListener("dragstart", this._tcrmOnDragStart);
            th.removeEventListener("dragover", this._tcrmOnDragOver);
            th.removeEventListener("dragleave", this._tcrmOnDragLeave);
            th.removeEventListener("drop", this._tcrmOnDrop);
            th.removeEventListener("dragend", this._tcrmOnDragEnd);
            delete th.dataset.tcrmDragBound;
        });
    },

    _tcrmOnDragStart(ev) {
        // Don't start column drag from the width-resize handle
        if (ev.target?.closest?.(".o_resize")) {
            ev.preventDefault();
            return;
        }
        const th = ev.currentTarget;
        this._tcrmColDrag.dragging = th.getAttribute("data-name");
        th.classList.add("o_tcrm_col_dragging");
        try {
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", this._tcrmColDrag.dragging);
        } catch {
            // ignore
        }
        this.preventReorder = true;
    },

    _tcrmOnDragOver(ev) {
        ev.preventDefault();
        const th = ev.currentTarget;
        const name = th.getAttribute("data-name");
        if (!this._tcrmColDrag.dragging || name === this._tcrmColDrag.dragging) {
            return;
        }
        th.classList.add("o_tcrm_col_drop_target");
        try {
            ev.dataTransfer.dropEffect = "move";
        } catch {
            // ignore
        }
    },

    _tcrmOnDragLeave(ev) {
        ev.currentTarget.classList.remove("o_tcrm_col_drop_target");
    },

    _tcrmOnDrop(ev) {
        ev.preventDefault();
        const target = ev.currentTarget.getAttribute("data-name");
        const source = this._tcrmColDrag.dragging;
        ev.currentTarget.classList.remove("o_tcrm_col_drop_target");
        if (!source || !target || source === target) {
            return;
        }
        const names = this.columns
            .filter((c) => c.type === "field" && c.name)
            .map((c) => c.name);
        const from = names.indexOf(source);
        const to = names.indexOf(target);
        if (from < 0 || to < 0) {
            return;
        }
        names.splice(to, 0, names.splice(from, 1)[0]);
        try {
            browser.localStorage.setItem(storageKey(this), JSON.stringify(names));
        } catch {
            // ignore
        }
        this.render(true);
    },

    _tcrmOnDragEnd(ev) {
        ev.currentTarget.classList.remove("o_tcrm_col_dragging");
        this.rootRef?.el?.querySelectorAll(".o_tcrm_col_drop_target").forEach((el) => {
            el.classList.remove("o_tcrm_col_drop_target");
        });
        this._tcrmColDrag.dragging = null;
        setTimeout(() => {
            this.preventReorder = false;
        }, 0);
    },
});
