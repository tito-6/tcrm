/** @odoo-module **/

/**
 * Highlight the active top-navbar section so users see which window they are on
 * (e.g. Lead Havuzu under CRM → Satış).
 */
function markActiveSections() {
    const current = (window.location.pathname + window.location.search).toLowerCase();
    const curAction = (current.match(/action-(\d+)/) || [])[1];

    document
        .querySelectorAll(".o_menu_sections .o_tcrm_nav_active")
        .forEach((el) => el.classList.remove("o_tcrm_nav_active"));

    if (!curAction) {
        return;
    }

    document
        .querySelectorAll(".o_menu_sections a[href], .o_menu_sections .dropdown-item[href]")
        .forEach((el) => {
            const href = (el.getAttribute("href") || "").toLowerCase();
            const actionMatch = href.match(/action-(\d+)/);
            if (!actionMatch || actionMatch[1] !== curAction) {
                return;
            }
            el.classList.add("o_tcrm_nav_active");
            const dropdown = el.closest(".dropdown, .o-dropdown");
            const toggle =
                dropdown &&
                dropdown.querySelector(
                    ":scope > .dropdown-toggle, :scope > .o_nav_entry, :scope > button"
                );
            if (toggle) {
                toggle.classList.add("o_tcrm_nav_active");
            }
        });
}

function boot() {
    markActiveSections();
    // SPA navigations change the URL without full reload
    const _push = history.pushState;
    const _replace = history.replaceState;
    history.pushState = function () {
        const ret = _push.apply(this, arguments);
        setTimeout(markActiveSections, 50);
        return ret;
    };
    history.replaceState = function () {
        const ret = _replace.apply(this, arguments);
        setTimeout(markActiveSections, 50);
        return ret;
    };
    window.addEventListener("popstate", () => setTimeout(markActiveSections, 50));
    setInterval(markActiveSections, 1500);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
} else {
    boot();
}
