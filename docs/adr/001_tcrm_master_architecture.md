# Architecture Decision Record — ADR-001

## Classification of `tcrm_master` as Dual-Purpose Database

**Status**: Approved (with mandatory review schedule)
**Date**: 2026-08-01
**Author**: AKOD Engineering
**Decision Maker**: AKOD Engineering & TCRM Architecture Board
**ADR Version**: 2

---

## 1. Context and Problem Statement

TCRM uses a multi-tenant database architecture where each customer tenant receives
a dedicated PostgreSQL database with isolated credentials. The platform control
plane (`tcrm_master`) manages tenant provisioning, domain mappings, subscription
entitlements, and global audit logs.

Public lead ingestion on `https://tcrm.online/` requires a designated database to
store incoming CRM leads submitted through the public website contact form. A
decision is required: should AKOD's own CRM leads be stored in `tcrm_master`
(the control plane) or in a separate tenant database?

---

## 2. Decision

`tcrm_master` is explicitly classified as **both**:

1. **Platform Control Plane** — manages tenant provisioning, domain mappings,
   subscription entitlements, SaaS configuration, and global audit logs.
2. **Approved AKOD Owner-Business CRM Tenant** — serves as the primary business
   CRM tenant for AKOD (the development firm that owns and operates TCRM) to
   receive and process public website leads submitted on `tcrm.online`.

This is an **explicit exception** to strict control-plane / business-data
separation. It applies **only** to AKOD's own CRM data and increases the blast
radius of a compromise affecting `tcrm_master`.

---

## 3. Business Owner Approval

| Role | Name / Entity | Approval |
|------|--------------|----------|
| Business Owner | AKOD (TCRM Owner Entity) | **[BUSINESS OWNER SIGNATURE REQUIRED]** |
| Technical Lead | AKOD Engineering | Approved |
| Security Reviewer | TCRM Architecture Board | Approved with conditions |

**Conditions of approval**:

- This ADR must be reviewed every 6 months or upon any material change to tenant
  provisioning architecture.
- A separate AKOD tenant database must be evaluated when the platform reaches
  5+ active customer tenants or when AKOD's CRM data exceeds simple lead intake.

---

## 4. Why a Separate AKOD Tenant Database Was Not Selected

| Factor | Separate DB | tcrm_master (chosen) |
|--------|-------------|---------------------|
| Operational overhead | Additional DB, credentials, backup schedule | Zero incremental infrastructure |
| Webhook routing complexity | Requires UUID→DB resolution for AKOD's own leads | Direct insertion via signed controller |
| Development velocity | Two-DB testing matrix | Single-DB development and staging |
| Production readiness | Requires tenant provisioning of AKOD itself | Already operational |
| Blast radius | Isolated | Elevated — documented as accepted risk |

**Rationale**: At the current scale (single operator, single public website), the
operational simplicity of using `tcrm_master` outweighs the blast-radius increase.
This trade-off will be re-evaluated per the review schedule in Section 3.

---

## 5. Which CRM Data May Exist in `tcrm_master`

The following data is **permitted** in `tcrm_master`:

- `crm.lead` records originating from the AKOD public website (`tcrm.online`)
- `res.partner` records auto-created by the lead pipeline for AKOD website
  contacts
- `crm.team` records belonging to AKOD's sales organization
- AKOD's own `res.company` record (company ID used for lead assignment)
- AKOD-owned `utm.source`, `utm.medium`, `utm.campaign` records for marketing
  attribution
- Integration request audit logs (`tcrm.integration.request`)

---

## 6. Which Tenant Business Data May NEVER Exist in `tcrm_master`

The following data **must never** be stored in `tcrm_master`:

- CRM leads belonging to any customer tenant
- Customer tenant `res.partner` records (contacts, vendors, customers)
- Customer tenant financial data (invoices, payments, accounting entries)
- Customer tenant documents, attachments, or file storage
- Customer tenant `res.users` records (except AKOD's own operators)
- Customer tenant inventory, sales orders, purchase orders
- Customer tenant HR, payroll, or employee data
- Any data that would be present in a customer's dedicated tenant database

**Enforcement**: Record rules on `crm.lead` and `res.partner` restrict visibility
to the AKOD company. Tenant provisioning creates a separate database — no customer
data path writes to `tcrm_master`.

---

## 7. Company and User Separation

| Entity | Location | Purpose |
|--------|----------|---------|
| AKOD company (`res.company`) | `tcrm_master` | Owner operator company for public leads |
| AKOD CRM users (`res.users`) | `tcrm_master` | Salespeople processing AKOD leads |
| Platform admin users | `tcrm_master` | Tenant provisioning and SaaS operations |
| Customer tenant companies | Customer DB (never `tcrm_master`) | Isolated per-tenant |
| Customer tenant users | Customer DB (never `tcrm_master`) | Isolated per-tenant |

AKOD CRM users and platform admin users coexist in `tcrm_master`. CRM users are
assigned to the AKOD company and have group memberships limited to CRM operations.
Platform admin users have `base.group_system` for tenant provisioning.

---

## 8. ACL and Record-Rule Boundaries

### CRM Record Rules (applied in `tcrm_master`)

| Rule | Model | Domain | Effect |
|------|-------|--------|--------|
| Lead company filter | `crm.lead` | `[('company_id','=',user.company_id.id)]` | Users see only their company's leads |
| Lead team filter | `crm.lead` | `[('team_id','in',user.sale_team_ids.ids)]` | Salespeople see only their team's leads |
| Partner company filter | `res.partner` | `[('company_id','in',[False,user.company_id.id])]` | Standard multi-company rule |

### Public Web Schema Isolation

| Object | Access by `tcrm_public_rate_limiter` |
|--------|--------------------------------------|
| `public_web.consume_rate_limit(text,text)` | EXECUTE ✓ |
| `public_web.rate_limit_counter` | No direct access |
| `public_web.rate_limit_policy` | No direct access |
| `crm_lead` | No access |
| `res_users` | No access |
| `res_partner` | No access |
| `ir_config_parameter` | No access |
| Any Odoo table | No access |

---

## 9. Backup and Restoration Implications

Because `tcrm_master` contains both control-plane state and business CRM data:

- **Backup frequency**: Must match the more aggressive of the two requirements
  (control-plane integrity → continuous WAL archiving recommended).
- **Point-in-time recovery**: Restoring `tcrm_master` restores both tenant
  provisioning state and AKOD CRM data simultaneously. There is no way to
  restore one without the other.
- **Blast radius on corruption**: A corrupt `tcrm_master` affects both platform
  operations (tenant routing, domain mappings) and AKOD's lead pipeline.
- **Backup testing**: Quarterly restore-from-backup tests must verify both
  control-plane and CRM data integrity.
- **Separation benefit**: Migrating AKOD CRM to a separate database (Section 14)
  would allow independent backup/restore cycles.

---

## 10. Public Webhook Routing

The public lead submission flow:

```
Browser → Nginx (tcrm.online) → Next.js (127.0.0.1:3002)
    → HMAC-signed POST → Odoo (127.0.0.1:8069)
    → /webhook/akod/lead controller
    → crm.lead.create() in tcrm_master
```

- The Next.js process resolves the target database implicitly: it always sends to
  the local Odoo instance, which connects to `tcrm_master` based on `tcrm.conf`.
- The webhook controller validates the HMAC signature, tenant UUID, timestamp,
  and idempotency key before creating the lead.
- The tenant UUID (`TCRM_TENANT_PUBLIC_UUID`) is registered in the control plane
  and maps uniquely to `tcrm_master` + AKOD company.
- No tenant routing lookup is required because the public website is hard-coded
  to the owner tenant.

---

## 11. Responsible Operational Owner

| Responsibility | Owner |
|---------------|-------|
| `tcrm_master` database administration | AKOD Engineering |
| Backup schedule and testing | AKOD Engineering / DevOps |
| CRM data stewardship (leads, partners) | AKOD Business Operations |
| Platform control-plane integrity | AKOD Engineering |
| Security review of this ADR | TCRM Architecture Board |
| ADR review schedule enforcement | AKOD Engineering |

---

## 12. Control-Plane Uniqueness Enforcement

The control plane must enforce uniqueness for:

| Constraint | Scope | Enforcement |
|-----------|-------|-------------|
| Tenant public UUID | Global across all tenants | UNIQUE constraint on `tcrm.tenant.public_uuid` |
| Active domain | Global | UNIQUE constraint on `tcrm.tenant.domain` WHERE `active = true` |
| Domain → database mapping | Global | One active domain maps to exactly one database |

The webhook must remain disabled when the tenant UUID → database mapping is
inconsistent or when the tenant record is inactive.

---

## 13. Security Boundaries Summary

```
┌─────────────────────────────────────────────────┐
│                  tcrm_master DB                  │
│                                                  │
│  ┌──────────────────┐  ┌──────────────────────┐ │
│  │  Control Plane    │  │  AKOD CRM Data       │ │
│  │  ─────────────    │  │  ──────────────       │ │
│  │  tcrm.tenant      │  │  crm.lead (AKOD)     │ │
│  │  domain mappings   │  │  res.partner (AKOD)  │ │
│  │  subscriptions     │  │  crm.team (AKOD)     │ │
│  │  audit logs        │  │  utm.* (AKOD)        │ │
│  └──────────────────┘  └──────────────────────┘ │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │  public_web schema (isolated)                ││
│  │  rate_limit_counter, rate_limit_policy        ││
│  │  Owner: tcrm_public_rate_limit_owner          ││
│  │  Access: tcrm_public_rate_limiter (EXECUTE)   ││
│  └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐
│  Customer Tenant A   │  │  Customer Tenant B   │
│  (separate PG DB)    │  │  (separate PG DB)    │
│  Own credentials     │  │  Own credentials     │
│  Own company data    │  │  Own company data    │
└─────────────────────┘  └─────────────────────┘
```

---

## 14. Future Database-Separation Migration Path

When the platform reaches the re-evaluation threshold (5+ active customer tenants
or AKOD CRM scope expansion), the following migration is recommended:

1. Provision a new database `tcrm_akod` using the standard tenant provisioning
   flow.
2. Assign the `tcrm.online` domain mapping to `tcrm_akod`.
3. Migrate AKOD CRM data (`crm.lead`, `res.partner`, `crm.team`, `utm.*`) from
   `tcrm_master` to `tcrm_akod` using `pg_dump --schema-only` + data export.
4. Update `TCRM_TENANT_PUBLIC_UUID` mapping to point to `tcrm_akod`.
5. Verify webhook routing resolves to `tcrm_akod`.
6. Remove AKOD CRM data from `tcrm_master`.
7. Update this ADR to reflect the new architecture.

**Estimated effort**: 1–2 engineering days.
**Risk**: Low — uses the same provisioning path as customer tenants.

---

## 15. Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1 | 2026-08-01 | AKOD Engineering | Initial stub (29 lines) |
| 2 | 2026-08-01 | AKOD Engineering | Full ADR with all 14 required sections |
