# TCRM Market Analysis — Phase 1 Repository & Tenancy Audit

**Date:** 2026-07-23  
**Spec:** `Piyasa Analizi.md`  
**Addon to create:** `tcrm_market_analysis` (user-facing: Piyasa Analizi)  
**Status:** Phase 1 complete — module code must not precede this document.

---

## 1. Repository structure

| Path | Role |
|------|------|
| `d:\tcrm\` | Workspace root |
| `custom_addons\` | TCRM custom modules (install path) |
| `tcrm-src\` | TCRM/Odoo fork (framework) |
| `tcrm-src\tcrm-bin` | Server entry |
| `tcrm.conf` | Active runtime config |
| `odoo.conf` | Alternate config (also present) |
| `tcrm_data\` | Filestore / data_dir |
| `scripts\` | Ad-hoc shell/test scripts |
| `tests\` | Top-level test helpers |
| `TCRM\` | Brand assets (fonts, logos) |
| `docs\execution\` | This execution trail (created for this module) |
| `Piyasa Analizi.md` | Product/engineering specification |

There is **no** existing `custom_addons/tcrm_market_analysis` directory.

---

## 2. Git status and branch

| Fact | Value |
|------|-------|
| Branch | `master` |
| Commits | **None yet** (`fatal: your current branch 'master' does not have any commits yet`) |
| Working tree | Large staged/untracked tree (entire product checkout) |
| Remote tracking | Not established in this clone state |

Unresolved: first commit / remote origin not verified in this audit.

---

## 3. Custom addons (exact)

Under `custom_addons/`:

| Addon | Role |
|-------|------|
| `tcrm_saas_core` | Multi-tenancy control plane + Command Center (spec “tcrm_master” equivalent) |
| `tcrm_propertio` | Real-estate engine (projects, units, sales, payments, reports) |
| `tcrm_ai` | Agentic AI hub |
| `tcrm_ai_research` | RAGFlow research assistant |
| `tcrm_research_hub` | Research hub OWL client |
| `tcrm_vector_sync` | Vector ingestion queue/mixin |
| `tcrm_web_enhance` | UI/branding/sidebar icon fixes |
| `tcrm_mock_data` | Deterministic mock/demo builder + tours |

---

## 4. Exact “tcrm_master” path

**Important naming split (do not invent a second control plane):**

| Concept in spec | Actual in repo |
|-----------------|----------------|
| `tcrm_master` **module** | **Does not exist** as an addon |
| Master / control-plane **module** | `custom_addons/tcrm_saas_core` |
| Master **database name** | `tcrm_master` (`tcrm.conf` → `db_name = tcrm_master`, `dbfilter = ^tcrm_master$`) |
| Client action tags using `tcrm_master.*` | Used as **OWL action tag namespace** only, e.g. `tcrm_master.command_center` in `tcrm_saas_core` |

**Control-plane path:** `d:\tcrm\custom_addons\tcrm_saas_core\`

---

## 5. Tenant models and fields

Primary files:

- `custom_addons/tcrm_saas_core/models/tcrm_tenant.py`
- `custom_addons/tcrm_saas_core/models/tcrm_saas_ops.py`

| Model | Key fields |
|-------|------------|
| `tcrm.tenant` | `name`, `client_name`, `company_id`, `sector_id`, `support_email`, `support_phone`, `domain_ids`, `subscription_ids`, `module_entitlement_ids`, `invoice_ids`, `db_name`, `active`, `state` (`draft`/`active`), `is_frozen`, `latitude`, `longitude` |
| `tcrm.tenant.domain` | `tenant_id`, `company_id` (related), `domain`, `is_primary`, `verified`, `ssl_status`, `active` |
| `tcrm.tenant.subscription` | `tenant_id`, `package_id`, `billing_cycle`, `status` (includes `suspended`), dates, amounts |
| `tcrm.tenant.module.entitlement` | `tenant_id`, `module_id`, `state` (`allowed`/`blocked`/`trial`), `source` |
| `tcrm.tenant.invoice` | Billing invoices |
| `tcrm.tenant.sector` | Sector catalog |
| `tcrm.saas.package` | Package + allowed `ir.module.module` apps |
| `tcrm.saas.package.feature` | Feature lines |

`db_name` help text (verbatim intent): optional dedicated tenant database; empty = single-database multi-company mode.

---

## 6. Domain and database fields

- Domain uniqueness: SQL constraint `unique(domain)` on `tcrm.tenant.domain`.
- One active primary domain per tenant (Python constraint).
- Demo domains seeded as `{code}.tcrm.local` in `tcrm.tenant` demo seeding.
- Database selection for dedicated DB: `tcrm.tenant.db_name` + ghost-login URL ` /tcrm?db={db_name} `.
- Multi-company mode: ghost-login URL ` /tcrm?cids={company_id} `.

---

## 7. Domain-to-database request flow

**Observed (code + config), not assumed:**

1. `tcrm.conf` forces `dbfilter = ^tcrm_master$` and `db_name = tcrm_master`.
2. Framework DB selection lives in `tcrm-src/tcrm/http.py` (`db_filter`, session DB, `X-Odoo-Database` / query `db`).
3. There is **no** custom reverse-proxy Host→DB mapper in `tcrm_saas_core` that overrides framework `dbfilter` based on `tcrm.tenant.domain`.
4. Tenant registry domains are stored for admin/SaaS ops; practical isolation in the current local config is primarily **`res.company` + ir.rules** on the master DB.
5. Optional dedicated DBs are created via `tcrm.tenant._create_tenant_db()` → `tcrm.service.db.exp_create_database`.
6. Opening a dedicated DB is explicit (`?db=`), not silent Host rewrite.

**Implication for market analysis:** install and store market data in the **current request database** (tenant DB when dedicated; otherwise company-scoped rows in the active DB). Never write market listings into a separate invented registry. Refuse seeding when current DB is the master control DB used only for SaaS admin (see Phase 14 rules).

---

## 8. Provisioning and suspension flow

| Action | Mechanism |
|--------|-----------|
| Create tenant | `tcrm.tenant.create` → auto-create `res.company` if missing; optional `_create_tenant_db` |
| Activate | `state`: `draft` → `active` |
| Freeze / suspend users | `action_freeze_tenant` / `action_unfreeze_tenant` + API `/tcrm_master/tenant/freeze` |
| Subscription suspend | `tcrm.tenant.subscription.status = suspended` |
| Module entitlement | Package sync `_sync_module_entitlements_from_subscription`; manual grant/block APIs |
| Ghost login | `/tcrm_master/tenant/ghost_login` (system admin only) |

Master API: `custom_addons/tcrm_saas_core/controllers/master_api.py`.

---

## 9. Module-installation flow

- Modules install via standard TCRM/Odoo `ir.module.module` on the **target database**.
- Packages (`tcrm.saas.package.module_ids`) and entitlements (`tcrm.tenant.module.entitlement`) gate which **applications** a tenant may use; they do not auto-install into every DB.
- Local install/upgrade pattern (from `CODEX_AGENTS.md` / README):

```powershell
cd D:\tcrm
$env:PYTHONPATH = "D:\tcrm\tcrm-src"
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -i tcrm_market_analysis --stop-after-init
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -u tcrm_market_analysis --stop-after-init
```

For a dedicated tenant DB, the same `-i`/`-u` must target that DB explicitly — never silently loop all databases.

---

## 10. Relevant TCRM models (summary)

See Phase 2 document for full map. High-signal models:

| Area | Models |
|------|--------|
| Property | `propertio.project`, `propertio.block`, `propertio.unit`, `propertio.unit.category`, `propertio.feature` |
| Sales | `propertio.sale`, `propertio.installment`, `propertio.payment`, `propertio.offer` |
| CRM | `crm.lead` (+ Propertio bridges) |
| Contacts/brokers | `res.partner` (agency via `propertio.sale.agency_id`) |
| SaaS | `tcrm.tenant*` |
| Dashboards | OWL `propertio.dashboard`, SaaS Command Center |
| Import/jobs | No market-listing import model yet; pattern = wizards + `ir.cron` |

---

## 11. Queue / cron / import frameworks

| Pattern | Location |
|---------|----------|
| `ir.cron` | `tcrm_propertio/data/propertio_cron.xml`, `tcrm_ai_research/data/ai_research_cron.xml`, `tcrm_saas_core/data/tcrm_saas_billing_data.xml`, `tcrm_vector_sync` queue cron |
| Queue model | `tcrm.vector.sync.queue` (vector only — not a general job bus) |
| `queue_job` | **Not present** as a dependency |
| Imports | File wizards / report export patterns in Propertio; no shared CSV market importer |

Market analysis should use **own job model** + `ir.cron` methods that bind to `self.env.cr.dbname` explicitly.

---

## 12. Test commands

Backend (module-tagged), pattern from `tcrm_ai_research`:

```powershell
$env:PYTHONPATH = "D:\tcrm\tcrm-src"
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master --test-enable --test-tags=tcrm_market_analysis --stop-after-init
```

Browser/HttpCase: see `tcrm_mock_data/tests/test_tours.py` (`HttpCase`, `post_install`).

Isolation script precedent: `redteam_tenant_isolation_test.py` (company-level isolation).

---

## 13. Asset commands

Assets declared in `__manifest__.py` under `web.assets_backend`. Dev server with `dev_mode = all` in `tcrm.conf` reloads assets. No separate webpack build for these OWL apps.

Restart / upgrade module after adding asset paths:

```powershell
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -u tcrm_market_analysis --stop-after-init
```

---

## 14. Module update commands

See §9. Also `run.bat` / `run.ps1` start the server without upgrade.

---

## 15. Frontend shell and sidebar

- Apps appear as root `ir.ui.menu` with `web_icon` / `web_icon_data`.
- OWL client actions registered via `registry.category("actions").add("<tag>", Component)`.
- Precedents: `tcrm_ai.chat`, `tcrm_ai_research.assistant`, `propertio.dashboard`, `tcrm_master.command_center`.
- Spec route `/tcrm/market-analysis` is optional; existing pattern prefers **client action tags**, not custom HTTP SPA routes. Use `ir.actions.client` tag `tcrm_market_analysis.app` unless a controller is required for public assets.
- Map stack already used: Leaflet 1.9.4 in `tcrm_saas_core` assets.

---

## 16. Security conventions

- Groups + privileges: `res.groups` + `res.groups.privilege` (see `tcrm_ai_research/security/ai_research_security.xml`).
- Company rules: `[('company_id', 'in', company_ids)]` (Propertio).
- ACL CSV: `security/ir.model.access.csv`.
- Tenant role ladder in SaaS: Viewer / Sales / Operations / Finance / Manager / Admin.

---

## 17. Unresolved facts

1. Whether production deployments use Host-based DB routing outside this repo (nginx/Caddy not present here).
2. Whether dedicated tenant databases are provisioned in CI/staging with full module sets.
3. Exact “refuse seed on master” policy: master DB currently also holds multi-company tenant operational data; seeding must refuse **SaaS-control-only** misuse and cross-DB fan-out, while still allowing company-scoped demo in environments that use multi-company on `tcrm_master`.
4. No licensed Sahibinden API credentials or endpoints exist in repo — connector must stay disabled.
5. Git history empty — cannot cite prior release tags.

---

## Phase 1 gate

This inventory exists at:

`docs/execution/tcrm_market_analysis_inventory.md`

Proceed to Phase 2 model map, then module implementation.
