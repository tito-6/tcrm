import base64
import json
import uuid

from tcrm.addons.tcrm_propertio.reports.report_definitions import ProjectProfitabilityReport


def _pick_isolated_users(env):
    users = env["res.users"].sudo().search([
        ("active", "=", True),
        ("share", "=", False),
        ("id", ">", 2),
        ("company_id", "!=", False),
    ])
    for user_a in users:
        for user_b in users:
            if user_a.id == user_b.id:
                continue
            if user_a.company_id.id == user_b.company_id.id:
                continue
            if user_a.company_id.id in user_b.company_ids.ids:
                continue
            if user_b.company_id.id in user_a.company_ids.ids:
                continue
            return user_a, user_b
    return False, False


def run_redteam(env):
    user_a, user_b = _pick_isolated_users(env)
    if not user_a or not user_b:
        print(json.dumps({
            "ok": False,
            "error": "Could not find two tenant users with isolated company access.",
        }, indent=2))
        return

    marker = f"REDTEAM-PROJ-{uuid.uuid4().hex[:8].upper()}"
    project = False
    try:
        project = env["propertio.project"].sudo().with_company(user_a.company_id).create({
            "name": marker,
            "city": "Istanbul",
            "company_id": user_a.company_id.id,
        })

        # Baseline visibility in owner tenant.
        a_can_read = bool(
            env["propertio.project"]
            .with_user(user_a)
            .with_company(user_a.company_id)
            .search_count([("id", "=", project.id)])
        )

        # Direct cross-tenant read attempt.
        b_can_read_direct = bool(
            env["propertio.project"]
            .with_user(user_b)
            .with_company(user_b.company_id)
            .search_count([("id", "=", project.id)])
        )

        # Crafted domain attack attempt (explicitly targeting tenant A company).
        b_can_read_crafted = bool(
            env["propertio.project"]
            .with_user(user_b)
            .with_company(user_b.company_id)
            .search_count([("id", "=", project.id), ("company_id", "=", user_a.company_id.id)])
        )

        # Report class isolation test.
        report_env_b = (
            env["res.users"]
            .with_user(user_b)
            .with_company(user_b.company_id)
            .env
        )
        report_rows = ProjectProfitabilityReport(env=report_env_b).get_data()
        b_leak_in_report_class = any(row.get("Project") == marker for row in report_rows)

        # Unified report wizard export isolation test.
        wiz = (
            env["propertio.unified.report.wizard"]
            .with_user(user_b)
            .with_company(user_b.company_id)
            .create({"report_type": "project_profitability", "export_format": "csv"})
        )
        wiz.action_generate_report()
        csv_payload = base64.b64decode(wiz.file_data or b"").decode("utf-8", errors="ignore")
        b_leak_in_wizard_export = marker in csv_payload

        result = {
            "ok": True,
            "tenant_a_user": user_a.login,
            "tenant_a_company": user_a.company_id.name,
            "tenant_b_user": user_b.login,
            "tenant_b_company": user_b.company_id.name,
            "marker_project": marker,
            "tenant_a_can_read_marker": a_can_read,
            "tenant_b_can_read_marker_direct": b_can_read_direct,
            "tenant_b_can_read_marker_with_crafted_company_domain": b_can_read_crafted,
            "tenant_b_report_class_leak": b_leak_in_report_class,
            "tenant_b_wizard_export_leak": b_leak_in_wizard_export,
            "pass": (
                a_can_read
                and not b_can_read_direct
                and not b_can_read_crafted
                and not b_leak_in_report_class
                and not b_leak_in_wizard_export
            ),
        }
        print(json.dumps(result, indent=2))
    finally:
        if project:
            project.sudo().unlink()


if "env" in locals():
    run_redteam(env)
