# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

Source = env["utm.source"].sudo()
Lead = env["crm.lead"].sudo()

wanted = [
    "Web Sitesi", "Instagram", "Facebook", "Sahibinden", "WhatsApp",
    "Sabit Hat", "Ofis / Showroom", "Referans", "Google Ads",
]
by_name = {}
for name in wanted:
    rec = Source.search([("name", "=", name)], limit=1)
    if not rec:
        rec = Source.create({"name": name})
    by_name[name] = rec

# Archive obsolete English-named mock leads (old xmlids left behind)
obsolete = Lead.search([
    "|", "|",
    ("name", "ilike", "Website enquiry"),
    ("name", "ilike", "Call-in -"),
    ("name", "=", "Investor bulk enquiry"),
])
if obsolete:
    obsolete.write({"active": False})
    print("ARCHIVED_OBSOLETE", len(obsolete))

# Assign rotating sources to any lead/opportunity still on Property Website / empty
cycle = list(by_name.values())
stale = Lead.search([
    "|",
    ("source_id", "=", False),
    ("source_id.name", "in", ["Property Website", "Website", "Search engine"]),
])
for i, lead in enumerate(stale):
    lead.write({"source_id": cycle[i % len(cycle)].id})
print("UPDATED_STALE", len(stale))

# Also rotate TCRM_SEED leads without a useful source
seed_leads = Lead.search([("name", "ilike", "TCRM_SEED")])
for i, lead in enumerate(seed_leads):
    lead.write({"source_id": cycle[i % len(cycle)].id})
print("UPDATED_SEED", len(seed_leads))

print("SAMPLE")
for l in Lead.search([], limit=25):
    print(" -", (l.source_id.name or "-"), "|", l.name[:60])

env.cr.commit()
print("DONE")
