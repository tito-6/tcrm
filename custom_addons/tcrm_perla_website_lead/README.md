# TCRM Perla Website Lead (`tcrm_perla_website_lead`)

Isolated addon for signed website leads from https://perlavillalari.com into the
Perla Villaları TCRM tenant only.

## Endpoint

`POST /webhook/tcrm/lead`

## Enable gate

Disabled unless tenant parameter `tcrm.public_lead.enabled` is true.

## Tenant configuration (Perla DB only)

| Parameter | Purpose |
|-----------|---------|
| `tcrm.public_lead.enabled` | Master switch (default false) |
| `tcrm.public_lead.webhook_secret` | HMAC secret (≥32 bytes); never commit |
| `tcrm.tenant_public_uuid` | UUID v4 tenant identity (provision once adminially) |
| `tcrm.public_lead.company` | XML ID or id of `res.company` |
| `tcrm.public_lead.team` | XML ID or id of `crm.team` |
| `tcrm.public_lead.salesperson` | XML ID or id of `res.users` |
| `tcrm.public_lead.stage` | XML ID or id of `crm.stage` |
| `tcrm.public_lead.source` | XML ID of `utm.source` (default module source) |
| `tcrm.public_lead.type` | `lead` or `opportunity` |

## Install

Install **only** in the database selected by `perlavillalari.tcrm.online`.

Do not install in `tcrm_master`, AKOD, or other tenants.

## Security notes

- Does not modify `/webhook/akod/lead` or `custom_crm_integration`.
- Secret and full tenant UUID must not appear in logs, git, or deployment reports.
- Integration request ACL is limited to `Perla Website Lead Integration Admin`.
