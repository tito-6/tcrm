# TCRM Custom Addons — Module Structure, Windows, Reports, Views & Key Functions

Structured summary of all custom addons under `custom_addons/`, with emphasis on **tcrm_ai** and **tcrm-related** modules.

---

## 1. Module structure

### 1.1 tcrm_ai
- **Manifest**: `name`: TCRM AI · `version`: 1.0 · `category`: Productivity  
- **Summary**: Gemini-powered AI: database, reports, real-time web, any question  
- **Depends**: `base`, `web`, `mail_bot`, `base_setup`  
- **Data**: `security/ir.model.access.csv`, `data/tcrm_ai_data.xml`, `data/tcrm_ai_provider_data.xml`, `views/tcrm_ai_settings_views.xml`, `views/tcrm_ai_provider_views.xml`, `views/res_config_settings_views.xml`, `views/tcrm_ai_menus.xml`  
- **Assets**: `tcrm_ai_chat.js`, `tcrm_ai_chat.xml` (backend)  
- **Main model files**:
  - **tcrm_ai_config.py** — TCRM AI configuration (Gemini key, model, timeout, temperature, max_tokens, ai_base_url, provider summary).
  - **tcrm_ai_engine.py** — Abstract engine: `_ask()`, tools (search_sales, get_payment_plan, get_record_details, get_situation, etc.), provider/key fallback.
  - **tcrm_ai_provider.py** — AI providers (Gemini, OpenAI, Anthropic, Groq, Mistral, Ollama) and keys; health/cooldown.
  - **tcrm_ai_session.py** — Transient session: history, get_history, append, clear.
  - **res_config_settings.py** — Inherit: Gemini key/model, ai_base_url, timeout, AI block in Settings.
  - **mail_bot.py** — Inherit: replace tcrmBot with TCRM AI in Discuss 1:1 chat.
  - **res_users.py** — Inherit: TCRM AI welcome message for new users.

### 1.2 tcrm_vector_sync
- **Manifest**: TCRM Vector Sync 1.0, Productivity  
- **Depends**: `base`  
- **Data**: `security/ir.model.access.csv`, `data/vector_sync_cron.xml`  
- **Main model files**:
  - **vector_sync_mixin.py** — Abstract mixin: create/write/unlink enqueue to `tcrm.vector.sync.queue` for RAG ingest.
  - **vector_sync_queue.py** — Queue processed by cron POST to `{tcrm.ai_base_url}/ingest`.
  - **res_partner.py** — Extend `res.partner` with mixin + semantic text for vectorization.

### 1.3 tcrm_propertio (Propertio)
- **Manifest**: Propertio 1.1, Real Estate  
- **Depends**: `base`, `web`, `mail`, `crm`, `tcrm_vector_sync`  
- **Data**: security, `data/propertio_data.xml`, contract/report templates, many view/menu/report XMLs (see below).  
- **Main model files**:
  - **propertio_project.py** — Projects, blocks, types, stages, features, units inventory.
  - **propertio_unit.py** — Units, categories, statuses, features, sale metrics, attachments.
  - **propertio_sale.py** — Sale contracts, payment plan (installments), confirm, links to unit/customer/payments.
  - **propertio_payment.py** — Payments (bank/cash/check/senet), allocation to installments (FIFO), post/cancel.
  - **crm_lead_inherit.py** — 5-star priority on CRM lead form/kanban.
  - **tcmb_manager.py** — `res.currency` inherit: TCMB rates (get_tcmb_data, _apply_rates).  
- **Wizards**: `propertio_print_wizard.py`, `propertio_sale_wizard.py`, `propertio_unified_report_wizard.py`, `propertio_report_export.py`.  
- **Reports**: `report_generator.py`, `report_definitions.py`, `report_base.py`; QWeb: contract + collection.

### 1.4 tcrm_web_enhance
- **Manifest**: TCRM Web Enhance 1.0, Hidden  
- **Depends**: `web`  
- **Data**: none  
- **Assets**: SCSS + `toast_service.js` for branding, spacing, toasts, dark mode.

### 1.5 tcrm_saas_core
- **Manifest**: TCRM SaaS Core 1.0  
- **Depends**: `base`  
- **Data**: `security/ir.model.access.csv`, `views/tenant_views.xml`  
- **Main model**: **tcrm_tenant.py** — Tenants (name, client_name, state, active); multi-tenancy master.

---

## 2. Windows & menus

### 2.1 tcrm_ai
- **ir.actions.client**: `action_tcrm_ai_client` — name “Ask TCRM AI”, tag `tcrm_ai.chat`.  
- **ir.actions.act_window**:
  - `action_tcrm_ai_config` — **TCRM AI Settings** · model `tcrm.ai.config` · view_mode `form` · used by menu AI Settings.
  - `action_tcrm_ai_provider` — **AI Providers** · model `tcrm.ai.provider` · view_mode `tree,form` · context `search_default_active: 1`.  
- **Menus** (parent `menu_tcrm_ai_root` “TCRM AI”):
  - **Ask TCRM AI** → `action_tcrm_ai_client` (seq 10).
  - **AI Providers** → `action_tcrm_ai_provider` (seq 85, `base.group_system`).
  - **AI Settings** → `action_tcrm_ai_config` (seq 90, `base.group_system`).

### 2.2 tcrm_saas_core
- **ir.actions.act_window**: `action_tcrm_tenant` — **Tenants** · model `tcrm.tenant` · view_mode `list,form`.  
- **Menus**: **TCRM Master** (root, `base.group_system`) → **Tenants** → `action_tcrm_tenant`.

### 2.3 tcrm_propertio (concise)
- **Root**: Propertio → Inventory, Sales, Collections, Reporting, Configuration.  
- **Inventory**: Projects (`action_propertio_project`), Units (`action_propertio_unit`).  
- **Sales**: New Sale wizard (`action_propertio_sale_wizard`), Sales Contracts (`action_propertio_sale`, search_view `view_propertio_sale_search`).  
- **Collections**: Payments (`action_propertio_payment`).  
- **Reporting**: Reports Center → Export Reports wizard; Collection/Payment reports; Sales reports; Customer; Financial; Performance; Property; Admin; Marketing (many act_window opening `propertio.unified.report.wizard` with `default_report_type`).  
- **Configuration**: Master Data (Unit Features, Project Types/Stages, Property Categories, Detailed Statuses, Sale Stages), Personnel & Partners (Agencies, Sales Personnel).  
- **Server actions**: Export Contracts (Word) — `action_server_export_word` (code: `action = records.action_export_batch_word()`); Danışman Karnesi (Bu Ay) — `action_server_danisman_karnesi_this_month`.

---

## 3. Tree / form / search views (by module)

### 3.1 tcrm_ai
- **tcrm.ai.config**: form `view_tcrm_ai_config_form` — Gemini key/model, Local AI URL, providers summary (button to AI Providers), generation (timeout, temperature, max_tokens).  
- **tcrm.ai.provider**: tree `view_tcrm_ai_provider_tree` (name, provider_code, priority, active_key_count, health_status); form `view_tcrm_ai_provider_form` — provider/limits, notebook “API Keys” with inline tree for keys (name, api_key, key_display, status, usage_display, cooldown_until), buttons Reset Cooldowns / Test All Keys.  
- **res.config.settings**: inherit block “TCRM AI” (ai_health_status, ai_provider_summary, Gemini key/model, Local AI URL, timeout, Manage AI providers, Open TCRM AI settings).

### 3.2 tcrm_saas_core
- **tcrm.tenant**: form (state statusbar, name, client_name, active); list (name, client_name, state badge, active).

### 3.3 tcrm_propertio
- **propertio.project**: form (name, city, type, stage, gdv, unit_count, properties; notebook: Amenities & Features, Units Inventory, Blocks); list (name, city, type, stage, unit_count, gdv sum).  
- **propertio.unit**: form (statusbar available/option/sold/handover; button Sales History; name, project/block, floor, entrance, category, status, view_type, list_price, gross_m2, properties; notebook: General Info, Features, Financial Stats, Documents); list (project, block, name, floor, category, status, gross_m2, list_price, state badge).  
- **propertio.sale**: form (header: Confirm Sale, Print/Export; statusbar draft/confirmed/cancel; buttons Property, Customer, Payments, Collections; contract ref, contract_no, partner, unit, date_sale, sale_price, total_paid, balance; notebook: Payment Plan with installments list + Rebalance, General Info, Unit Specs, Legal & Bank, Team, Technical Financials); list (name, project, partner, unit, sale_price sum, state badge; header button Download Word); search `view_propertio_sale_search` (name, partner, unit, project; filters Draft/Confirmed; group by State).  
- **propertio.payment**: form (Post/Cancel; name, partner, sale, payment_method, payment_date, currency, amount, exchange_rate, covered_amount; chatter); list (name, payment_date, partner, sale, amount, currency, state).  
- **propertio.feature**: list (icon, name, color).  
- **propertio.project.type** / **propertio.unit.category**: form (name, active, properties_definition).  
- **propertio.installment**: multiple list/pivot/graph views for Collection Map, Cash Flow, GDV, Tahsilat, Proje Nakit, Danışman Karnesi, Kırmızı Alarm, etc.  
- **propertio.print.options**: form — Print/Export options (Download PDF/Word, View HTML, Batch Word).  
- **propertio.sale.wizard**: form — New Sale (partner, unit, currency, price, list_price; Payment Terms: down_payment, installments, balloon; Exchange Rates with TCMB HTML).  
- **propertio.unified.report.wizard**: form — Report type, export format, date range, filters (project, partner, user); Generate / Download / View in Browser / New Report.  
- **propertio.report.export**: form — report_type, export_format, date_from/date_to; Export / Download.  
- **crm.lead**: inherit form & kanban — priority widget for 5-star.

---

## 4. Reports (ir.actions.report & QWeb)

### 4.1 tcrm_propertio
- **action_report_propertio_contract**  
  - Model: `propertio.sale`  
  - report_type: qweb-pdf  
  - report_name / report_file: `tcrm_propertio.report_contract_document`  
  - binding_model: `propertio.sale`  
  - Template: **report_contract_document** — Sales Contract PDF (buyer, date, project, unit code; property details table; financial terms; payment plan table; signatures).  

- **action_report_propertio_collection**  
  - Model: `propertio.installment`  
  - report_type: qweb-pdf  
  - report_name / report_file: `tcrm_propertio.report_collection_doc`  
  - binding_model: `propertio.installment`  
  - Template: **report_collection_doc** — Collection Status Report (Sale Ref, Description, Due Date, Amount, Paid, Residual, Status; color by payment_status).  

All other “reports” in Propertio are either **act_window** opening the unified report wizard (with different `default_report_type`) or **pivot/graph/list** views (no QWeb PDF); actual XLSX/CSV/PDF/HTML generation is in `report_generator.py` and report definitions.

---

## 5. Screens/views summary (models & key fields)

| View type | Model | Key fields / purpose |
|-----------|--------|------------------------|
| Form | tcrm.ai.config | Gemini key/model, ai_base_url, timeout, temperature, max_tokens, provider_summary |
| Tree, Form | tcrm.ai.provider | name, provider_code, default_model, priority, limits; keys inline |
| Form (inherit) | res.config.settings | TCRM AI block: health, summary, Gemini, URL, timeout, buttons |
| Client | — | Ask TCRM AI (tag tcrm_ai.chat) |
| Form, List | tcrm.tenant | name, client_name, state, active |
| Form, List | propertio.project | name, city, type, stage, gdv, unit_count, properties, units, blocks |
| Form, List | propertio.unit | name, project, block, floor, category, status, list_price, state, features, financials, attachments |
| Form, List, Search | propertio.sale | name, partner, unit, sale_price, installments, state; filters draft/confirmed |
| Form, List | propertio.payment | partner, sale, amount, payment_method, payment_date, exchange_rate, covered_amount, state |
| List | propertio.feature | icon, name, color |
| Form | propertio.print.options | Buttons: PDF, Word, HTML, Batch Word |
| Form | propertio.sale.wizard | partner, unit, price, payment terms, TCMB rates; action_generate_sale |
| Form | propertio.unified.report.wizard | report_type, export_format, date_filter, project/partner/user; Generate, Download, View HTML, Reset |
| Form | propertio.report.export | report_type, export_format, dates; Export, Download |
| List, Pivot, Graph | propertio.installment | Collection Map, Cash Flow, GDV, Tahsilat, Danışman Karnesi, Kırmızı Alarm, etc. |

---

## 6. Key functions (public methods, buttons / API)

### 6.1 tcrm_ai (models)
- **tcrm.ai.config**: `get_config(company=None)` — Get or create config for company; sync to ICP; legacy fallback when provider table missing.  
- **tcrm.ai.provider**: `action_reset_cooldowns()` — Reset cooldowns for all keys; `action_test_all_keys()` — Test keys, post result as message.  
- **tcrm.ai.key**: `is_available()`, `reset_if_cooldown_expired()`, `mark_rate_limited()`, `mark_exhausted()`, `mark_error()`, `mark_success()`, `reset_cooldowns()`.  
- **tcrm.ai.engine**: `_ask(message, base_url=None)` — Main entry: tools (get_situation, get_record_details, search_sales, get_payment_plan, get_paid_amount, get_overdue_payments, summarize_sales_pipeline, search_partners, run_search_read, web_search), returns answer/tables/links; `_test_provider_keys(provider)`; `_format_answer_as_html(result)`.  
- **tcrm.ai.session**: `get_history(session_id)`, `append(session_id, role, content)`, `clear(session_id)`; `_auto_vacuum_sessions()`.  
- **res.config.settings**: `get_values()` / `set_values()` — Load/save Gemini, ai_base_url, timeout; sync to tcrm.ai.config when possible.

### 6.2 tcrm_ai (controllers)
- **/web/tcrm_ai/ping** (GET) — Health check.  
- **/tcrm_ai/ask** (JSON) — `ask(message, session_id=None)` — Call engine `_ask`, return answer/tables/links.  
- **/tcrm_ai/clear_session** (JSON) — `clear_session(session_id)`.  
- **/tcrm_ai/export** (POST) — Export chat tables as Excel/HTML/PDF.

### 6.3 tcrm_vector_sync
- **vector_sync_mixin**: `create`, `write`, `unlink` — Overridden to enqueue payloads to queue for ingest.  
- **res.partner**: extended with mixin + semantic text for RAG.

### 6.4 tcrm_propertio (models)
- **propertio.sale**:  
  - `action_rebalance_plan()` — Auto-balance payment plan / add remainder installment.  
  - `action_confirm()` — Set state confirmed, unit state sold.  
  - `action_view_installments()` — Open installments list/graph/pivot.  
  - `action_view_unit()` — Open unit form.  
  - `action_view_customer()` — Open partner form.  
  - `action_view_payments()` — Open payments list for this sale.  
  - `action_download_word()` — act_url to `/propertio/contract_word/{id}`.  
  - `action_print_contract_html()` — act_url to report HTML.  
  - `action_export_batch_word()` — act_url batch Word (used by server action).  
  - `action_download_pdf()` — act_url to `/propertio/contract_pdf/{id}`.  
  - `action_open_full_screen()` — Open sale form.  
- **propertio.unit**: `action_view_sales_history()` — Open sales for unit.  
- **propertio.payment**: `action_post()` — Allocate payment to installments (FIFO), set state posted; `action_cancel()`.  
- **propertio.installment**: `action_open_danisman_karnesi_this_month()` — Open Danışman Karnesi filtered to this month’s paid installments (used by server action).  
- **res.currency** (tcmb_manager): `get_tcmb_data(target_date=None)` — Fetch TCMB rates; `_apply_rates`, `_update_tcmb_rates` (cron).

### 6.5 tcrm_propertio (wizards)
- **propertio.print.options**: `action_download_pdf()`, `action_download_word()`, `action_print_html()`, `action_export_word_batch()`.  
- **propertio.sale.wizard**: `action_generate_sale()` — Create sale + installments from wizard.  
- **propertio.unified.report.wizard**: `action_generate_report()`, `action_download()`, `action_view_html()`, `action_print_pdf()`, `action_reset()`.  
- **propertio.report.export**: `action_export()`, `action_download()`.

### 6.6 tcrm_propertio (controllers)
- **download_contract_word(sale, **kw)** — Single contract Word.  
- **download_contract_word_batch(ids, **kw)** — Batch Word.  
- **download_contract_pdf(sale, **kw)** — Contract PDF.

### 6.7 tcrm_saas_core
- **tcrm.tenant**: `create` override (if any specific logic; otherwise standard).

---

This document lists every window, menu, report, main screen/view, and the main public methods used by buttons or API in the TCRM custom addons (tcrm_ai, tcrm_vector_sync, tcrm_propertio, tcrm_web_enhance, tcrm_saas_core).
