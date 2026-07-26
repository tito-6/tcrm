# -*- coding: utf-8 -*-
"""Full wipe of Propertio transactional data + linked mock reseed.

Run via Odoo/TCRM shell (as SUPERUSER so financial unlink is allowed):

  exec(open(r'd:\\tcrm\\custom_addons\\tcrm_propertio\\scripts\\reseed_propertio_linked_demo.py', encoding='utf-8').read())
"""
from datetime import date, datetime, timedelta
from collections import defaultdict

MARK = "TCRM_SEED"
today = date.today()


def _sudo(model_name):
    return env[model_name].sudo().with_context(
        propertio_audit_skip=True,
        propertio_financial_internal=True,
        tracking_disable=True,
        mail_create_nolog=True,
        mail_notrack=True,
        no_reset_password=True,
    )


def _exists(model_name):
    return model_name in env


def wipe_all(model_name, domain=None):
    if not _exists(model_name):
        return 0
    Model = _sudo(model_name)
    recs = Model.search(domain or [])
    count = len(recs)
    if count:
        recs.unlink()
    return count


def find_or_create(model_name, domain, vals):
    Model = _sudo(model_name)
    rec = Model.search(domain, limit=1)
    return rec or Model.create(vals)


print("=" * 72)
print("PHASE 1 — Full wipe of Propertio transactional data")
print("=" * 72)

# Collect partners used by property sales before wipe (customers + brokers)
partner_ids = set()
if _exists("propertio.sale"):
    for sale in _sudo("propertio.sale").search([]):
        if sale.partner_id:
            partner_ids.add(sale.partner_id.id)
        if sale.agency_id:
            partner_ids.add(sale.agency_id.id)
        if sale.agency_2_id:
            partner_ids.add(sale.agency_2_id.id)
if _exists("propertio.offer"):
    for offer in _sudo("propertio.offer").search([]):
        if offer.partner_id:
            partner_ids.add(offer.partner_id.id)
if _exists("propertio.payment"):
    for pay in _sudo("propertio.payment").search([]):
        if pay.partner_id:
            partner_ids.add(pay.partner_id.id)

# Also any previously seeded demo partners
demo_partners = _sudo("res.partner").search([
    "|", "|", "|",
    ("ref", "=ilike", "TCRM_SEED%"),
    ("ref", "=", "TCRM_DEMO"),
    ("name", "ilike", "[TCRM DEMO]%"),
    ("name", "ilike", "TCRM_SEED%"),
])
partner_ids.update(demo_partners.ids)

wipe_counts = {}
wipe_order = [
    ("propertio.cash.transaction", []),
    ("propertio.cash.register", []),
    ("propertio.payment.cancel.request", []),
    ("propertio.collection.task", []),
    ("propertio.handover.issue", []),
    ("propertio.handover.checklist", []),
    ("propertio.handover", []),
    ("propertio.document", []),
    ("propertio.einvoice", []),
    ("propertio.notary", []),
    ("propertio.title.deed", []),
    ("propertio.service.request", []),
    ("propertio.commission", []),
    ("propertio.target", []),
    ("propertio.revenue.period", []),
    ("propertio.offer", []),
    ("propertio.payment", []),
    ("propertio.installment", []),
    ("propertio.sale", []),
    ("propertio.unit", []),
    ("propertio.block", []),
    ("propertio.project", []),
    ("propertio.audit.log", []),
]
for model_name, domain in wipe_order:
    wipe_counts[model_name] = wipe_all(model_name, domain)

# Wipe CRM leads tied to collected partners or seed markers
lead_count = 0
if _exists("crm.lead"):
    Lead = _sudo("crm.lead")
    lead_domain = ["|", ("name", "ilike", "TCRM_SEED%"), ("name", "ilike", "[TCRM DEMO]%")]
    if partner_ids:
        lead_domain = ["|"] + lead_domain + [("partner_id", "in", list(partner_ids))]
    leads = Lead.search(lead_domain)
    lead_count = len(leads)
    if leads:
        leads.unlink()
wipe_counts["crm.lead"] = lead_count

# Delete collected partners that are not linked to users / company records
protected = set()
for user in _sudo("res.users").search([("partner_id", "!=", False)]):
    protected.add(user.partner_id.id)
for company in _sudo("res.company").search([]):
    if company.partner_id:
        protected.add(company.partner_id.id)

to_delete = [pid for pid in partner_ids if pid not in protected]
partner_deleted = 0
if to_delete:
    partners = _sudo("res.partner").browse(to_delete).exists()
    partner_deleted = len(partners)
    if partners:
        partners.unlink()
wipe_counts["res.partner(seed)"] = partner_deleted

for model_name, count in wipe_counts.items():
    if count:
        print("  wiped %-40s %s" % (model_name, count))

print("=" * 72)
print("PHASE 2 — Linked mock reseed")
print("=" * 72)

# Target companies: active SaaS tenants, else all companies
companies = _sudo("res.company").browse([])
if _exists("tcrm.tenant"):
    tenants = _sudo("tcrm.tenant").search([("active", "=", True), ("company_id", "!=", False)])
    companies = tenants.mapped("company_id")
if not companies:
    companies = _sudo("res.company").search([])

# Prefer known demo tenant companies when present
preferred_names = ["Test Agency", "Blue Horizon Realty", "Nova Estates"]
preferred = _sudo("res.company").search([("name", "in", preferred_names)])
if preferred:
    companies = (companies | preferred)

sales_login_map = {
    "Test Agency": ("agency_sales", "agency_admin"),
    "Blue Horizon Realty": ("bh_sales", "bh_admin"),
    "Nova Estates": ("nova_sales", "nova_admin"),
}

CUSTOMER_NAMES = [
    "Ayse Yilmaz", "Mehmet Demir", "Elif Kaya", "Can Arslan",
    "Zeynep Celik", "Murat Sahin", "Selin Aydin", "Omer Koc",
]
BROKER_SUFFIXES = ["Prime Brokers", "Coastal Realty"]
CAT_NAMES = ["1+1", "2+1", "3+1", "4+1", "Villa", "Commercial"]
FEATURE_DEFS = [
    ("Sea View", "fa-water"),
    ("Smart Home", "fa-home"),
    ("Covered Parking", "fa-car"),
    ("Pool", "fa-swimming-pool"),
    ("Concierge", "fa-bell"),
]
PROJECT_SPECS = [
    ("Marina Residences", "Istanbul", 950000000),
    ("Hillside Villas", "Bodrum", 420000000),
]

report = []

for company in companies:
    print("--- Seeding company: %s (id=%s) ---" % (company.name, company.id))
    env_c = env(user=env.uid, context=dict(env.context, allowed_company_ids=[company.id]))
    # keep using sudo helpers but force company defaults via vals

    logins = sales_login_map.get(company.name, ())
    sales_users = []
    for login in logins:
        user = _sudo("res.users").search([("login", "=", login)], limit=1)
        if user:
            sales_users.append(user)
    if not sales_users:
        # any internal user belonging to this company
        users = _sudo("res.users").search([
            ("share", "=", False),
            ("active", "=", True),
            "|", ("company_id", "=", company.id), ("company_ids", "in", [company.id]),
        ], limit=2)
        sales_users = list(users) or [env.user]
    if len(sales_users) == 1:
        sales_users.append(sales_users[0])
    sp1, sp2 = sales_users[0], sales_users[1]

    currency = company.currency_id

    project_type = find_or_create(
        "propertio.project.type",
        [("name", "=", "Mixed Use"), ("company_id", "=", company.id)],
        {"name": "Mixed Use", "company_id": company.id},
    )
    project_stage = find_or_create(
        "propertio.project.stage",
        [("name", "=", "Active Sales"), ("company_id", "=", company.id)],
        {"name": "Active Sales", "sequence": 10, "company_id": company.id},
    )
    sale_stage = find_or_create(
        "propertio.sale.stage",
        [("name", "=", "Contracted"), ("company_id", "=", company.id)],
        {"name": "Contracted", "sequence": 10, "company_id": company.id},
    )

    categories = {}
    for cname in CAT_NAMES:
        categories[cname] = find_or_create(
            "propertio.unit.category",
            [("name", "=", cname), ("company_id", "=", company.id)],
            {"name": cname, "company_id": company.id},
        )

    features = []
    for fname, icon in FEATURE_DEFS:
        features.append(find_or_create(
            "propertio.feature",
            [("name", "=", fname), ("company_id", "=", company.id)],
            {"name": fname, "icon": icon, "company_id": company.id},
        ))

    # Commission rule (flat 1.5%)
    rule = find_or_create(
        "propertio.commission.rule",
        [("name", "=", "%s Flat 1.5%%" % MARK), ("company_id", "=", company.id)],
        {
            "name": "%s Flat 1.5%%" % MARK,
            "company_id": company.id,
            "rule_type": "flat",
            "rate_pct": 1.5,
            "active": True,
        },
    )
    # deactivate other flat rules for this company so commission compute picks ours
    other_rules = _sudo("propertio.commission.rule").search([
        ("company_id", "=", company.id),
        ("id", "!=", rule.id),
        ("rule_type", "=", "flat"),
    ])
    if other_rules:
        other_rules.write({"active": False})

    customers = []
    for idx, name in enumerate(CUSTOMER_NAMES, start=1):
        customers.append(_sudo("res.partner").create({
            "name": "%s %s" % (MARK, name),
            "ref": "%s-C-%s-%02d" % (MARK, company.id, idx),
            "email": "seed.c%02d.company%s@propertio.test" % (idx, company.id),
            "phone": "+90 5%02d %03d %02d%02d" % (30 + (idx % 40), company.id % 1000, idx, idx),
            "company_id": company.id,
            "vergi_no": "1%09d" % (company.id * 100 + idx),
            "vergi_dairesi": ["Kadikoy", "Besiktas", "Cankaya", "Konak"][idx % 4],
        }))

    brokers = []
    for bidx, suffix in enumerate(BROKER_SUFFIXES, start=1):
        brokers.append(_sudo("res.partner").create({
            "name": "%s %s %s" % (MARK, company.name.split()[0], suffix),
            "ref": "%s-B-%s-%02d" % (MARK, company.id, bidx),
            "is_company": True,
            "email": "broker%02d.company%s@broker.test" % (bidx, company.id),
            "phone": "+90 212 500 %02d%02d" % (company.id % 100, bidx),
            "company_id": company.id,
            "vergi_no": "2%09d" % (company.id * 10 + bidx),
            "vergi_dairesi": "Large Taxpayers",
        }))

    projects = []
    units = []
    for pidx, (pname, city, gdv) in enumerate(PROJECT_SPECS):
        project = _sudo("propertio.project").create({
            "name": "%s %s — %s" % (MARK, pname, company.name),
            "city": city,
            "type_id": project_type.id,
            "stage_id": project_stage.id,
            "gdv": gdv,
            "currency_id": currency.id,
            "company_id": company.id,
            "standard_feature_ids": [(6, 0, [f.id for f in features[:3]])],
            "extra_feature_ids": [(6, 0, [f.id for f in features[3:]])],
        })
        projects.append(project)
        for block_name in ["A", "B"]:
            block = _sudo("propertio.block").create({
                "name": "%s Block %s" % (MARK, block_name),
                "project_id": project.id,
            })
            for floor in range(1, 4):
                for uno in range(1, 3):
                    cat_name = CAT_NAMES[(pidx + floor + uno) % len(CAT_NAMES)]
                    base_price = 2800000 + pidx * 900000 + floor * 350000 + uno * 150000
                    if cat_name == "Villa":
                        base_price = int(base_price * 2.4)
                    if cat_name == "Commercial":
                        base_price = int(base_price * 1.6)
                    unit = _sudo("propertio.unit").create({
                        "name": "%s-%s%02d" % (block_name, floor, uno),
                        "project_id": project.id,
                        "block_id": block.id,
                        "floor": str(floor),
                        "entrance": block_name,
                        "view_type": ["Sea", "City", "Garden", "Forest"][floor % 4],
                        "gross_m2": 70 + floor * 15 + uno * 8,
                        "net_m2": 55 + floor * 12 + uno * 6,
                        "general_gross_m2": 85 + floor * 18 + uno * 8,
                        "balcony_m2": 8 + uno,
                        "terrace_m2": 12 if floor == 3 else 0,
                        "garden_m2": 30 if floor == 1 and cat_name in ("Villa", "4+1") else 0,
                        "facade": ["North", "South", "East", "West"][(floor + uno) % 4],
                        "parking_no": "%s-P%s%s" % (block_name, floor, uno),
                        "parking_type": "closed" if uno == 1 else "open",
                        "unit_code": "%s-%s-P%s-%s-%s%s" % (MARK, company.id, pidx + 1, block_name, floor, uno),
                        "tapu_ref": "TAPU-%s-%s%s%s" % (company.id, pidx + 1, floor, uno),
                        "category_id": categories[cat_name].id,
                        "state": "available",
                        "list_price": base_price,
                        "standard_feature_ids": [(6, 0, [features[0].id, features[1].id])],
                        "extra_feature_ids": [(6, 0, [features[2].id])],
                    })
                    units.append(unit)

    sold_units = units[:12]
    available_units = units[12:]
    sales = []
    for idx, unit in enumerate(sold_units):
        customer = customers[idx % len(customers)]
        sale_date = date(today.year, max(1, min(12, (idx % 10) + 1)), min(24, (idx % 24) + 1))
        price = round(unit.list_price * (0.95 + (idx % 5) * 0.01), 2)
        sale_vals = {
            "partner_id": customer.id,
            "unit_id": unit.id,
            "stage_id": sale_stage.id,
            "sale_price": price,
            "currency_id": currency.id,
            "agency_id": brokers[idx % len(brokers)].id,
            "sales_person_id": sp1.id if idx % 2 == 0 else sp2.id,
            "sales_person_2_id": sp2.id if idx % 3 == 0 else False,
            "sales_office": "%s HQ Sales Office" % company.name,
            "department_name": "Residential Sales" if idx % 2 == 0 else "Investment Sales",
            "contact_person_id": sp1.id,
            "activity_person_id": sp2.id,
            "contract_no": "%s-SALE-%s-%03d" % (MARK, company.id, idx + 1),
            "contract_date": sale_date,
            "date_sale": sale_date,
            "payment_method_type": "Down Payment + Installments",
            "discount_amount": round(unit.list_price * 0.03, 2),
            "rate_tcmb": 1.0,
            "customer_pid": "1%010d" % (company.id * 1000 + idx),
            "is_vip": idx % 5 == 0,
            "state": "draft",
        }
        if idx % 4 == 0:
            sale_vals["agency_2_id"] = brokers[(idx + 1) % len(brokers)].id
        sale = _sudo("propertio.sale").create(sale_vals)

        down = round(price * 0.25, 2)
        remaining = round(price - down, 2)
        use_balloon = idx % 4 == 0
        balloon = round(remaining * 0.15, 2) if use_balloon else 0.0
        install_pool = round(remaining - balloon, 2)
        n_inst = 6
        per = round(install_pool / n_inst, 2)
        inst_vals = [{
            "sale_id": sale.id,
            "name": "Down Payment",
            "date_due": sale_date,
            "amount": down,
            "type": "down_payment",
            "sequence": 1,
        }]
        running = 0.0
        for seq in range(1, n_inst + 1):
            amt = per if seq < n_inst else round(install_pool - running, 2)
            running += amt
            inst_vals.append({
                "sale_id": sale.id,
                "name": "Installment %s/%s" % (seq, n_inst),
                "date_due": sale_date + timedelta(days=30 * seq),
                "amount": amt,
                "type": "installment",
                "sequence": seq + 1,
            })
        if use_balloon and balloon:
            inst_vals.append({
                "sale_id": sale.id,
                "name": "Balloon",
                "date_due": sale_date + timedelta(days=30 * (n_inst + 2)),
                "amount": balloon,
                "type": "balloon",
                "sequence": 99,
            })
        _sudo("propertio.installment").create(inst_vals)
        sale.action_confirm()
        sales.append(sale)

    payments = []
    for idx, sale in enumerate(sales):
        installments = sale.installment_ids.sorted("date_due")
        pay_count = 1 + (idx % 3)  # cover DP + 0..2 installments
        amount = sum(installments[:pay_count].mapped("amount"))
        payment = _sudo("propertio.payment").create({
            "partner_id": sale.partner_id.id,
            "sale_id": sale.id,
            "amount": amount,
            "currency_id": sale.currency_id.id,
            "payment_method": ["bank", "cash", "credit_card", "senet"][idx % 4],
            "receipt_no": "%s-RCPT-%s-%03d" % (MARK, company.id, idx + 1),
            "payment_date": sale.date_sale + timedelta(days=5 + idx),
            "exchange_rate": 1.0,
            "vat_rate": 20.0,
        })
        payment.action_post()
        payments.append(payment)

    register = _sudo("propertio.cash.register").create({
        "name": "%s Main Register — %s" % (MARK, company.name),
        "company_id": company.id,
        "currency_id": currency.id,
        "responsible_id": sp1.id,
        "opening_balance": 250000,
    })
    for payment in payments:
        _sudo("propertio.cash.transaction").create({
            "register_id": register.id,
            "date": payment.payment_date,
            "type": "in",
            "amount": payment.amount,
            "payment_id": payment.id,
            "reference": payment.name,
            "description": "%s collection for %s" % (MARK, payment.sale_id.contract_no),
        })

    # Aftersales on first half of sales
    for idx, sale in enumerate(sales[:6]):
        _sudo("propertio.title.deed").create({
            "sale_id": sale.id,
            "tapu_no": "%s-TAPU-%s-%03d" % (MARK, company.id, idx + 1),
            "tapu_date": sale.date_sale + timedelta(days=60),
            "tapu_type": "kat_mulkiyet" if idx % 2 else "kat_irtifak",
            "tapu_office": ["Kadikoy", "Bodrum", "Cankaya"][idx % 3],
            "tapu_cost": round(sale.sale_price * 0.02, 2),
            "tapu_cost_paid": idx % 2 == 0,
            "state": ["pending", "appointment", "transferred"][idx % 3],
        })
        _sudo("propertio.notary").create({
            "sale_id": sale.id,
            "notary_office": "%s Notary Office %s" % (MARK, (idx % 3) + 1),
            "appointment_datetime": datetime.combine(sale.date_sale + timedelta(days=20), datetime.min.time()) + timedelta(hours=10),
            "appointment_type": "sale",
            "documents_ready": True,
            "completed": idx % 2 == 0,
            "notes": "%s notary appointment" % MARK,
        })
        handover = _sudo("propertio.handover").create({
            "sale_id": sale.id,
            "title_deed_done": idx % 3 == 0,
            "keys_handed": False,
            "handover_date": sale.date_sale + timedelta(days=120) if idx % 3 == 0 else False,
            "state": ["pending", "scheduled", "done"][idx % 3],
        })
        _sudo("propertio.handover.checklist").create({
            "handover_id": handover.id,
            "name": "Keys & remotes",
            "done": idx % 3 == 0,
        })
        _sudo("propertio.document").create({
            "sale_id": sale.id,
            "doc_type": "contract",
            "filename": "%s-contract-%03d.pdf" % (MARK, idx + 1),
            "uploaded_by": sp1.id,
            "is_required": True,
            "verified": True,
            "verified_by": sp1.id,
            "notes": "%s sale contract checklist" % MARK,
        })
        if idx % 2 == 0:
            _sudo("propertio.service.request").create({
                "partner_id": sale.partner_id.id,
                "unit_id": sale.unit_id.id,
                "sale_id": sale.id,
                "request_type": "maintenance",
                "priority": "normal",
                "description": "%s after-sales maintenance sample for %s" % (MARK, sale.contract_no),
                "assigned_to": sp2.id,
                "deadline": today + timedelta(days=14),
            })

    # Offers on available units
    offer_count = 0
    for oidx, unit in enumerate(available_units[:6]):
        _sudo("propertio.offer").create({
            "unit_id": unit.id,
            "partner_id": customers[oidx % len(customers)].id,
            "user_id": sp1.id if oidx % 2 == 0 else sp2.id,
            "offer_price": round(unit.list_price * 0.94, 2),
            "date_offer": today - timedelta(days=oidx + 1),
            "date_expiry": today + timedelta(days=14),
            "state": "draft",
            "notes": "%s active offer/reservation" % MARK,
        })
        offer_count += 1

    # CRM leads sharing customers / salespeople — diverse Kaynak (not all Website)
    lead_n = 0
    if _exists("crm.lead"):
        source_names = [
            "Web Sitesi", "Instagram", "Facebook", "Sahibinden",
            "WhatsApp", "Sabit Hat", "Ofis / Showroom", "Referans", "Google Ads",
        ]
        source_recs = []
        for sname in source_names:
            source_recs.append(find_or_create("utm.source", [("name", "=", sname)], {"name": sname}))
        for lidx in range(8):
            _sudo("crm.lead").create({
                "name": "%s Lead %02d — %s" % (MARK, lidx + 1, company.name),
                "partner_id": customers[lidx % len(customers)].id,
                "user_id": sp1.id if lidx % 2 == 0 else sp2.id,
                "expected_revenue": 2500000 + lidx * 175000,
                "probability": 20 + (lidx % 7) * 10,
                "company_id": company.id,
                "source_id": source_recs[lidx % len(source_recs)].id,
            })
            lead_n += 1

    # Sales targets
    for user in {sp1, sp2}:
        _sudo("propertio.target").create({
            "company_id": company.id,
            "user_id": user.id,
            "period_type": "yearly",
            "date_from": date(today.year, 1, 1),
            "date_to": date(today.year, 12, 31),
            "project_id": projects[0].id,
            "target_units": 12,
            "target_amount": 25000000,
            "target_collection": 8000000,
            "currency_id": currency.id,
            "state": "active",
        })

    # Commission statements per salesperson
    for user in {sp1, sp2}:
        _sudo("propertio.commission").create({
            "company_id": company.id,
            "user_id": user.id,
            "period_from": date(today.year, 1, 1),
            "period_to": date(today.year, 12, 31),
            "deductions": 5000,
            "currency_id": currency.id,
            "state": "approved",
        })

    # Linkage verification
    bad_agency = _sudo("propertio.sale").search_count([
        ("company_id", "=", company.id), ("agency_id", "=", False),
    ])
    bad_sp = _sudo("propertio.sale").search_count([
        ("company_id", "=", company.id), ("sales_person_id", "=", False),
    ])
    sales_recs = _sudo("propertio.sale").search([("company_id", "=", company.id)])
    plan_ok = 0
    plan_bad = 0
    for sale in sales_recs:
        total = round(sum(sale.installment_ids.mapped("amount")), 2)
        if abs(total - sale.sale_price) <= 1.0:
            plan_ok += 1
        else:
            plan_bad += 1
    posted = _sudo("propertio.payment").search_count([
        ("sale_id.company_id", "=", company.id), ("state", "=", "posted"),
    ])
    dp = _sudo("propertio.installment").search_count([
        ("sale_id.company_id", "=", company.id), ("type", "=", "down_payment"),
    ])
    inst = _sudo("propertio.installment").search_count([
        ("sale_id.company_id", "=", company.id), ("type", "=", "installment"),
    ])
    balloon = _sudo("propertio.installment").search_count([
        ("sale_id.company_id", "=", company.id), ("type", "=", "balloon"),
    ])
    sold = _sudo("propertio.unit").search_count([
        ("company_id", "=", company.id), ("state", "=", "sold"),
    ])
    avail = _sudo("propertio.unit").search_count([
        ("company_id", "=", company.id), ("state", "in", ["available", "option"]),
    ])
    commissions = _sudo("propertio.commission").search([("company_id", "=", company.id)])
    comm_total = sum(commissions.mapped("gross_commission"))

    row = {
        "company": company.name,
        "projects": len(projects),
        "units": len(units),
        "sold": sold,
        "available": avail,
        "sales": len(sales),
        "down_payments": dp,
        "installments": inst,
        "balloons": balloon,
        "payments_posted": posted,
        "offers": offer_count,
        "leads": lead_n,
        "brokers": len(brokers),
        "salespersons": "%s / %s" % (sp1.login, sp2.login),
        "missing_agency": bad_agency,
        "missing_salesperson": bad_sp,
        "plan_ok": plan_ok,
        "plan_bad": plan_bad,
        "commission_gross": round(comm_total, 2),
    }
    report.append(row)
    print(
        "  projects=%(projects)s units=%(units)s sold=%(sold)s avail=%(available)s "
        "sales=%(sales)s DP=%(down_payments)s taksit=%(installments)s balloon=%(balloons)s "
        "payments=%(payments_posted)s offers=%(offers)s leads=%(leads)s "
        "missing_agency=%(missing_agency)s missing_sp=%(missing_salesperson)s "
        "plan_ok=%(plan_ok)s plan_bad=%(plan_bad)s commission=%(commission_gross)s"
        % row
    )

env.cr.commit()

print("=" * 72)
print("PHASE 3 — Verification summary")
print("=" * 72)
for row in report:
    print(
        "COMPANY: %(company)s | sales=%(sales)s | agency_ok=%(missing_agency)s==0 | "
        "sp_ok=%(missing_salesperson)s==0 | plan_ok=%(plan_ok)s plan_bad=%(plan_bad)s | "
        "SP=%(salespersons)s | commission_gross=%(commission_gross)s"
        % row
    )
print("DONE. Marker prefix: %s" % MARK)
raise SystemExit
