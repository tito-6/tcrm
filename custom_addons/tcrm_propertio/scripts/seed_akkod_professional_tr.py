# -*- coding: utf-8 -*-
"""AK KOD şirketi için gerçekçi Türkçe operasyonel Propertio verisi.

Çalıştırma (tcrm shell):
  exec(open(r'd:\\tcrm\\custom_addons\\tcrm_propertio\\scripts\\seed_akkod_professional_tr.py', encoding='utf-8').read())
"""
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

MARK = "AKKOD_TR"
today = date.today()


def S(model):
    return env[model].sudo().with_context(
        propertio_audit_skip=True,
        propertio_financial_internal=True,
        tracking_disable=True,
        mail_create_nolog=True,
        mail_notrack=True,
        no_reset_password=True,
    )


def find_or_create(model, domain, vals):
    rec = S(model).search(domain, limit=1)
    return rec or S(model).create(vals)


company = S("res.company").search([("name", "ilike", "AK KOD")], limit=1) or env.company
print("Şirket:", company.name)

try_cur = S("res.currency").search([("name", "=", "TRY")], limit=1)
if try_cur and not try_cur.active:
    try_cur.active = True
# Company accounting currency may be locked (journal items); Propertio records use TRY.
currency = try_cur or company.currency_id
print("Propertio para birimi:", currency.name, currency.symbol, "(şirket muhasebe:", company.currency_id.name, ")")

# Prefer Turkish sales users
users = S("res.users").search([
    ("share", "=", False),
    ("active", "=", True),
    "|", ("company_id", "=", company.id), ("company_ids", "in", [company.id]),
    ("login", "not in", ("public", "portaltemplate")),
])
# Prefer named TR users
named = users.filtered(lambda u: any(x in (u.name or "") for x in ("Ayşe", "Mehmet", "Demir", "Yılmaz")))
sales_users = list(named[:2]) or list(users[:2]) or [env.user]
if len(sales_users) == 1:
    sales_users.append(sales_users[0])
sp1, sp2 = sales_users[0], sales_users[1]
print("Danışmanlar:", sp1.name, "/", sp2.name)

# Master data (TR)
ptype = find_or_create(
    "propertio.project.type",
    [("name", "=", "Konut"), ("company_id", "=", company.id)],
    {"name": "Konut", "company_id": company.id},
)
pstage = find_or_create(
    "propertio.project.stage",
    [("name", "=", "Satışta"), ("company_id", "=", company.id)],
    {"name": "Satışta", "sequence": 10, "company_id": company.id},
)
sstage = find_or_create(
    "propertio.sale.stage",
    [("name", "=", "Sözleşmeli"), ("company_id", "=", company.id)],
    {"name": "Sözleşmeli", "sequence": 10, "company_id": company.id},
)
cats = {}
for cname in ("1+1", "2+1", "3+1", "4+1", "Dükkan"):
    cats[cname] = find_or_create(
        "propertio.unit.category",
        [("name", "=", cname), ("company_id", "=", company.id)],
        {"name": cname, "company_id": company.id},
    )

rule = find_or_create(
    "propertio.commission.rule",
    [("name", "=", "Standart Komisyon %1,5"), ("company_id", "=", company.id)],
    {
        "name": "Standart Komisyon %1,5",
        "company_id": company.id,
        "rule_type": "flat",
        "rate_pct": 1.5,
        "active": True,
    },
)
S("propertio.commission.rule").search([
    ("company_id", "=", company.id), ("id", "!=", rule.id), ("rule_type", "=", "flat"),
]).write({"active": False})

# Agency
agency = find_or_create(
    "res.partner",
    [("ref", "=", "%s-ACENTE" % MARK)],
    {
        "name": "Başakşehir Gayrimenkul Danışmanlık A.Ş.",
        "ref": "%s-ACENTE" % MARK,
        "is_company": True,
        "phone": "+90 212 555 0140",
        "email": "info@basaksehirgm.com.tr",
        "company_id": company.id,
        "street": "Başakşehir Mah. İkitelli Cad. No:12",
        "city": "İstanbul",
        "country_id": env.ref("base.tr").id if env.ref("base.tr", raise_if_not_found=False) else False,
    },
)

CUSTOMERS = [
    ("Ahmet Kaya", "ahmet.kaya@ornekmail.com", "+90 532 411 2201", "34891234567"),
    ("Elif Öztürk", "elif.ozturk@ornekmail.com", "+90 533 620 8844", "34912345678"),
    ("Caner Arslan", "caner.arslan@ornekmail.com", "+90 505 778 3310", "35023456789"),
    ("Zeynep Aydın", "zeynep.aydin@ornekmail.com", "+90 544 190 6622", "35134567890"),
    ("Burak Çelik", "burak.celik@ornekmail.com", "+90 555 903 1145", "35245678901"),
    ("Selin Demirtaş", "selin.demirtas@ornekmail.com", "+90 530 267 8890", "35356789012"),
    ("Emre Yıldız", "emre.yildiz@ornekmail.com", "+90 536 445 7712", "35467890123"),
    ("Fatma Şahin", "fatma.sahin@ornekmail.com", "+90 542 118 9033", "35578901234"),
]
partners = []
for i, (name, email, phone, tc) in enumerate(CUSTOMERS, 1):
    partners.append(find_or_create(
        "res.partner",
        [("ref", "=", "%s-M%02d" % (MARK, i))],
        {
            "name": name,
            "ref": "%s-M%02d" % (MARK, i),
            "email": email,
            "phone": phone,
            "company_id": company.id,
            "street": "Atatürk Bulvarı No:%s" % (10 + i),
            "city": "İstanbul",
            "country_id": env.ref("base.tr").id if env.ref("base.tr", raise_if_not_found=False) else False,
            "vat": tc if False else False,  # keep clean
        },
    ))
    # TC field on sale later

# Projects
PROJECTS = [
    ("Model Sanayi Merkezi", "Başakşehir", 185000000),
    ("Bahçeşehir Residence", "Bahçeşehir", 92000000),
    ("İkitelli İş Merkezi", "İkitelli", 64000000),
]
projects = []
all_units = []
for pidx, (pname, city, gdv) in enumerate(PROJECTS):
    project = find_or_create(
        "propertio.project",
        [("name", "=", pname), ("company_id", "=", company.id)],
        {
            "name": pname,
            "city": city,
            "type_id": ptype.id,
            "stage_id": pstage.id,
            "gdv": gdv,
            "currency_id": currency.id,
            "company_id": company.id,
        },
    )
    # Refresh currency if project existed
    if project.currency_id != currency:
        project.currency_id = currency.id
    projects.append(project)
    block = find_or_create(
        "propertio.block",
        [("name", "=", "A Blok"), ("project_id", "=", project.id)],
        {"name": "A Blok", "project_id": project.id},
    )
    for floor in range(1, 5):
        for uno in range(1, 3):
            uname = "A-%s%02d" % (floor, uno)
            cat = list(cats.values())[(floor + uno + pidx) % len(cats)]
            price = 4_250_000 + pidx * 1_100_000 + floor * 380_000 + uno * 175_000
            if "Dükkan" in cat.name:
                price = int(price * 1.35)
            unit = find_or_create(
                "propertio.unit",
                [("unit_code", "=", "%s-%s-%s" % (MARK, pidx + 1, uname))],
                {
                    "name": uname,
                    "project_id": project.id,
                    "block_id": block.id,
                    "floor": str(floor),
                    "entrance": "A",
                    "view_type": ["Şehir", "Bahçe", "Cadde", "Park"][floor % 4],
                    "gross_m2": 85 + floor * 12,
                    "net_m2": 68 + floor * 10,
                    "general_gross_m2": 98 + floor * 12,
                    "balcony_m2": 10,
                    "facade": ["Kuzey", "Güney", "Doğu", "Batı"][(floor + uno) % 4],
                    "unit_code": "%s-%s-%s" % (MARK, pidx + 1, uname),
                    "tapu_ref": "TAPU-34-%s%s%s" % (pidx + 1, floor, uno),
                    "category_id": cat.id,
                    "state": "available",
                    "list_price": price,
                    "currency_id": currency.id,
                },
            )
            if unit.currency_id != currency:
                unit.currency_id = currency.id
            all_units.append(unit)

# Wipe previous MARK sales for this company to avoid duplicates on re-run
old_sales = S("propertio.sale").search([
    ("company_id", "=", company.id),
    ("contract_no", "ilike", "%s%%" % MARK),
])
if old_sales:
    # cascade related
    S("propertio.collection.task").search([("sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.cash.transaction").search([("payment_id.sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.payment").search([("sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.title.deed").search([("sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.handover").search([("sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.notary").search([("sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.service.request").search([("sale_id", "in", old_sales.ids)]).unlink()
    S("propertio.installment").search([("sale_id", "in", old_sales.ids)]).unlink()
    old_sales.unlink()
    print("Eski %s satışları temizlendi." % MARK)

# Create 8 confirmed sales with payment plans
sold_units = [u for u in all_units if u.state == "available"][:8]
sales = []
for idx, unit in enumerate(sold_units):
    partner = partners[idx % len(partners)]
    sale_date = today - relativedelta(months=(7 - idx), days=idx * 2)
    price = round(unit.list_price * (0.96 + (idx % 4) * 0.01), 2)
    sale = S("propertio.sale").create({
        "partner_id": partner.id,
        "unit_id": unit.id,
        "stage_id": sstage.id,
        "sale_price": price,
        "currency_id": currency.id,
        "agency_id": agency.id,
        "sales_person_id": sp1.id if idx % 2 == 0 else sp2.id,
        "sales_office": "Başakşehir Satış Ofisi",
        "department_name": "Konut Satış",
        "contract_no": "%s-SZL-%04d" % (MARK, 2026001 + idx),
        "contract_date": sale_date,
        "date_sale": sale_date,
        "payment_method_type": "Peşinat + Taksit",
        "customer_pid": "1%010d" % (1000000000 + idx * 137),
        "father_name": ["Ali", "Hasan", "Mustafa", "İbrahim"][idx % 4],
        "is_vip": idx in (0, 3),
        "state": "draft",
    })
    down = round(price * 0.30, 2)
    remaining = round(price - down, 2)
    n_inst = 8
    per = round(remaining / n_inst, 2)
    running = 0.0
    insts = [{
        "sale_id": sale.id,
        "name": "Peşinat",
        "date_due": sale_date,
        "amount": down,
        "type": "down_payment",
        "sequence": 1,
        "amount_paid": down,
        "date_paid": sale_date,
    }]
    for seq in range(1, n_inst + 1):
        amt = per if seq < n_inst else round(remaining - running, 2)
        running += amt
        due = sale_date + relativedelta(months=seq)
        # Leave some overdue / unpaid for collection queue
        paid = 0.0
        date_paid = False
        if seq <= 3:
            paid = amt
            date_paid = due
        elif seq == 4 and idx % 2 == 0:
            paid = round(amt * 0.4, 2)
            date_paid = due
        insts.append({
            "sale_id": sale.id,
            "name": "Taksit %s/%s" % (seq, n_inst),
            "date_due": due,
            "amount": amt,
            "type": "installment",
            "sequence": seq + 1,
            "amount_paid": paid,
            "date_paid": date_paid or False,
        })
    S("propertio.installment").create(insts)
    sale.action_confirm()
    sales.append(sale)

    # Payment for peşinat
    pay = S("propertio.payment").create({
        "partner_id": partner.id,
        "sale_id": sale.id,
        "amount": down,
        "currency_id": currency.id,
        "payment_method": "bank" if idx % 2 == 0 else "cash",
        "payment_date": sale_date,
        "receipt_no": "MK-%s-%03d" % (sale_date.strftime("%Y%m"), idx + 1),
        "exchange_rate": 1.0,
        "state": "draft",
    })
    if hasattr(pay, "action_post"):
        pay.action_post()
    else:
        pay.with_context(propertio_financial_internal=True).write({"state": "posted"})

print("Satışlar:", len(sales))

# Title deeds
for idx, sale in enumerate(sales):
    find_or_create(
        "propertio.title.deed",
        [("sale_id", "=", sale.id)],
        {
            "sale_id": sale.id,
            "tapu_no": "34/%s/%s" % (2026, 4500 + idx),
            "tapu_date": sale.date_sale + relativedelta(months=2) if idx < 4 else False,
            "tapu_type": "kat_mulkiyet" if idx % 2 == 0 else "kat_irtifak",
            "tapu_office": "Başakşehir Tapu Müdürlüğü",
            "tapu_cost": 18500 + idx * 750,
            "tapu_cost_paid": idx < 5,
            "state": ["transferred", "appointment", "pending", "transferred"][idx % 4],
            "mortgage_exists": idx % 3 == 0,
        },
    )

# Notary
for idx, sale in enumerate(sales[:6]):
    find_or_create(
        "propertio.notary",
        [("sale_id", "=", sale.id)],
        {
            "sale_id": sale.id,
            "notary_office": "%s. Noterliği / Başakşehir" % (12 + idx),
            "appointment_datetime": datetime.combine(
                sale.date_sale + timedelta(days=10), datetime.min.time()
            ) + timedelta(hours=11),
            "appointment_type": "sale" if idx % 2 == 0 else "promise_sale",
            "documents_ready": idx < 4,
            "completed": idx < 3,
            "notes": "Kimlik ve vekalet belgelerinin asılları kontrol edildi.",
        },
    )

# Handovers
for idx, sale in enumerate(sales[:6]):
    ho = find_or_create(
        "propertio.handover",
        [("sale_id", "=", sale.id)],
        {
            "sale_id": sale.id,
            "title_deed_done": idx < 3,
            "keys_handed": idx < 2,
            "handover_date": sale.date_sale + relativedelta(months=3) if idx < 3 else False,
            "state": ["done", "scheduled", "pending", "issue", "scheduled", "pending"][idx],
        },
    )
    if not ho.checklist_ids:
        S("propertio.handover.checklist").create([
            {"handover_id": ho.id, "name": "Anahtar teslimi", "done": idx < 2},
            {"handover_id": ho.id, "name": "Sayaç devir işlemleri", "done": idx < 2},
            {"handover_id": ho.id, "name": "Eksiklik tutanağı", "done": idx < 1},
        ])
    if ho.state == "issue" and not ho.issue_ids:
        S("propertio.handover.issue").create({
            "handover_id": ho.id,
            "description": "Banyo seramiklerinde çatlak tespit edildi; tadilat planlandı.",
            "priority": "high",
            "state": "in_progress",
            "assigned_to": sp2.id,
        })

# Service requests
SERVICE = [
    ("defect", "Mutfak dolabı menteşesi arızalı.", "high"),
    ("maintenance", "Klima bakımı talep edildi.", "normal"),
    ("complaint", "Ortak alan temizliği yetersiz.", "normal"),
    ("document", "İskan belgesi fotokopisi isteniyor.", "low"),
    ("info", "Aidat ödeme planı hakkında bilgi.", "low"),
]
for idx, (rtype, desc, prio) in enumerate(SERVICE):
    sale = sales[idx % len(sales)]
    find_or_create(
        "propertio.service.request",
        [("sale_id", "=", sale.id), ("description", "=", desc)],
        {
            "partner_id": sale.partner_id.id,
            "unit_id": sale.unit_id.id,
            "sale_id": sale.id,
            "request_type": rtype,
            "priority": prio,
            "description": desc,
            "assigned_to": sp1.id if idx % 2 == 0 else sp2.id,
            "deadline": today + timedelta(days=7 + idx),
            "state": ["in_progress", "new", "resolved", "new", "in_progress"][idx],
            "resolution": "İşlem tamamlandı, müşteri bilgilendirildi." if idx == 2 else False,
            "resolved_date": today - timedelta(days=2) if idx == 2 else False,
        },
    )

# Cash registers
kasa_tl = find_or_create(
    "propertio.cash.register",
    [("name", "=", "Merkez Kasa (TRY)"), ("company_id", "=", company.id)],
    {
        "name": "Merkez Kasa (TRY)",
        "company_id": company.id,
        "currency_id": currency.id,
        "responsible_id": sp1.id,
        "opening_balance": 250000,
    },
)
kasa_tl.currency_id = currency.id
# Clear and recreate a few movements
S("propertio.cash.transaction").search([("register_id", "=", kasa_tl.id)]).unlink()
pays = S("propertio.payment").search([
    ("sale_id", "in", [s.id for s in sales]),
    ("state", "=", "posted"),
], limit=6)
for p in pays:
    S("propertio.cash.transaction").create({
        "register_id": kasa_tl.id,
        "date": p.payment_date,
        "type": "in",
        "amount": p.amount,
        "reference": p.name or p.receipt_no,
        "payment_id": p.id,
        "description": "Satış tahsilatı — %s" % (p.partner_id.name or ""),
    })
S("propertio.cash.transaction").create({
    "register_id": kasa_tl.id,
    "date": today - timedelta(days=3),
    "type": "out",
    "amount": 18500,
    "reference": "GIDER-2026-014",
    "description": "Ofis kira ve aidat ödemesi",
})

# Targets (current month + year)
month_start = today.replace(day=1)
for user, t_units, t_amt in ((sp1, 4, 18_000_000), (sp2, 3, 14_500_000)):
    find_or_create(
        "propertio.target",
        [
            ("company_id", "=", company.id),
            ("user_id", "=", user.id),
            ("date_from", "=", month_start),
            ("period_type", "=", "monthly"),
        ],
        {
            "company_id": company.id,
            "user_id": user.id,
            "period_type": "monthly",
            "date_from": month_start,
            "date_to": today,
            "project_id": projects[0].id,
            "target_units": t_units,
            "target_amount": t_amt,
            "target_collection": t_amt * 0.35,
            "currency_id": currency.id,
            "state": "active",
        },
    )
year_start = today.replace(month=1, day=1)
find_or_create(
    "propertio.target",
    [
        ("company_id", "=", company.id),
        ("user_id", "=", sp1.id),
        ("period_type", "=", "yearly"),
        ("date_from", "=", year_start),
    ],
    {
        "company_id": company.id,
        "user_id": sp1.id,
        "period_type": "yearly",
        "date_from": year_start,
        "date_to": today,
        "target_units": 24,
        "target_amount": 95_000_000,
        "target_collection": 40_000_000,
        "currency_id": currency.id,
        "state": "active",
    },
)

# Commissions for Q1/Q2 style periods
S("propertio.commission").search([
    ("company_id", "=", company.id),
    ("user_id", "in", [sp1.id, sp2.id]),
]).unlink()
periods = [
    (date(today.year, 1, 1), date(today.year, 3, 31), 7500, "approved"),
    (date(today.year, 4, 1), date(today.year, 6, 30), 4200, "approved"),
    (date(today.year, 7, 1), today, 0, "draft"),
]
for user in (sp1, sp2):
    for pf, pt, ded, st in periods:
        S("propertio.commission").create({
            "company_id": company.id,
            "user_id": user.id,
            "period_from": pf,
            "period_to": pt,
            "deductions": ded,
            "currency_id": currency.id,
            "state": st if user == sp1 or st != "draft" else "draft",
        })

# Collection queue from overdue installments
S("propertio.collection.task").action_generate_tasks()
tasks = S("propertio.collection.task").search([("company_id", "=", company.id)])
for i, task in enumerate(tasks[:5]):
    task.write({
        "contact_attempts": 1 + (i % 3),
        "last_contact_date": today - timedelta(days=i + 1),
        "last_contact_result": ["promise", "no_answer", "partial", "dispute", "promise"][i % 5],
        "promise_date": today + timedelta(days=5) if i % 2 == 0 else False,
        "notes": "Müşteri ile görüşüldü; ödeme planı hatırlatıldı.",
        "next_action_date": today + timedelta(days=2 + i),
        "assigned_to": sp1.id if i % 2 == 0 else sp2.id,
    })

env.cr.commit()
print("=" * 60)
print("AK KOD profesyonel TR veri yüklendi")
print("  Projeler:", S("propertio.project").search_count([("company_id", "=", company.id)]))
print("  Satışlar:", S("propertio.sale").search_count([("company_id", "=", company.id), ("state", "=", "confirmed")]))
print("  Komisyonlar:", S("propertio.commission").search_count([("company_id", "=", company.id)]))
print("  Hedefler:", S("propertio.target").search_count([("company_id", "=", company.id)]))
print("  Tapular:", S("propertio.title.deed").search_count([("company_id", "=", company.id)]))
print("  Teslimler:", S("propertio.handover").search_count([("company_id", "=", company.id)]))
print("  Servis:", S("propertio.service.request").search_count([("company_id", "=", company.id)]))
print("  Noter:", S("propertio.notary").search_count([("company_id", "=", company.id)]))
print("  Kasalar:", S("propertio.cash.register").search_count([("company_id", "=", company.id)]))
print("  Tahsilat kuyruğu:", S("propertio.collection.task").search_count([("company_id", "=", company.id)]))
print("  Para birimi:", currency.name, currency.symbol)
print("=" * 60)
