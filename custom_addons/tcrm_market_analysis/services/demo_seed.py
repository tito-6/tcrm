# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Deterministic fictional demo market data. Never copies real listings."""
from __future__ import annotations

from typing import List, Dict, Any

from tcrm.exceptions import UserError

MASTER_DB_DENYLIST = {"tcrm_master"}


def refuse_master_seed(env):
    """Business seeding against the master control DB must be refused when
    invoked as an explicit cross-tenant fan-out. Multi-company demo on the
    operational DB is allowed only with an explicit company context flag.
    """
    if env.context.get("tcrm_market_allow_master_company_seed"):
        return
    if env.cr.dbname in MASTER_DB_DENYLIST and env.context.get("tcrm_market_seed_all_dbs"):
        raise UserError(
            "Refusing to seed market demo data across databases from master. "
            "Run seed on each explicit tenant database / company separately."
        )


def generate_demo_rows(scenario: str = "istanbul", company_marker: str = "A") -> List[Dict[str, Any]]:
    """Return deterministic fictional rows for import pipeline."""
    if scenario == "istanbul":
        cities = [
            ("İstanbul", "Kadıköy", "Moda", 40.984, 29.028),
            ("İstanbul", "Beşiktaş", "Levent", 41.082, 29.011),
            ("İstanbul", "Şişli", "Nişantaşı", 41.052, 28.994),
            ("İstanbul", "Üsküdar", "Acıbadem", 41.005, 29.055),
            ("İstanbul", "Bakırköy", "Ataköy", 40.980, 28.855),
        ]
        categories = [
            ("residential", "apartment"),
            ("residential", "residence"),
            ("commercial", "office"),
        ]
        base_sale = 4500000
        base_rent = 45000
        prefix = "IST-DEMO"
    else:
        cities = [
            ("Ankara", "Çankaya", "Kızılay", 39.920, 32.854),
            ("Ankara", "Yenimahalle", "Batıkent", 39.968, 32.729),
            ("İzmir", "Konak", "Alsancak", 38.436, 27.142),
            ("İzmir", "Karşıyaka", "Bostanlı", 38.463, 27.100),
        ]
        categories = [
            ("residential", "apartment"),
            ("residential", "villa"),
            ("commercial", "shop"),
        ]
        base_sale = 3200000
        base_rent = 28000
        prefix = "ANKIZ-DEMO"

    rows: List[Dict[str, Any]] = []
    n = 0
    for i, (prov, dist, neigh, lat, lng) in enumerate(cities):
        for j, (cat, sub) in enumerate(categories):
            for k, tx in enumerate(("sale", "rent")):
                n += 1
                price = (base_sale if tx == "sale" else base_rent) * (1 + 0.07 * i + 0.03 * j)
                # inject outlier and duplicate-ish records
                if n == 3:
                    price *= 3.5
                area = 85 + 10 * j + 5 * i
                rows.append({
                    "external_id": "%s-%s-%02d" % (prefix, company_marker[:8], n),
                    "transaction_type": tx,
                    "category": cat,
                    "subcategory": sub,
                    "title": "Fictional %s %s %s" % (prov, sub, n),
                    "province": prov,
                    "district": dist,
                    "neighborhood": neigh,
                    "latitude": lat + 0.001 * k,
                    "longitude": lng + 0.001 * j,
                    "currency": "TRY",
                    "asking_price": round(price, 2),
                    "gross_m2": area,
                    "net_m2": area * 0.85,
                    "rooms": "%s+1" % (1 + (j % 3)),
                    "bedrooms": 1 + (j % 3),
                    "bathrooms": 1,
                    "building_age": str(5 + i),
                    "floor": str(2 + k),
                    "total_floors": "12",
                    "heating": "kombi",
                    "balcony": True,
                    "elevator": True,
                    "seller_type": "agency" if n % 2 else "owner",
                    "organization_name": "Demo Agency %s" % (1 + (n % 3)) if n % 2 else "",
                    "seller_id": "ORG-%s-%s" % (company_marker[:4], 1 + (n % 3)) if n % 2 else "OWN-%s-%02d" % (company_marker[:4], n),
                    "permitted_source_url": "https://demo.tcrm.local/listings/%s" % n,
                    "media_count": 0,
                })
    # intentional near-duplicate for cluster detection
    if rows:
        dup = dict(rows[0])
        dup["external_id"] = dup["external_id"] + "-DUP"
        dup["title"] = dup["title"] + " (dup)"
        rows.append(dup)
    # removed-lifecycle companion is handled after import by seeder
    return rows


def seed_company_demo(env, company, scenario="istanbul"):
    """Idempotent company-scoped demo seed."""
    refuse_master_seed(env)
    Source = env["tcrm.market.source"].sudo()
    Job = env["tcrm.market.import.job"].sudo()

    source = Source.search([
        ("company_id", "=", company.id),
        ("source_type", "=", "demo"),
        ("name", "=", "Fictional Demo — %s" % scenario),
    ], limit=1)
    if not source:
        source = Source.create({
            "name": "Fictional Demo — %s" % scenario,
            "source_type": "demo",
            "company_id": company.id,
            "authorization_state": "authorized",
            "state": "enabled",
            "health": "healthy",
        })
    else:
        source.write({"state": "enabled", "authorization_state": "authorized", "kill_switch": False})

    job = Job.create({
        "source_id": source.id,
        "company_id": company.id,
        "job_type": "demo_seed",
        "tenant_db_name": env.cr.dbname,
        "name": "Demo seed %s" % company.name,
    })
    job.action_run()

    # Mark one listing removed (not sold)
    Listing = env["tcrm.market.listing"].sudo()
    victim = Listing.search([
        ("company_id", "=", company.id),
        ("source_id", "=", source.id),
    ], order="id asc", limit=1)
    if victim:
        victim.action_mark_removed_from_source()

    # Price-change second pass for history
    active = Listing.search([
        ("company_id", "=", company.id),
        ("source_id", "=", source.id),
        ("state", "=", "active"),
    ], limit=1)
    if active:
        rows = generate_demo_rows(scenario=scenario, company_marker=company.name or "A")
        # bump first matching external
        for row in rows:
            if row["external_id"] == active.external_listing_id:
                row["asking_price"] = round(float(row["asking_price"]) * 1.08, 2)
                break
        job2 = Job.create({
            "source_id": source.id,
            "company_id": company.id,
            "job_type": "demo_seed",
            "tenant_db_name": env.cr.dbname,
            "name": "Demo reseed price change %s" % company.name,
        })
        from .import_pipeline import ImportPipeline
        ImportPipeline(env, source, job2, company_id=company.id).run(rows)

    return source
