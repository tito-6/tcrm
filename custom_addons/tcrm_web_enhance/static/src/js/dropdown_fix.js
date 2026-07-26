/** @odoo-module **/

/**
 * Global fallback handler for Bootstrap navbar dropdowns (Language selector, User profile, etc.)
 */
document.addEventListener('click', function (e) {
    const toggle = e.target.closest('[data-bs-toggle="dropdown"], [data-toggle="dropdown"], .dropdown-toggle');
    if (toggle) {
        const dropdown = toggle.closest('.dropdown, .dropup, .js_language_selector, .o_no_autohide_item, .nav-item');
        if (dropdown) {
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu) {
                const isShown = menu.classList.contains('show');
                // Close all other open navbar dropdowns
                document.querySelectorAll('.dropdown-menu.show').forEach((m) => m.classList.remove('show'));
                if (!isShown) {
                    menu.classList.add('show');
                    toggle.setAttribute('aria-expanded', 'true');
                } else {
                    menu.classList.remove('show');
                    toggle.setAttribute('aria-expanded', 'false');
                }
                e.preventDefault();
                e.stopPropagation();
            }
        }
    } else if (!e.target.closest('.dropdown-menu')) {
        // Close open dropdowns when clicking outside
        document.querySelectorAll('.dropdown-menu.show').forEach((m) => m.classList.remove('show'));
    }
});
