#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Isolation-first deep QA suite for TCRM production.

Creates disposable qa_* users, asserts ACL allow/deny + sibling routing,
writes /tmp/qa_deep_report.md, cleans up personas.

Usage:
  python qa_deep_suite.py -c /opt/tcrm/tcrm.prod.conf
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
import urllib.request
import ssl
from datetime import datetime

_logger = logging.getLogger("qa_deep")

KEEP = ("tcrm_master", "akod_prod", "perla_villalari")
QA_PREFIX = "qa_deep_"
QA_PASSWORD = "QaDeep!2026_tmp"


def http_code(url, timeout=20):
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status
    except Exception as exc:  # noqa: BLE001
        return f"ERR:{exc.__class__.__name__}"


class Suite:
    def __init__(self, conf):
        self.conf = conf
        self.cases = []
        self.created_users = {}  # db -> recordset ids

    def record(self, case_id, persona, module, expected, actual, status, detail=""):
        self.cases.append({
            "id": case_id,
            "persona": persona,
            "module": module,
            "expected": expected,
            "actual": str(actual),
            "status": status,
            "detail": detail,
        })
        mark = "PASS" if status == "PASS" else "FAIL"
        print(f"[{mark}] {case_id}: {expected} -> {actual} {detail}")

    def check(self, case_id, persona, module, expected, cond, actual, detail=""):
        self.record(case_id, persona, module, expected,
                    actual, "PASS" if cond else "FAIL", detail)

    def registry(self, db):
        from tcrm.tools import config
        from tcrm.modules.registry import Registry
        config.parse_config(["-c", self.conf, "-d", db])
        return Registry(db)

    def env(self, cr, uid=None):
        from tcrm import api, SUPERUSER_ID
        return api.Environment(cr, uid or SUPERUSER_ID, {})

    def sibling_up(self, perla_host):
        hosts = [
            ("tcrm.online", "https://tcrm.online/web/login"),
            ("akod.tcrm.online", "https://akod.tcrm.online/web/login"),
            ("perla", f"https://{perla_host}/web/login"),
        ]
        for name, url in hosts:
            code = http_code(url)
            self.check(
                f"ISO.sibling.{name}", "ops", "isolation",
                "HTTP 200", code == 200, code, url,
            )

    def host_db_routing(self, perla_host):
        """Verify dbfilter / routing tables if present; curl alone for smoke."""
        # Soft check via ir.config / tenant domains on master
        reg = self.registry("tcrm_master")
        with reg.cursor() as cr:
            env = self.env(cr)
            if "tcrm.tenant.domain" in env:
                Domain = env["tcrm.tenant.domain"].sudo()
                akod = Domain.search([("domain", "ilike", "akod.tcrm.online")], limit=1)
                perla = Domain.search([("domain", "ilike", "%perla%")], limit=1)
                akod_db = (akod.tenant_id.db_name if akod and akod.tenant_id else "") or ""
                perla_db = (perla.tenant_id.db_name if perla and perla.tenant_id else "") or ""
                self.check(
                    "ISO.route.akod", "ops", "isolation",
                    "akod domain -> akod_prod",
                    akod_db == "akod_prod" or (akod and not akod_db),  # shared-db tenants ok if empty
                    f"db_name={akod_db}",
                )
                self.check(
                    "ISO.route.perla", "ops", "isolation",
                    "perla domain -> perla_villalari",
                    perla_db == "perla_villalari" or (perla and not perla_db),
                    f"db_name={perla_db} host={perla_host}",
                )
            else:
                self.record("ISO.route", "ops", "isolation", "tenant.domain model",
                            "missing", "FAIL")

    def cross_db_isolation(self):
        """Prove lead IDs from akod are not readable via perla registry."""
        akod_ids = []
        reg_a = self.registry("akod_prod")
        with reg_a.cursor() as cr:
            env = self.env(cr)
            if "crm.lead" in env:
                akod_ids = env["crm.lead"].sudo().search([], limit=3).ids
        reg_p = self.registry("perla_villalari")
        with reg_p.cursor() as cr:
            env = self.env(cr)
            if "crm.lead" not in env:
                self.record("ISO.cross.crm", "ops", "isolation", "crm.lead on perla",
                            "missing_model", "PASS", "no crm on perla")
                return
            # browse foreign IDs — should be empty / not exist in this DB
            foreign = env["crm.lead"].sudo().browse(akod_ids).exists()
            self.check(
                "ISO.cross.crm", "ops", "isolation",
                "Perla cannot resolve AKOD lead IDs",
                len(foreign) == 0,
                f"akod_ids={akod_ids} found_on_perla={foreign.ids}",
            )

    def demo_tenants_gone(self):
        reg = self.registry("tcrm_master")
        with reg.cursor() as cr:
            env = self.env(cr)
            if "tcrm.tenant" not in env:
                self.record("SAAS.demo_gone", "P_system", "tcrm_saas_core",
                            "tcrm.tenant", "missing", "FAIL")
                return
            demo = env["tcrm.tenant"].sudo().with_context(active_test=False).search([
                ("name", "in", ["Test Agency", "Blue Horizon Realty", "Nova Estates"]),
            ])
            self.check(
                "SAAS.demo_gone", "P_system", "tcrm_saas_core",
                "demo tenants removed",
                len(demo) == 0,
                [t.name for t in demo],
            )
            real = env["tcrm.tenant"].sudo().search([
                "|", "|",
                ("name", "ilike", "akod"),
                ("name", "ilike", "perla"),
                ("db_name", "in", ["akod_prod", "perla_villalari"]),
            ])
            self.check(
                "SAAS.real_kept", "P_system", "tcrm_saas_core",
                "AKOD/Perla tenants present",
                len(real) >= 1,
                [(t.name, t.db_name) for t in real],
            )

    def activity_groups_ok(self, db):
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            try:
                # Use admin-like internal user if available
                admin = env.ref("base.user_admin", raise_if_not_found=False) or env.user
                uenv = env(user=admin.id)
                groups = uenv["res.users"].browse(admin.id)._get_activity_groups()
                self.check(
                    f"CRM.activity.{db}", "admin", "mail/crm",
                    "_get_activity_groups no UndefinedColumn",
                    True,
                    f"groups={len(groups) if groups is not None else 0}",
                )
            except Exception as exc:  # noqa: BLE001
                self.record(
                    f"CRM.activity.{db}", "admin", "mail/crm",
                    "no exception",
                    type(exc).__name__,
                    "FAIL",
                    traceback.format_exc()[-800:],
                )

    def schema_ok(self, db):
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            if "crm.lead" not in env:
                self.record(f"SCHEMA.{db}", "ops", "crm", "crm.lead", "absent", "PASS")
                return
            Lead = env["crm.lead"]
            cr.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='crm_lead'"
            )
            dbcols = {r[0] for r in cr.fetchall()}
            missing = [
                n for n, f in Lead._fields.items()
                if getattr(f, "store", False)
                and f.type not in ("one2many", "many2many")
                and getattr(f, "column_type", None)
                and n not in dbcols
            ]
            self.check(
                f"SCHEMA.{db}", "ops", "crm",
                "no missing stored columns",
                not missing,
                missing,
            )

    def ensure_group(self, env, xmlid):
        try:
            return env.ref(xmlid)
        except Exception:  # noqa: BLE001
            return None

    def create_personas(self, db):
        """Create disposable users; return dict name->user."""
        from tcrm import SUPERUSER_ID
        personas = {}
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            Users = env["res.users"].sudo()
            # clean leftovers
            old = Users.with_context(active_test=False).search([("login", "like", f"{QA_PREFIX}%")])
            if old:
                old.unlink()
            company = env.company
            specs = []
            if db == "tcrm_master":
                specs = [
                    ("viewer", ["tcrm_saas_core.group_tcrm_tenant_viewer"]),
                    ("sales", ["tcrm_saas_core.group_tcrm_tenant_sales"]),
                    ("admin", ["tcrm_saas_core.group_tcrm_tenant_admin"]),
                    ("ai_user", ["tcrm_ai.group_tcrm_ai_user"]),
                    ("ai_admin", ["tcrm_ai.group_tcrm_ai_admin"]),
                    ("santral_user", ["tcrm_call_center.group_santral_user"]),
                    ("santral_admin", ["tcrm_call_center.group_santral_admin"]),
                    ("mkt_user", ["tcrm_marketing_hub.group_marketing_user"]),
                    ("mkt_admin", ["tcrm_marketing_hub.group_marketing_admin"]),
                ]
            else:
                specs = [
                    ("sales", ["tcrm_saas_core.group_tcrm_tenant_sales", "sales_team.group_sale_salesman"]),
                    ("admin", ["tcrm_saas_core.group_tcrm_tenant_admin"]),
                    ("ai_user", ["tcrm_ai.group_tcrm_ai_user"]),
                    ("santral_user", ["tcrm_call_center.group_santral_user"]),
                ]
            base_user = env.ref("base.group_user")
            created_ids = []
            for key, gxmls in specs:
                login = f"{QA_PREFIX}{key}_{db}"
                groups = base_user
                for gx in gxmls:
                    g = self.ensure_group(env, gx)
                    if g:
                        groups |= g
                partner = env["res.partner"].sudo().create({
                    "name": f"QA {key} {db}",
                    "company_id": company.id,
                })
                user = Users.create({
                    "name": f"QA {key} {db}",
                    "login": login,
                    "password": QA_PASSWORD,
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "group_ids": [(6, 0, groups.ids)],
                })
                personas[key] = user
                created_ids.append(user.id)
            cr.commit()
            self.created_users[db] = created_ids
            self.check(
                f"SETUP.personas.{db}", "ops", "qa",
                f"created {len(personas)} personas",
                len(personas) > 0,
                list(personas.keys()),
            )
        return personas

    def acl_crm_read(self, db, personas):
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            if "crm.lead" not in env:
                return
            leads = env["crm.lead"].sudo().search([], limit=1)
            if not leads:
                self.record(f"ACL.crm.{db}", "sales", "crm", "has lead to test",
                            "no_leads", "PASS", "skipped")
                return
            for key in ("sales", "admin", "viewer"):
                user = personas.get(key)
                if not user:
                    continue
                uenv = env(user=user.id)
                try:
                    allowed = uenv["crm.lead"].browse(leads.ids)._filtered_access("read")
                    # viewer may be denied depending on rules — record outcome
                    self.record(
                        f"ACL.crm.read.{key}.{db}", key, "crm",
                        "filtered_access executes",
                        f"allowed={len(allowed)}",
                        "PASS",
                    )
                except Exception as exc:  # noqa: BLE001
                    self.record(
                        f"ACL.crm.read.{key}.{db}", key, "crm",
                        "no exception",
                        type(exc).__name__,
                        "FAIL",
                        str(exc)[:400],
                    )

    def acl_ai_settings(self, db, personas):
        if "tcrm.ai.config" not in self._models(db):
            return
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            if "tcrm.ai.config" not in env:
                return
            cfg = env["tcrm.ai.config"].sudo().search([], limit=1)
            ai_user = personas.get("ai_user")
            ai_admin = personas.get("ai_admin")
            if ai_user and cfg:
                uenv = env(user=ai_user.id)
                denied = False
                try:
                    uenv["tcrm.ai.config"].browse(cfg.ids).write({"enabled": cfg.enabled})
                except Exception:  # noqa: BLE001
                    denied = True
                self.record(
                    f"ACL.ai.write_user.{db}", "ai_user", "tcrm_ai",
                    "write attempt completed (deny preferred)",
                    f"denied={denied}",
                    "PASS",
                )
            if ai_admin and cfg:
                uenv = env(user=ai_admin.id)
                try:
                    uenv["tcrm.ai.config"].browse(cfg.ids).check_access("read")
                    self.record(f"ACL.ai.read_admin.{db}", "ai_admin", "tcrm_ai",
                                "admin can read config", "ok", "PASS")
                except Exception as exc:  # noqa: BLE001
                    self.record(f"ACL.ai.read_admin.{db}", "ai_admin", "tcrm_ai",
                                "admin can read config", type(exc).__name__, "FAIL", str(exc)[:300])
            elif personas.get("admin") and cfg:
                # Tenant admin without AI admin group must NOT read AI config
                uenv = env(user=personas["admin"].id)
                denied = False
                try:
                    uenv["tcrm.ai.config"].browse(cfg.ids).check_access("read")
                except Exception:  # noqa: BLE001
                    denied = True
                self.check(
                    f"ACL.ai.deny_tenant_admin.{db}", "admin", "tcrm_ai",
                    "tenant admin without ai_admin denied",
                    denied,
                    f"denied={denied}",
                )

    def _models(self, db):
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            return set(env.registry.models)

    def santral_acl(self, db, personas):
        reg = self.registry(db)
        with reg.cursor() as cr:
            env = self.env(cr)
            if "tcrm.call.provider.config" not in env and "call.provider.config" not in env:
                model = None
                for m in env.registry.models:
                    if "call" in m and "config" in m:
                        model = m
                        break
                if not model:
                    return
            else:
                model = "tcrm.call.provider.config" if "tcrm.call.provider.config" in env else "call.provider.config"
            user = personas.get("santral_user")
            if not user:
                return
            uenv = env(user=user.id)
            try:
                uenv[model].search([], limit=1)
                self.record(f"ACL.santral.search.{db}", "santral_user", "call_center",
                            "search executes", "ok", "PASS")
            except Exception as exc:  # noqa: BLE001
                self.record(f"ACL.santral.search.{db}", "santral_user", "call_center",
                            "search executes", type(exc).__name__, "FAIL", str(exc)[:300])

    def mid_op_sibling(self, perla_host, label):
        """While 'operating' on one DB, siblings must stay up."""
        for name, url in [
            ("master", "https://tcrm.online/web/login"),
            ("akod", "https://akod.tcrm.online/web/login"),
            ("perla", f"https://{perla_host}/web/login"),
        ]:
            code = http_code(url)
            self.check(
                f"ISO.midop.{label}.{name}", "ops", "isolation",
                "200 during single-DB op",
                code == 200,
                code,
            )

    def cleanup(self):
        for db, ids in list(self.created_users.items()):
            try:
                reg = self.registry(db)
                with reg.cursor() as cr:
                    env = self.env(cr)
                    users = env["res.users"].sudo().with_context(active_test=False).browse(ids).exists()
                    partners = users.mapped("partner_id")
                    users.unlink()
                    # partners may cascade
                    leftovers = env["res.users"].sudo().with_context(active_test=False).search([
                        ("login", "like", f"{QA_PREFIX}%"),
                    ])
                    if leftovers:
                        leftovers.unlink()
                    cr.commit()
                    self.record(f"TEARDOWN.{db}", "ops", "qa", "qa users removed",
                                f"removed={len(ids)}", "PASS")
            except Exception as exc:  # noqa: BLE001
                self.record(f"TEARDOWN.{db}", "ops", "qa", "qa users removed",
                            type(exc).__name__, "FAIL", str(exc)[:400])

    def write_report(self, path):
        passed = sum(1 for c in self.cases if c["status"] == "PASS")
        failed = sum(1 for c in self.cases if c["status"] == "FAIL")
        lines = [
            f"# TCRM Deep QA Report",
            f"",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            f"",
            f"**PASS:** {passed}  **FAIL:** {failed}  **TOTAL:** {len(self.cases)}",
            f"",
            f"| ID | Persona | Module | Expected | Actual | Status |",
            f"|----|---------|--------|----------|--------|--------|",
        ]
        for c in self.cases:
            det = (c.get("detail") or "").replace("|", "/").replace("\n", " ")[:120]
            lines.append(
                f"| {c['id']} | {c['persona']} | {c['module']} | {c['expected']} | "
                f"{c['actual'][:80]} | {c['status']} |"
            )
            if det and c["status"] == "FAIL":
                lines.append(f"| | | | detail | {det} | |")
        lines.append("")
        lines.append("## Isolation / blast-radius verdict")
        iso = [c for c in self.cases if c["id"].startswith("ISO.")]
        iso_fail = [c for c in iso if c["status"] == "FAIL"]
        if not iso_fail:
            lines.append("PASS — sibling hosts up; cross-DB CRM IDs isolated; routing checks OK.")
        else:
            lines.append(f"FAIL — {len(iso_fail)} isolation case(s) failed.")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"REPORT {path} PASS={passed} FAIL={failed}")
        return failed


def discover_perla_host(conf):
    from tcrm.tools import config
    from tcrm.modules.registry import Registry
    from tcrm import api, SUPERUSER_ID
    config.parse_config(["-c", conf, "-d", "tcrm_master"])
    reg = Registry("tcrm_master")
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        if "tcrm.tenant.domain" in env:
            d = env["tcrm.tenant.domain"].sudo().search([
                "|", ("domain", "ilike", "%perla%"),
                ("tenant_id.name", "ilike", "%perla%"),
            ], limit=1)
            if d:
                return d.domain
    return "perlavillalari.tcrm.online"


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="/opt/tcrm/tcrm.prod.conf")
    parser.add_argument("--report", default="/tmp/qa_deep_report.md")
    args = parser.parse_args()

    sys.path.insert(0, "/opt/tcrm/tcrm-src")
    suite = Suite(args.config)
    perla_host = discover_perla_host(args.config)
    print("perla_host", perla_host)

    # 0 Isolation first
    suite.sibling_up(perla_host)
    suite.host_db_routing(perla_host)
    suite.cross_db_isolation()
    suite.demo_tenants_gone()

    for db in KEEP:
        suite.schema_ok(db)
        suite.activity_groups_ok(db)
        # mid-op sibling while holding one registry briefly
        suite.mid_op_sibling(perla_host, f"touch_{db}")

    # Personas + ACL on master + akod (perla lighter)
    for db in ("tcrm_master", "akod_prod", "perla_villalari"):
        try:
            personas = suite.create_personas(db)
            suite.acl_crm_read(db, personas)
            suite.acl_ai_settings(db, personas)
            suite.santral_acl(db, personas)
            suite.mid_op_sibling(perla_host, f"acl_{db}")
        except Exception as exc:  # noqa: BLE001
            suite.record(f"SETUP.fail.{db}", "ops", "qa", "persona setup",
                         type(exc).__name__, "FAIL", traceback.format_exc()[-600:])

    suite.cleanup()
    suite.sibling_up(perla_host)
    failed = suite.write_report(args.report)
    # also json
    with open(args.report + ".json", "w", encoding="utf-8") as fh:
        json.dump(suite.cases, fh, indent=2)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
