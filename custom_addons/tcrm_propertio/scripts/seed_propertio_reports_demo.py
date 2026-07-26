# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

company = env.company
user = env.user
today = date.today()

MARK = "[TCRM DEMO]"


def find_or_create(model, domain, vals):
    rec = env[model].search(domain, limit=1)
    return rec or env[model].create(vals)


def unlink_demo(model, domain):
    recs = env[model].search(domain)
    if recs:
        recs.with_context(propertio_audit_skip=True).unlink()


# Keep this reset scoped to records created by this script.
for model, domain in [
    ("propertio.cash.transaction", [("description", "ilike", MARK)]),
    ("propertio.payment", [("receipt_no", "ilike", MARK)]),
    ("propertio.title.deed", [("tapu_no", "ilike", "TCRM-DEMO")]),
    ("propertio.commission", [("period_from", ">=", date(today.year, 1, 1))]),
    ("propertio.sale", [("contract_no", "ilike", "TCRM-DEMO")]),
    ("propertio.offer", [("notes", "ilike", MARK)]),
    ("propertio.cash.register", [("name", "ilike", MARK)]),
    ("crm.lead", [("name", "ilike", MARK)]),
    ("propertio.unit", [("unit_code", "ilike", "TCRM-DEMO")]),
    ("propertio.block", [("name", "ilike", MARK)]),
    ("propertio.project", [("name", "ilike", MARK)]),
    ("res.partner", [("ref", "=", "TCRM_DEMO")]),
]:
    if model in env:
        unlink_demo(model, domain)


usd = env.ref("base.USD", raise_if_not_found=False) or company.currency_id
eur = env.ref("base.EUR", raise_if_not_found=False) or company.currency_id
try_currency = company.currency_id

project_type = find_or_create(
    "propertio.project.type",
    [("name", "=", "Mixed Use Development"), ("company_id", "=", company.id)],
    {"name": "Mixed Use Development", "company_id": company.id},
)
stage = find_or_create(
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
for name in ["1+1", "2+1", "3+1", "4+1", "Villa", "Commercial"]:
    categories[name] = find_or_create(
        "propertio.unit.category",
        [("name", "=", name), ("company_id", "=", company.id)],
        {"name": name, "company_id": company.id},
    )

features = []
for name, icon in [
    ("Sea View", "fa-water"),
    ("Smart Home", "fa-home"),
    ("Covered Parking", "fa-car"),
    ("Pool", "fa-swimming-pool"),
    ("Concierge", "fa-bell"),
]:
    features.append(find_or_create(
        "propertio.feature",
        [("name", "=", name), ("company_id", "=", company.id)],
        {"name": name, "icon": icon, "company_id": company.id},
    ))

projects_data = [
    ("[TCRM DEMO] Istanbul Marina Residences", "Istanbul", try_currency, 1800000000),
    ("[TCRM DEMO] Bodrum Azure Villas", "Mugla", usd, 62000000),
    ("[TCRM DEMO] Ankara Finance Offices", "Ankara", eur, 48000000),
]
projects = []
for pname, city, currency, gdv in projects_data:
    project = env["propertio.project"].create({
        "name": pname,
        "city": city,
        "type_id": project_type.id,
        "stage_id": stage.id,
        "gdv": gdv,
        "currency_id": currency.id,
        "company_id": company.id,
        "standard_feature_ids": [(6, 0, [f.id for f in features[:3]])],
        "extra_feature_ids": [(6, 0, [f.id for f in features[3:]])],
    })
    projects.append(project)

customers = []
customer_names = [
    "Ayse Yilmaz", "Mehmet Demir", "Elif Kaya", "Can Arslan", "Zeynep Celik",
    "Murat Sahin", "Selin Aydin", "Omer Koc", "Derya Eren", "Kerem Aksoy",
]
for idx, name in enumerate(customer_names, start=1):
    customers.append(env["res.partner"].create({
        "name": "%s %s" % (MARK, name),
        "ref": "TCRM_DEMO",
        "email": "demo.customer.%02d@propertio.test" % idx,
        "phone": "+90 5%02d 000 %02d%02d" % (30 + idx, idx, idx),
        "company_id": company.id,
    }))

brokers = []
for name in ["Istanbul Prime Brokers", "Bodrum Coastal Realty", "Ankara Kurumsal Gayrimenkul"]:
    brokers.append(env["res.partner"].create({
        "name": "%s %s" % (MARK, name),
        "ref": "TCRM_DEMO",
        "is_company": True,
        "email": name.lower().replace(" ", ".") + "@broker.test",
        "phone": "+90 212 000 0000",
        "company_id": company.id,
    }))

units = []
for pidx, project in enumerate(projects):
    for bidx, block_name in enumerate(["A", "B", "C"], start=1):
        block = env["propertio.block"].create({
            "name": "%s Block %s" % (MARK, block_name),
            "project_id": project.id,
        })
        for floor in range(1, 4):
            for uno in range(1, 3):
                cat_name = list(categories.keys())[(pidx + bidx + floor + uno) % len(categories)]
                base_price = 3500000 + (pidx * 1800000) + (floor * 420000) + (uno * 180000)
                if cat_name == "Villa":
                    base_price *= 3
                if cat_name == "Commercial":
                    base_price *= 2
                unit = env["propertio.unit"].create({
                    "name": "%s-%s%02d" % (block_name, floor, uno),
                    "project_id": project.id,
                    "block_id": block.id,
                    "floor": str(floor),
                    "entrance": block_name,
                    "view_type": ["Sea", "City", "Garden", "Forest"][floor % 4],
                    "gross_m2": 65 + floor * 18 + uno * 9,
                    "net_m2": 52 + floor * 15 + uno * 7,
                    "general_gross_m2": 80 + floor * 20 + uno * 10,
                    "balcony_m2": 8 + uno,
                    "terrace_m2": 12 if floor == 3 else 0,
                    "garden_m2": 35 if floor == 1 and cat_name in ("Villa", "4+1") else 0,
                    "facade": ["North", "South", "East", "West"][(floor + uno) % 4],
                    "parking_no": "%s-P%s%s" % (block_name, floor, uno),
                    "parking_type": "closed" if uno == 1 else "open",
                    "unit_code": "TCRM-DEMO-%s-%s-%s-%s" % (pidx + 1, block_name, floor, uno),
                    "tapu_ref": "TAPU-DEMO-%s%s%s" % (pidx + 1, floor, uno),
                    "category_id": categories[cat_name].id,
                    "state": "available",
                    "list_price": base_price,
                    "standard_feature_ids": [(6, 0, [features[0].id, features[1].id])],
                    "extra_feature_ids": [(6, 0, [features[2].id, features[3].id])],
                })
                units.append(unit)

sales = []
sold_units = units[:18]
for idx, unit in enumerate(sold_units):
    customer = customers[idx % len(customers)]
    sale_date = date(today.year, max(1, min(12, (idx % 10) + 1)), min(24, (idx % 24) + 1))
    sale = env["propertio.sale"].create({
        "partner_id": customer.id,
        "unit_id": unit.id,
        "stage_id": sale_stage.id,
        "sale_price": unit.list_price * (0.96 + (idx % 4) * 0.01),
        "currency_id": unit.currency_id.id,
        "agency_id": brokers[idx % len(brokers)].id,
        "sales_person_id": user.id,
        "contract_no": "TCRM-DEMO-SALE-%03d" % (idx + 1),
        "contract_date": sale_date,
        "date_sale": sale_date,
        "payment_method_type": "Down Payment + Installments",
        "discount_amount": unit.list_price * 0.03,
        "rate_tcmb": 1.0 if unit.currency_id == try_currency else (32.5 if unit.currency_id == usd else 35.2),
        "state": "draft",
    })
    amount = sale.sale_price
    down = round(amount * 0.25, 2)
    remaining = amount - down
    inst_vals = [{
        "sale_id": sale.id,
        "name": "Down Payment",
        "date_due": sale_date,
        "amount": down,
        "type": "down_payment",
        "sequence": 1,
    }]
    for seq in range(1, 7):
        due = sale_date + timedelta(days=30 * seq)
        inst_vals.append({
            "sale_id": sale.id,
            "name": "Installment %s/6" % seq,
            "date_due": due,
            "amount": round(remaining / 6.0, 2),
            "type": "installment",
            "sequence": seq + 1,
        })
    env["propertio.installment"].create(inst_vals)
    sale.action_confirm()
    sales.append(sale)

payments = []
for idx, sale in enumerate(sales):
    installments = sale.installment_ids.sorted("date_due")
    pay_count = 1 + (idx % 4)
    amount = sum(installments[:pay_count].mapped("amount"))
    if idx % 5 == 0 and len(installments) > pay_count:
        amount += installments[pay_count].amount * 0.45
    payment = env["propertio.payment"].create({
        "partner_id": sale.partner_id.id,
        "sale_id": sale.id,
        "amount": amount,
        "currency_id": sale.currency_id.id,
        "payment_method": ["bank", "cash", "credit_card", "senet"][idx % 4],
        "receipt_no": "%s RCPT-%03d" % (MARK, idx + 1),
        "payment_date": sale.date_sale + timedelta(days=10 + idx),
        "exchange_rate": 1.0,
    })
    payment.action_post()
    payments.append(payment)

for unit, customer in zip(units[18:28], customers):
    env["propertio.offer"].create({
        "unit_id": unit.id,
        "partner_id": customer.id,
        "user_id": user.id,
        "offer_price": unit.list_price * 0.94,
        "date_offer": today - timedelta(days=customer.id % 20),
        "date_expiry": today + timedelta(days=14),
        "state": "draft",
        "notes": "%s active reservation/offer sample" % MARK,
    })

for idx, payment in enumerate(payments):
    register = find_or_create(
        "propertio.cash.register",
        [("name", "=", "%s Main TRY Register" % MARK), ("company_id", "=", company.id)],
        {"name": "%s Main TRY Register" % MARK, "company_id": company.id, "currency_id": company.currency_id.id, "responsible_id": user.id, "opening_balance": 250000},
    )
    env["propertio.cash.transaction"].create({
        "register_id": register.id,
        "date": payment.payment_date,
        "type": "in",
        "amount": payment.amount if payment.currency_id == register.currency_id else payment.covered_amount,
        "payment_id": payment.id,
        "reference": payment.name,
        "description": "%s collection transaction" % MARK,
    })

for idx, sale in enumerate(sales[:8]):
    env["propertio.title.deed"].create({
        "sale_id": sale.id,
        "tapu_no": "TCRM-DEMO-TAPU-%03d" % (idx + 1),
        "tapu_date": sale.date_sale + timedelta(days=60),
        "tapu_type": "kat_mulkiyet" if idx % 2 else "kat_irtifak",
        "tapu_office": ["Kadikoy", "Bodrum", "Cankaya"][idx % 3],
        "tapu_cost": sale.sale_price * 0.02,
        "tapu_cost_paid": idx % 2 == 0,
        "state": ["pending", "appointment", "transferred"][idx % 3],
    })

rule = find_or_create(
    "propertio.commission.rule",
    [("name", "=", "TCRM Demo Flat 1.5%"), ("company_id", "=", company.id)],
    {"name": "TCRM Demo Flat 1.5%", "company_id": company.id, "rule_type": "flat", "rate_pct": 1.5},
)
env["propertio.commission"].create({
    "company_id": company.id,
    "user_id": user.id,
    "period_from": date(today.year, 1, 1),
    "period_to": date(today.year, 12, 31),
    "deductions": 12500,
    "state": "approved",
})

for idx in range(24):
    lead = env["crm.lead"].create({
        "name": "%s Lead %02d - %s" % (MARK, idx + 1, ["Google Ads", "Meta", "Web Form", "Broker"][idx % 4]),
        "partner_id": customers[idx % len(customers)].id,
        "user_id": user.id,
        "expected_revenue": 2500000 + idx * 175000,
        "probability": 20 + (idx % 7) * 10,
    })
    lead.message_post(body="%s marketing/source activity sample" % MARK)

for sale in sales[:10]:
    sale.activity_schedule(
        "mail.mail_activity_data_todo",
        date_deadline=today + timedelta(days=7),
        summary="%s follow up collection / tapu workflow" % MARK,
        user_id=user.id,
    )

env.cr.commit()
print("Seeded Propertio report demo data: %s projects, %s units, %s sales, %s payments, 24 leads." % (
    len(projects), len(units), len(sales), len(payments)
))
raise SystemExit
