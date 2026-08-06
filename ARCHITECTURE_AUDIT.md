# TCRM Architecture Audit (Phase 1)

**Date:** 2026-03-01  
**Scope:** Existing TCRM app on **port 8069** (no new app, no port 3000).

---

## 1. Project root layout

| Path | Purpose |
|------|--------|
| `tcrm.conf` | Main config: addons_path, http_port=8069, db, data_dir |
| `run.bat` | Starts server: `python -m tcrm -c tcrm.conf` (PYTHONPATH=tcrm-src) |
| `tcrm-src/` | Core framework (Tcrm/Odoo fork) |
| `custom_addons/` | TCRM modules: tcrm_saas_core, tcrm_propertio, tcrm_ai |
| `TCRM/` | Brand assets (logos, fonts – Bricolage Grotesque) |
| `venv/` | Python 3.10 virtualenv |
| `tcrm_data/` | Runtime data, logs |

---

## 2. Tech stack

| Layer | Technology |
|-------|------------|
| **Framework** | Tcrm (Odoo Community Edition fork), Python 3.10 |
| **Entry point** | `tcrm-src/tcrm-bin` → `tcrm.cli.main()` → server on 8069 |
| **Backend** | Python (tcrm.*), WSGI (werkzeug in dev) |
| **Database** | PostgreSQL (db_port 5432 in tcrm.conf) |
| **Templating** | QWeb (XML) for views and backend UI |
| **Frontend** | Tcrm Web Client: JS (OWL-like), SCSS (Bootstrap 5–based), bundled via `web.assets_backend` |
| **Routing** | Tcrm HTTP + ir.http: controllers, menu actions, `ir.actions.act_window` |

---

## 3. Entry point and server

- **Binary:** `d:\tcrm\tcrm-src\tcrm-bin` (script) and `tcrm/__main__.py` both call `tcrm.cli.main()`.
- **Config:** `tcrm.conf` is passed with `-c tcrm.conf`.
- **Addons path (order):**  
  `d:/tcrm/tcrm-src/tcrm/addons` → `d:/tcrm/tcrm-src/addons` → `d:/tcrm/custom_addons`.

---

## 4. Templates and views

- **Backend UI:** Defined in XML as `ir.ui.view` (form, list, kanban, etc.) in each addon’s `views/*.xml`.
- **Main layout:** `tcrm-src/addons/web/views/webclient_templates.xml` (e.g. `web.layout`, `web.frontend_layout`).
- **Rendering:** QWeb in Python; backend assets loaded via `web.assets_backend` (SCSS + JS).
- **Custom views:**  
  - **tcrm_saas_core:** `views/tenant_views.xml` (tenant form/list, menu).  
  - **tcrm_propertio:** Multiple XMLs under `views/` (menus, project, unit, sale, payment, wizards, reports).  
  - **tcrm_ai:** Settings and menus; chat UI in `static/src/tcrm_ai_chat/`.

---

## 5. Static assets

- **Core backend assets:** `tcrm-src/addons/web/static/` (SCSS under `src/`, Bootstrap, FontAwesome, JS).
- **Variables:** `web/static/src/scss/pre_variables.scss` (Bootstrap overrides), then `lib/bootstrap/scss/_variables*.scss`.
- **Backend bundle:** `web.assets_backend` in `web/__manifest__.py` (long list of SCSS/JS).
- **Custom addons:**  
  - **tcrm_ai:** `static/src/tcrm_ai_chat/` (JS + XML).  
  - **tcrm_propertio:** `static/description/icon.png`.  
  - No custom addon SCSS in `custom_addons` yet; enhancement will add one.

---

## 6. Routing and menus

- **HTTP:** Tcrm’s `ir.http` + controllers (e.g. `tcrm_ai.controllers.main`).
- **Menus:** `ir.ui.menu` + `ir.actions.act_window` in XML (e.g. TCRM Master → Tenants; Propertio → Inventory, Sales, Collections, Reporting, Configuration).
- **Access:** Role-based via `groups="base.group_system"` etc. and `ir.model.access.csv`.

---

## 7. Custom modules (custom_addons)

| Module | Role |
|--------|------|
| **tcrm_saas_core** | Multi-tenancy: `tcrm.tenant` (name, client_name, active, state), DB creation on create, Tenant form/list and “TCRM Master” menu. |
| **tcrm_propertio** | Real estate: projects, units, sales, payments, reports, wizards; extends CRM lead; many views and reports. |
| **tcrm_ai** | AI (Gemini): config, engine, chat UI; depends on `web`, `mail_bot`, `base_setup`; injects `tcrm_ai_chat` into backend assets. |

---

## 8. Summary

- **Single app:** One Tcrm server on **port 8069**; no separate Next.js or other server.
- **Enhancements** will be done by: (1) adding a small **tcrm_web_enhance** module in `custom_addons` for global UI (SCSS variables, toasts, loading, dark mode), and (2) **editing existing** view XML and, where applicable, SCSS in `custom_addons` and, if needed, minimal overrides in `tcrm-src/addons/web` (prefer extending via new assets in custom addon).
- **Branding:** Deep Blue #101E55, Navy #0e142c, Bricolage Grotesque (README); applied in `web/static/src/scss/primary_variables.scss` and enhanced via `tcrm_web_enhance`.

---

## Implementation summary (Phases 2–5)

### Phase 2: UI/UX
- **tcrm_web_enhance** (new module in `custom_addons`): SCSS for TCRM variables, card radius, spacing utilities (`.tcrm-mt-*`, `.tcrm-p-*`), list row hover, form group spacing, dark-mode CSS vars, toast container styles, responsive touch hit areas.
- **tcrm_saas_core**: Tenant list shows state as badge (success/muted); form has placeholders and class for styling.
- **primary_variables.scss** (core): Fixed duplicate `$o-tcrm-navy`; added `$o-tcrm-action-red: #E00000`.

### Phase 3: Functional
- **tcrm_web_enhance**: `toast_service.js` — `window.tcrmToast(message, type, durationMs)` for success/error/info toasts (non-intrusive).
- **tcrm_propertio**: Sale search view — added “Group By” > “State” filter.

### Phase 4: Code quality
- **tcrm_saas_core**: Tenant create — on DB creation failure, raise `UserError` with clear message instead of only logging; use `_()` for translation.

### Phase 5: How to run and verify
1. Start TCRM on **port 8069**: `run.bat` or `python -m tcrm -c tcrm.conf` (PYTHONPATH=tcrm-src).
2. Update Apps list, install **TCRM Web Enhance**.
3. Optional: upgrade **TCRM SaaS Core** and **Propertio** to get view/error-handling changes.
4. Verify: Tenants list (badge, spacing), Tenant form (placeholders), Propertio Sales (search > Group By State), browser console `tcrmToast('Test', 'success')`.
