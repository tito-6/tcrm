# TCRM — Multi-Tenant Real-Estate CRM/ERP Platform

**Connect · Grow · Win**

TCRM is a white-labeled, multi-tenant SaaS platform built on a customized Odoo-based
core (`tcrm-src`), with TCRM branding and a suite of custom modules for real-estate
CRM, sales, call center, marketing, AI, and multi-tenant SaaS operations.

Operated by **AK KOD YAZILIM BİLİŞİM LTD. ŞTİ.** — https://tcrm.online

## Repository layout

| Path | Description |
|------|-------------|
| `tcrm-src/` | Customized platform core (Odoo-based fork). Tracked source. |
| `custom_addons/` | TCRM custom modules (production addons path). |
| `deploy/` | Deployment configuration: nginx, systemd, provisioning scripts, conf template. |
| `docs/` | Project documentation. |
| `TCRM/` | Brand assets (logos, fonts, icons). |
| `.env.example` | Template for environment variables (never commit real `.env`). |

## Key custom modules (`custom_addons/`)

- `tcrm_saas_core` — Tenant management / control plane (TCRM Master).
- `tcrm_saas_routing` — Secure host→database routing and tenant isolation (server-wide module).
- `tcrm_propertio` — Real-estate ERP (projects, blocks, units, sales, installments).
- `tcrm_call_center` — Santral WebRTC call center integration.
- `tcrm_web_enhance` — Public website, branding, docs, i18n (TR/EN).
- `tcrm_ai` — Agentic AI layer over live CRM/ERP data.

## Multi-tenancy & routing

- `tcrm.online` / `www.tcrm.online` → control-plane database (`tcrm_master`).
- A registered, active tenant domain → its **explicitly mapped** database
  (the DB name comes only from the validated `tcrm.tenant` record, never from the
  subdomain string).
- Suspended / not-yet-provisioned / unknown hosts → branded status pages; the Odoo
  database selector/manager is never publicly reachable.

## Configuration

Runtime configuration lives in `/opt/tcrm/tcrm.prod.conf` on the server (not committed;
secrets are supplied via environment / the conf file). `deploy/tcrm.prod.conf.template`
documents the required keys with `CHANGE_ME_*` placeholders. Secrets are provided through
`.env` (see `.env.example`) and are never committed.

## License

Platform core based on Odoo Community Edition (LGPL-3).
TCRM customizations © AK KOD YAZILIM BİLİŞİM LTD. ŞTİ.
