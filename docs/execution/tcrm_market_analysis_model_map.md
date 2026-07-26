# TCRM Market Analysis — Phase 2 Existing Model Inventory

**Date:** 2026-07-23  
**Depends on:** `docs/execution/tcrm_market_analysis_inventory.md`  
**Addon:** `tcrm_market_analysis` (not yet created)

Rule: do not duplicate existing models; extend or link.

---

## Concept map

### 1. Property project

| Item | Value |
|------|-------|
| **Exact model** | `propertio.project` |
| **Addon** | `tcrm_propertio` |
| **File** | `custom_addons/tcrm_propertio/models/propertio_project.py` |
| **Reusable fields** | `name`, `company_id`, `city`, `type_id`, `stage_id`, `gdv`, `currency_id`, `block_ids`, `unit_ids`, amenity M2Ms |
| **Missing for market** | Province/district/neighborhood hierarchy; lat/lng; market category taxonomy |
| **New module relation** | `tcrm.market.comparable.set` / analysis → `project_id` Many2one; price-position from unit list prices vs market medians |

### 2. Building / block / tower / floor

| Item | Value |
|------|-------|
| **Exact model** | `propertio.block` (+ unit `floor` Char) |
| **Addon** | `tcrm_propertio` |
| **Reusable fields** | Block `name`, `project_id`, `company_id`; unit `floor`, `entrance` |
| **Missing** | Dedicated tower/floor models; total floors on building |
| **Relation** | Comparables map `floor` / `total_floors` on market listings; optional link to `block_id` |

### 3. Property unit and unit type

| Item | Value |
|------|-------|
| **Exact models** | `propertio.unit`, `propertio.unit.category`, `propertio.unit.status`, `propertio.feature` |
| **Addon** | `tcrm_propertio` |
| **Reusable fields** | Areas (`gross_m2`, `net_m2`, …), `list_price`, `state`, parking, features, `category_id`, `properties` |
| **Missing** | Rooms/bedrooms/bathrooms as first-class fields; building age; heating; furnished |
| **Relation** | Core subject for emsal: `comparable.set.unit_id` → `propertio.unit` |

### 4. Geographic location

| Item | Value |
|------|-------|
| **Exact model** | Soft: `propertio.project.city` Char; tenant lat/lng on `tcrm.tenant`; partner address fields on `res.partner` |
| **Missing** | Normalized country/province/district/neighborhood models for market |
| **Relation** | **New** mapping/location fields on `tcrm.market.listing` + taxonomy map models (do not invent global geo DB in master) |

### 5. Broker / agency

| Item | Value |
|------|-------|
| **Exact model** | `res.partner` (`is_company=True`), linked as `propertio.sale.agency_id` / `agency_2_id` |
| **Addon** | `base` + `tcrm_propertio` |
| **Reusable** | Partner identity, company_id rules |
| **Missing** | Market seller identity separate from CRM contacts |
| **Relation** | Manual link `tcrm.market.seller.partner_id` → `res.partner` (never auto-create from scraped private data) |

### 6. Owner / contact

| Item | Value |
|------|-------|
| **Exact model** | `res.partner` |
| **Relation** | Analysis ownership via `user_id` / `company_id`; do not store private listing phones/emails |

### 7. Lead / opportunity

| Item | Value |
|------|-------|
| **Exact model** | `crm.lead` |
| **Addon** | `crm` + inherit `tcrm_propertio/models/crm_lead_inherit.py` |
| **Reusable** | `propertio_project_id`, `propertio_unit_id`, `propertio_sale_ids`, priority stars |
| **Relation** | Action: open market analysis with prefilled location/category/budget; attach saved analysis |

### 8. Quotation / sale

| Item | Value |
|------|-------|
| **Exact model** | `propertio.sale` (contract), `propertio.offer` (offer) |
| **Reusable** | `sale_price`, `unit_id`, `opportunity_id`, agencies, payment plan |
| **Missing** | Separate “quotation” model — offers fill that role |
| **Relation** | Attach analysis snapshot to sale/offer; never auto-mutate contractual prices |

### 9. Reservation

| Item | Value |
|------|-------|
| **Exact model** | Unit `state='option'` + offers; no dedicated reservation model found |
| **Relation** | Optional context only |

### 10. Payment plan / installment

| Item | Value |
|------|-------|
| **Exact models** | `propertio.installment`, `propertio.payment` |
| **Relation** | Out of scope for market metrics; no duplication |

### 11. Valuation / comparables

| Item | Value |
|------|-------|
| **Exact model** | **None** as persistent comparable workspace |
| **Related** | Report key `valuation_gedas_readiness` in `propertio.report.engine` / report center (readiness score, not emsal set) |
| **Relation** | **New** `tcrm.market.comparable.set` + `.line` |

### 12. External listing

| Item | Value |
|------|-------|
| **Exact model** | **None** |
| **Relation** | **New** `tcrm.market.listing` + snapshots |

### 13. Import job

| Item | Value |
|------|-------|
| **Exact model** | **None** for market feeds |
| **Precedents** | Wizards under `tcrm_propertio/wizard/`; vector sync queue |
| **Relation** | **New** `tcrm.market.import.job` + source + sync job |

### 14. Dashboard metric

| Item | Value |
|------|-------|
| **Exact models** | OWL dashboards (`propertio.dashboard`, SaaS command center); `propertio.report.engine` |
| **Relation** | Extend with market KPI client actions / RPC — do not build a parallel dashboard platform |

---

## Models the new module must create (gap list)

| Model | Purpose |
|-------|---------|
| `tcrm.market.source` | Authorized source registry + capabilities + health |
| `tcrm.market.import.job` | Import/sync job tracking |
| `tcrm.market.listing` | Normalized listing identity |
| `tcrm.market.listing.snapshot` | Historical observations |
| `tcrm.market.seller` | Organization-level / pseudonymous sellers |
| `tcrm.market.map.*` (or unified mapping lines) | Taxonomy mapping |
| `tcrm.market.analysis` | Saved analyses |
| `tcrm.market.comparable.set` | Comparable workspace |
| `tcrm.market.comparable.line` | Comparable rows |
| `tcrm.market.sync.job` (optional alias of import job type) | Sync runs |

---

## Dependency recommendation

```
depends: ['base', 'web', 'mail', 'crm', 'tcrm_propertio']
```

Do **not** depend on `tcrm_saas_core` for tenant-DB install (SaaS core is master control plane and depends on propertio). Market module installs in tenant/operational DBs beside Propertio/CRM.

Optional soft integration with SaaS entitlements later via package module list once the app exists.

---

## Phase 2 gate

Document complete. Proceed to Phase 3–4 source architecture + addon skeleton.
