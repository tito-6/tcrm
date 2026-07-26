# TCRM Market Analysis — Execution Progress

**Date:** 2026-07-23

| Phase | Status | Evidence |
|-------|--------|----------|
| 1 Repository/tenancy audit | Done | `docs/execution/tcrm_market_analysis_inventory.md` |
| 2 Model inventory | Done | `docs/execution/tcrm_market_analysis_model_map.md` |
| 3 Source architecture | Done | `custom_addons/tcrm_market_analysis/connectors/*` |
| 4 Addon skeleton | Done | `custom_addons/tcrm_market_analysis/` |
| 5 Security | Done | `security/market_security.xml`, rules, ACL |
| 6 Normalized model | Done | listing/snapshot/seller/mapping/analysis/comparable |
| 7 Connector framework | Done | base + csv/xlsx/json/demo + disabled sahibinden |
| 8 Import pipeline | Done | `services/import_pipeline.py` + wizard/jobs |
| 9 History/lifecycle | Partial | snapshots, removed_from_source, age metrics |
| 10 Analytics | Partial | services helpers + overview RPC + comparable scoring |
| 11 TCRM integrations | Partial | CRM lead / unit / project / sale actions |
| 12 Premium UI | Partial | OWL app shell with sections |
| 13 Dashboards | Partial | Overview KPIs in OWL (not yet Propertio dashboard widgets) |
| 14 Demo data | Done | `services/demo_seed.py` (idempotent, company-scoped) |
| 15+ Tests | Pass (23/23) | `0 failed, 0 error(s)` — geo, sahibinden public, isolation, render (tcrm.log 2026-07-23 20:11:42) |
| Public Sahibinden | Done | No CAPTCHA/auth bypass; Scrape Now + schedule; cascading TR geo filters |

## Install / test commands

```powershell
cd D:\tcrm
$env:PYTHONPATH = "D:\tcrm\tcrm-src"
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -i tcrm_market_analysis --stop-after-init
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master --test-enable --test-tags=tcrm_market_analysis --stop-after-init
```
