/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@tcrm/owl";

/**
 * Lead / Fırsat Havuzu list: progressive load on scroll so users can
 * scroll continuously without clicking the pager « » controls.
 */
export class CrmHavuzuListController extends ListController {
    setup() {
        super.setup();
        this._havuzuScrollEl = null;
        this._havuzuOnScroll = null;
        this._havuzuLoadingMore = false;
        onMounted(() => this._havuzuAttachScroll());
        onWillUnmount(() => this._havuzuDetachScroll());
    }

    get display() {
        const display = super.display;
        return {
            ...display,
            controlPanel: {
                ...(display.controlPanel || {}),
                pager: false,
            },
        };
    }

    _havuzuFindScrollEl(root) {
        const candidates = [
            root.querySelector(".o_list_renderer"),
            root.closest(".o_content"),
            document.querySelector(".o_action_manager .o_content"),
            root.parentElement,
        ].filter(Boolean);
        for (const el of candidates) {
            const style = window.getComputedStyle(el);
            const canScroll =
                /(auto|scroll)/.test(style.overflowY) ||
                el.scrollHeight > el.clientHeight + 1;
            if (canScroll) {
                return el;
            }
        }
        return candidates[0] || null;
    }

    _havuzuAttachScroll() {
        const root = this.rootRef?.el;
        if (!root) {
            return;
        }
        const scrollEl = this._havuzuFindScrollEl(root);
        if (!scrollEl) {
            return;
        }
        this._havuzuScrollEl = scrollEl;
        this._havuzuOnScroll = () => {
            this._havuzuMaybeLoadMore();
        };
        scrollEl.addEventListener("scroll", this._havuzuOnScroll, { passive: true });
        // First paint may already need more rows on tall screens
        Promise.resolve().then(() => this._havuzuMaybeLoadMore());
    }

    _havuzuDetachScroll() {
        if (this._havuzuScrollEl && this._havuzuOnScroll) {
            this._havuzuScrollEl.removeEventListener("scroll", this._havuzuOnScroll);
        }
        this._havuzuScrollEl = null;
        this._havuzuOnScroll = null;
    }

    async _havuzuMaybeLoadMore() {
        if (this._havuzuLoadingMore) {
            return;
        }
        const list = this.model?.root;
        if (!list || list.isGrouped) {
            return;
        }
        const el = this._havuzuScrollEl;
        if (!el) {
            return;
        }
        const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 280;
        const needsFill = el.scrollHeight <= el.clientHeight + 40;
        if (!nearBottom && !needsFill) {
            return;
        }
        const count = list.count || 0;
        const loaded = list.records?.length || 0;
        if (!count || loaded >= count) {
            return;
        }
        const step = 80;
        const nextLimit = Math.min((list.limit || step) + step, count);
        if (nextLimit <= (list.limit || 0)) {
            return;
        }
        this._havuzuLoadingMore = true;
        try {
            await list.load({ limit: nextLimit, offset: 0 });
        } finally {
            this._havuzuLoadingMore = false;
            // Continue filling tall screens until scrollable or fully loaded
            Promise.resolve().then(() => this._havuzuMaybeLoadMore());
        }
    }
}

export const crmHavuzuListView = {
    ...listView,
    Controller: CrmHavuzuListController,
};

registry.category("views").add("crm_havuzu_list", crmHavuzuListView);
