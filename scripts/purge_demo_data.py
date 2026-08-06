#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marker/xmlid-scoped demo purge for one TCRM database.

Usage (on server, via wrapper):
  python purge_demo_data.py -c /opt/tcrm/tcrm.prod.conf -d tcrm_master

Hard rules:
  - Never search([]).unlink() on CRM/Propertio on akod_prod / perla_villalari
  - On master: only unlink fictional demo tenants (Test Agency, Blue Horizon, Nova Estates)
  - Never touch AKOD / Perla tenant registry rows
"""
from __future__ import annotations

import argparse
import logging
import sys

_logger = logging.getLogger("purge_demo_data")

KEEP_DBS = {"tcrm_master", "akod_prod", "perla_villalari"}
DEMO_TENANT_NAMES = {"Test Agency", "Blue Horizon Realty", "Nova Estates"}
DEMO_TENANT_CODES = {"test_agency", "blue_horizon", "nova_estates"}
DEMO_LOGINS = {
    "agency_admin", "agency_sales",
    "bh_admin", "bh_sales",
    "nova_admin", "nova_sales",
}
MARK = "[TCRM DEMO]"


def _safe_unlink(recs, label):
    if not recs:
        return 0
    n = len(recs)
    cr = recs.env.cr
    sp = f"sp_purge_{abs(hash(label)) % 10_000_000}"
    cr.execute(f"SAVEPOINT {sp}")
    try:
        try:
            recs.with_context(propertio_audit_skip=True, mail_notrack=True).unlink()
        except TypeError:
            recs.unlink()
        cr.execute(f"RELEASE SAVEPOINT {sp}")
        _logger.info("unlinked %s: %s", n, label)
        return n
    except Exception as exc:  # noqa: BLE001
        _logger.warning("ORM unlink failed for %s (%s): %s — archive fallback", recs._name, label, exc)
        cr.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        if "active" in recs._fields:
            recs.write({"active": False})
            _logger.info("archived %s: %s", n, label)
            return n
        _logger.error("cannot archive %s (%s) — no active field; skipping", recs._name, label)
        return 0


def _sql_delete_markers(env, table, where_sql, params, label):
    cr = env.cr
    cr.execute(f'DELETE FROM "{table}" WHERE {where_sql}', params)
    n = cr.rowcount
    _logger.info("SQL deleted %s from %s (%s)", n, table, label)
    return n


def _model_ok(env, name):
    return name in env


def purge_marker_propertio(env):
    """Marker-scoped Propertio / CRM demo rows only — children before parents."""
    counts = {}

    def search(model, domain):
        if not _model_ok(env, model):
            return None
        # drop leaves whose field is missing
        cleaned = []
        i = 0
        raw = list(domain)
        # Only support simple domains used here
        try:
            return env[model].sudo().with_context(active_test=False).search(domain)
        except ValueError as exc:
            _logger.warning("search skipped %s %s: %s", model, domain, exc)
            return env[model].browse()

    demo_sales = None
    if _model_ok(env, "propertio.sale"):
        demo_sales = search(
            "propertio.sale",
            ["|", ("contract_no", "ilike", "TCRM-DEMO"), ("contract_no", "ilike", "TCRM_SEED")],
        )

    child_specs = []
    if _model_ok(env, "propertio.cash.transaction"):
        child_specs.append(("propertio.cash.transaction", [("description", "ilike", MARK)]))
    if _model_ok(env, "propertio.payment"):
        pay_domain = ["|", ("receipt_no", "ilike", MARK), ("receipt_no", "ilike", "TCRM-DEMO")]
        if demo_sales:
            pay_domain = [
                "|", "|",
                ("receipt_no", "ilike", MARK),
                ("receipt_no", "ilike", "TCRM-DEMO"),
                ("sale_id", "in", demo_sales.ids),
            ]
        child_specs.append(("propertio.payment", pay_domain))
    if _model_ok(env, "propertio.installment") and demo_sales:
        child_specs.append(("propertio.installment", [("sale_id", "in", demo_sales.ids)]))
    if _model_ok(env, "propertio.commission") and demo_sales and "sale_id" in env["propertio.commission"]._fields:
        child_specs.append(("propertio.commission", [("sale_id", "in", demo_sales.ids)]))
    if _model_ok(env, "propertio.title.deed"):
        child_specs.append(("propertio.title.deed", [("tapu_no", "ilike", "TCRM-DEMO")]))
    if _model_ok(env, "propertio.offer"):
        child_specs.append(("propertio.offer", [("notes", "ilike", MARK)]))

    for model, domain in child_specs:
        recs = search(model, domain)
        if recs is None:
            continue
        counts[model] = _safe_unlink(recs, f"{model} cascade/marker")

    parent_specs = [
        ("propertio.sale", ["|", ("contract_no", "ilike", "TCRM-DEMO"), ("contract_no", "ilike", "TCRM_SEED")]),
        ("propertio.cash.register", [("name", "ilike", MARK)]),
        # crm.lead handled via SQL below (broken inverse table on some DBs)
        ("propertio.unit", ["|", ("unit_code", "ilike", "TCRM-DEMO"), ("unit_code", "ilike", "TCRM_SEED")]),
        ("propertio.block", ["|", ("name", "ilike", MARK), ("name", "ilike", "TCRM_SEED")]),
        ("propertio.project", ["|", ("name", "ilike", MARK), ("name", "ilike", "TCRM_SEED")]),
        ("res.partner", ["|", ("ref", "=", "TCRM_DEMO"), ("ref", "=ilike", "TCRM_SEED%")]),
    ]
    for model, domain in parent_specs:
        if not _model_ok(env, model):
            continue
        # Validate fields
        ok = True
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] not in env[model]._fields:
                ok = False
                _logger.warning("skip %s missing field %s", model, leaf[0])
                break
        if not ok:
            continue
        recs = search(model, domain)
        if recs is None:
            continue
        counts[model] = _safe_unlink(recs, f"{model} marker")

    # Marker CRM leads via SQL only (avoids broken tcrm.real.estate.payment.plan inverse)
    if _model_ok(env, "crm.lead"):
        cr = env.cr
        cr.execute("SAVEPOINT purge_crm_leads")
        try:
            counts["crm.lead"] = _sql_delete_markers(
                env,
                "crm_lead",
                "(name ILIKE %s OR name ILIKE %s)",
                [f"%{MARK}%", "TCRM_SEED%"],
                "marker crm leads",
            )
            cr.execute("RELEASE SAVEPOINT purge_crm_leads")
        except Exception as exc:  # noqa: BLE001
            _logger.warning("SQL delete crm_lead failed (%s); archiving instead", exc)
            cr.execute("ROLLBACK TO SAVEPOINT purge_crm_leads")
            cr.execute(
                "UPDATE crm_lead SET active=false "
                "WHERE (name ILIKE %s OR name ILIKE %s) AND COALESCE(active,true)=true",
                [f"%{MARK}%", "TCRM_SEED%"],
            )
            counts["crm.lead"] = cr.rowcount
            _logger.info("archived %s marker crm leads", cr.rowcount)
    return counts


def purge_market_demo(env):
    counts = {}
    model = None
    for cand in ("tcrm.market.listing", "market.listing", "tcrm.market.analysis.listing", "tcrm.market.analysis"):
        if _model_ok(env, cand):
            model = cand
            break
    if not model:
        return counts
    Model = env[model].sudo()
    domain_parts = []
    for fname in ("name", "listing_code", "external_id", "ref", "code", "title"):
        if fname in Model._fields:
            domain_parts.append((fname, "ilike", "IST-DEMO"))
            domain_parts.append((fname, "ilike", "ANKIZ-DEMO"))
            domain_parts.append((fname, "ilike", MARK))
    if not domain_parts:
        return counts
    # Build OR domain
    domain = domain_parts[0:1]
    for leaf in domain_parts[1:]:
        domain = ["|"] + domain + [leaf]
    recs = Model.with_context(active_test=False).search(domain)
    counts[model] = _safe_unlink(recs, "market demo listings")
    return counts


def purge_akkod_tr_seed(env, dbname):
    """Only remove clearly AKKOD_TR-marked seed rows — never unmarked sales."""
    counts = {}
    if dbname not in ("akod_prod", "tcrm_master"):
        return counts
    MARK_TR = "AKKOD_TR"
    specs = [
        ("propertio.sale", [("contract_no", "ilike", MARK_TR)]),
        ("propertio.payment", [("receipt_no", "ilike", MARK_TR)]),
        ("propertio.project", [("name", "ilike", MARK_TR)]),
        ("propertio.unit", [("unit_code", "ilike", MARK_TR)]),
        ("crm.lead", [("name", "ilike", MARK_TR)]),
    ]
    for model, domain in specs:
        if not _model_ok(env, model):
            continue
        recs = env[model].sudo().with_context(active_test=False).search(domain)
        counts[model] = _safe_unlink(recs, f"AKKOD_TR {model}")
    return counts


def purge_mock_xmlids(env):
    """Remove records owned by tcrm_mock_data xmlids (if module present)."""
    counts = {"ir.model.data": 0, "records": 0}
    Imd = env["ir.model.data"].sudo()
    xmlids = Imd.search([("module", "=", "tcrm_mock_data")])
    if not xmlids:
        return counts
    # Unlink records newest-dependency-first by model groups
    by_model = {}
    for xid in xmlids:
        by_model.setdefault(xid.model, Imd.browse())
        by_model[xid.model] |= xid
    # Prefer child transactional models first
    order = [
        "propertio.payment", "propertio.installment", "propertio.sale",
        "propertio.offer", "propertio.unit", "propertio.block", "propertio.project",
        "crm.lead", "sale.order", "account.move", "res.partner", "res.users",
        "res.company",
    ]
    seen = set()
    for model in order + [m for m in by_model if m not in order]:
        if model in seen or model not in by_model:
            continue
        seen.add(model)
        xids = by_model[model]
        if model not in env:
            xids.unlink()
            counts["ir.model.data"] += len(xids)
            continue
        ids = [x.res_id for x in xids if x.res_id]
        recs = env[model].sudo().with_context(active_test=False).browse(ids).exists()
        counts["records"] += _safe_unlink(recs, f"mock xmlid {model}")
        xids.unlink()
        counts["ir.model.data"] += len(xids)
    return counts


def purge_demo_tenants_master(env, dbname):
    """Master-only: remove fictional SaaS demo tenants + their demo users/companies."""
    out = {"tenants": 0, "domains": 0, "users": 0, "companies": 0}
    if dbname != "tcrm_master":
        return out
    if "tcrm.tenant" not in env:
        return out
    Tenant = env["tcrm.tenant"].sudo().with_context(active_test=False)
    domain = [("name", "in", list(DEMO_TENANT_NAMES))]
    # Optional fields — only if present on this schema version
    if "code" in Tenant._fields:
        domain = ["|", ("name", "in", list(DEMO_TENANT_NAMES)), ("code", "in", list(DEMO_TENANT_CODES))]
    tenants = Tenant.search(domain)
    # Extra safety: never touch AKOD / Perla / real keep-list DBs
    keep_db = {"akod_prod", "perla_villalari", "tcrm_master"}
    tenants = tenants.filtered(
        lambda t: (t.name or "") not in ("",)
        and "akod" not in (t.name or "").lower()
        and "perla" not in (t.name or "").lower()
        and (t.db_name or "") not in keep_db
    )
    company_ids = tenants.mapped("company_id").ids
    # Domains
    if "tcrm.tenant.domain" in env and tenants:
        domains = env["tcrm.tenant.domain"].sudo().search([("tenant_id", "in", tenants.ids)])
        out["domains"] = _safe_unlink(domains, "demo tenant domains")
    # Related SaaS rows
    for model, field in [
        ("tcrm.tenant.module", "tenant_id"),
        ("tcrm.subscription", "tenant_id"),
        ("tcrm.provisioning.job", "tenant_id"),
    ]:
        if model in env and tenants:
            recs = env[model].sudo().search([(field, "in", tenants.ids)])
            _safe_unlink(recs, model)
    out["tenants"] = _safe_unlink(tenants, "demo tenants")

    # Demo logins — archive instead of unlink (FK refs from commissions etc.)
    Users = env["res.users"].sudo().with_context(active_test=False)
    demo_users = Users.search([("login", "in", list(DEMO_LOGINS))])
    demo_users = demo_users.filtered(lambda u: u.id not in (1, 2, 3, 4, 5) and u.login not in ("admin", "public", "__system__"))
    archived = 0
    for u in demo_users:
        try:
            u.write({"active": False})
            archived += 1
        except Exception as exc:  # noqa: BLE001
            _logger.warning("could not archive demo user %s: %s", u.login, exc)
    out["users"] = archived
    _logger.info("archived demo logins: %s", archived)

    # Demo companies by exact name (only if no remaining tenant points at them)
    Companies = env["res.company"].sudo()
    for cname in DEMO_TENANT_NAMES:
        company = Companies.search([("name", "=", cname)], limit=1)
        if not company:
            continue
        still = Tenant.search([("company_id", "=", company.id)], limit=1)
        if still:
            continue
        # Archive rather than delete if unlink fails (company may be main)
        try:
            company.write({"active": False}) if "active" in company._fields else None
            out["companies"] += _safe_unlink(company, f"demo company {cname}")
        except Exception as exc:  # noqa: BLE001
            _logger.warning("could not unlink company %s: %s — archived if possible", cname, exc)
            if "active" in company._fields:
                company.write({"active": False})
    return out


def count_snapshot(env):
    snap = {}
    for model in ("crm.lead", "tcrm.tenant", "propertio.sale", "propertio.project", "res.users"):
        if model in env:
            snap[model] = env[model].sudo().with_context(active_test=False).search_count([])
    return snap


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True)
    parser.add_argument("-d", "--database", required=True)
    args = parser.parse_args()
    dbname = args.database
    if dbname not in KEEP_DBS:
        _logger.error("Refusing to purge unknown DB %s (not in keep list). Use drop path instead.", dbname)
        sys.exit(2)

    sys.path.insert(0, "/opt/tcrm/tcrm-src")
    from tcrm.tools import config
    from tcrm.modules.registry import Registry
    from tcrm import api, SUPERUSER_ID

    config.parse_config(["-c", args.config, "-d", dbname])
    registry = Registry(dbname)
    report = {"db": dbname, "before": {}, "after": {}, "actions": {}}
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        report["before"] = count_snapshot(env)
        report["actions"]["demo_tenants"] = purge_demo_tenants_master(env, dbname)
        report["actions"]["markers"] = purge_marker_propertio(env)
        report["actions"]["market"] = purge_market_demo(env)
        report["actions"]["akkod_tr"] = purge_akkod_tr_seed(env, dbname)
        report["actions"]["mock_xmlids"] = purge_mock_xmlids(env)
        env.flush_all()
        cr.commit()
        report["after"] = count_snapshot(env)

    # Safety: unmarked lead count must not drop without marker unlinks accounting
    before_leads = report["before"].get("crm.lead", 0)
    after_leads = report["after"].get("crm.lead", 0)
    marker_leads = report["actions"]["markers"].get("crm.lead", 0)
    mock_recs = report["actions"]["mock_xmlids"].get("records", 0)
    akkod_leads = report["actions"]["akkod_tr"].get("crm.lead", 0)
    expected_min = before_leads - marker_leads - akkod_leads - mock_recs
    if after_leads < expected_min:
        _logger.error(
            "SAFETY FAIL: crm.lead dropped too far before=%s after=%s expected_min=%s",
            before_leads, after_leads, expected_min,
        )
        sys.exit(3)

    import json
    print(json.dumps(report, indent=2, default=str))
    print("PURGE_OK", dbname)


if __name__ == "__main__":
    main()
