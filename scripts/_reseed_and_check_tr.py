# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

summary = env["tcrm.mock.builder"].build_all()
print("MOCK", summary)

print("SOURCES")
for s in env["utm.source"].search([]):
    print(" -", s.id, s.name)

print("LEADS")
for l in env["crm.lead"].search([]):
    src = l.source_id.name or "-"
    print(" -", l.type, "|", src, "|", l.name)

print("FIELDS")
for f in env["ir.model.fields"].search([
    ("model", "=", "propertio.sale"),
    ("name", "in", ["name", "sale_price", "state", "project_id", "unit_id", "partner_id"]),
]):
    print(" -", f.name, "->", f.field_description)

print("MENUS")
for m in env["ir.ui.menu"].search([("complete_name", "ilike", "Propertio")]):
    print(" -", m.complete_name)

env.cr.commit()
print("DONE")
