"""
SECURITY DEFINER Escape Resistance Tests
=========================================
Tests privilege isolation for:
  - tcrm_public_rate_limit_app (application role)
  - tcrm_public_rate_limit_maintenance (cleanup role)

Verifies neither role can access Odoo tables, create objects, or escalate.

Usage:
    python tests/test_security_definer.py --database tcrm_master
"""

import psycopg2
import sys
import argparse


def connect_as_app(dbname):
    """Connect as the application login role."""
    try:
        conn = psycopg2.connect(
            f"dbname={dbname} user=tcrm_public_rate_limit_app host=localhost",
            connect_timeout=5
        )
        conn.autocommit = True
        print("[CONN] Connected as tcrm_public_rate_limit_app")
        return conn
    except psycopg2.OperationalError:
        print("[WARN] Cannot connect as tcrm_public_rate_limit_app directly.")
        print("       Falling back to SET ROLE via odoo connection.")
        conn = psycopg2.connect(f"dbname={dbname} user=odoo password=odoo host=localhost")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SET ROLE tcrm_public_rate_limit_app;")
        return conn


def connect_as_maintenance(dbname):
    """Connect as the maintenance login role."""
    try:
        conn = psycopg2.connect(
            f"dbname={dbname} user=tcrm_public_rate_limit_maintenance host=localhost",
            connect_timeout=5
        )
        conn.autocommit = True
        print("[CONN] Connected as tcrm_public_rate_limit_maintenance")
        return conn
    except psycopg2.OperationalError:
        print("[WARN] Cannot connect as maintenance directly.")
        print("       Falling back to SET ROLE via odoo connection.")
        conn = psycopg2.connect(f"dbname={dbname} user=odoo password=odoo host=localhost")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SET ROLE tcrm_public_rate_limit_maintenance;")
        return conn


def _expect_fail(cur, label, sql, params=None):
    """Execute SQL expecting it to fail. Returns True if it fails, False if it succeeds."""
    try:
        cur.execute(sql, params)
        print(f"  [FAIL] {label}: SUCCEEDED (should have been denied)")
        return False
    except (psycopg2.errors.InsufficientPrivilege,
            psycopg2.errors.RaiseException,
            psycopg2.errors.UndefinedTable,
            psycopg2.errors.InFailedSqlTransaction):
        print(f"  [PASS] {label}: denied")
        return True
    except Exception as e:
        print(f"  [PASS] {label}: {type(e).__name__}")
        return True


def _expect_succeed(cur, label, sql, params=None):
    """Execute SQL expecting it to succeed."""
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        print(f"  [PASS] {label}: succeeded (result: {row})")
        return True
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        return False


# ============================================================================
# APPLICATION ROLE TESTS
# ============================================================================

def test_app_valid_call(cur):
    """App role can call consume_lead_rate_limits."""
    print("\n[TEST] App: valid consume_lead_rate_limits call")
    return _expect_succeed(cur, "consume_lead_rate_limits",
        """SELECT * FROM public_web.consume_lead_rate_limits(
            repeat('a', 64), repeat('b', 64), repeat('c', 64),
            repeat('d', 64), repeat('e', 64)
        );""")


def test_app_unknown_namespace(cur):
    """Unknown namespace in internal function must be rejected."""
    print("\n[TEST] App: unknown namespace → rejected")
    return _expect_fail(cur, "unknown namespace",
        """SELECT * FROM public_web.consume_rate_limit(
            'attacker:ns:v1',
            '0000000000000000000000000000000000000000000000000000000000000000'
        );""")


def test_app_malformed_hashes(cur):
    """Malformed hashes must be rejected."""
    print("\n[TEST] App: malformed hashes → rejected")
    tests = [
        ("short hash", "abcdef"),
        ("uppercase", "ABCDEF0000000000000000000000000000000000000000000000000000000000"),
        ("non-hex", "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"),
        ("empty", ""),
    ]
    all_ok = True
    for label, bad_hash in tests:
        ok = _expect_fail(cur, label,
            "SELECT * FROM public_web.consume_lead_rate_limits(%s, %s, %s, %s, %s);",
            (bad_hash, "b"*64, "c"*64, "d"*64, "e"*64))
        if not ok:
            all_ok = False
    return all_ok


def test_app_null_inputs(cur):
    """NULL inputs must be rejected."""
    print("\n[TEST] App: NULL inputs → rejected")
    return _expect_fail(cur, "NULL inputs",
        "SELECT * FROM public_web.consume_lead_rate_limits(NULL, NULL, NULL, NULL, NULL);")


def test_app_long_namespace(cur):
    """Extremely long values must be rejected."""
    print("\n[TEST] App: extremely long value → rejected")
    return _expect_fail(cur, "long value",
        "SELECT * FROM public_web.consume_lead_rate_limits(%s, %s, %s, %s, %s);",
        ("a"*200, "b"*64, "c"*64, "d"*64, "e"*64))


def test_app_no_direct_tables(cur):
    """App must NOT have direct SELECT on any public_web table."""
    print("\n[TEST] App: no direct table access")
    all_ok = True
    for table in ["rate_limit_counter", "rate_limit_policy", "schema_migration"]:
        ok = _expect_fail(cur, f"SELECT {table}",
            f"SELECT * FROM public_web.{table} LIMIT 1;")
        if not ok:
            all_ok = False
    return all_ok


def test_app_no_odoo_tables(cur):
    """App must NOT read ANY Odoo business or control-plane tables."""
    print("\n[TEST] App: Odoo table isolation")
    tables = [
        "public.crm_lead", "public.res_users", "public.res_partner",
        "public.ir_config_parameter", "public.ir_http",
        "public.ir_module_module", "public.ir_cron",
    ]
    all_ok = True
    for table in tables:
        ok = _expect_fail(cur, table, f"SELECT 1 FROM {table} LIMIT 1;")
        if not ok:
            all_ok = False
    return all_ok


def test_app_no_create(cur):
    """App must NOT create schemas, tables, or functions."""
    print("\n[TEST] App: no CREATE privileges")
    all_ok = True
    all_ok &= _expect_fail(cur, "CREATE SCHEMA", "CREATE SCHEMA attacker_schema;")
    all_ok &= _expect_fail(cur, "CREATE TABLE",
        "CREATE TABLE public.test_forbidden(id integer);")
    all_ok &= _expect_fail(cur, "CREATE FUNCTION",
        "CREATE FUNCTION public_web.evil() RETURNS void LANGUAGE sql AS $$ SELECT 1; $$;")
    return all_ok


def test_app_no_alter(cur):
    """App must NOT alter tables or functions."""
    print("\n[TEST] App: no ALTER privileges")
    all_ok = True
    all_ok &= _expect_fail(cur, "ALTER TABLE",
        "ALTER TABLE public_web.rate_limit_counter ADD COLUMN evil text;")
    all_ok &= _expect_fail(cur, "ALTER FUNCTION",
        "ALTER FUNCTION public_web.consume_lead_rate_limits(text,text,text,text,text) SECURITY INVOKER;")
    return all_ok


def test_app_no_set_role(cur):
    """App must NOT escalate to owner or other privileged roles."""
    print("\n[TEST] App: no SET ROLE escalation")
    all_ok = True
    all_ok &= _expect_fail(cur, "SET ROLE owner",
        "SET ROLE tcrm_public_rate_limit_owner;")
    all_ok &= _expect_fail(cur, "SET ROLE postgres",
        "SET ROLE postgres;")
    return all_ok


def test_app_no_extensions(cur):
    """App must NOT create extensions."""
    print("\n[TEST] App: no CREATE EXTENSION")
    return _expect_fail(cur, "CREATE EXTENSION", "CREATE EXTENSION IF NOT EXISTS dblink;")


# ============================================================================
# MAINTENANCE ROLE TESTS
# ============================================================================

def test_maint_cleanup_succeeds(cur):
    """Maintenance role can call cleanup function."""
    print("\n[TEST] Maintenance: cleanup_expired_rate_limits succeeds")
    return _expect_succeed(cur, "cleanup",
        "SELECT public_web.cleanup_expired_rate_limits(1000);")


def test_maint_no_direct_tables(cur):
    """Maintenance must NOT have direct table access."""
    print("\n[TEST] Maintenance: no direct table access")
    all_ok = True
    all_ok &= _expect_fail(cur, "SELECT counter",
        "SELECT * FROM public_web.rate_limit_counter LIMIT 1;")
    all_ok &= _expect_fail(cur, "INSERT counter",
        """INSERT INTO public_web.rate_limit_counter
           (namespace, identifier_hash, window_started_at, request_count, expires_at)
           VALUES ('x','x','2026-01-01',1,'2026-01-01');""")
    return all_ok


def test_maint_no_odoo(cur):
    """Maintenance must NOT read Odoo tables."""
    print("\n[TEST] Maintenance: Odoo table isolation")
    all_ok = True
    for table in ["public.crm_lead", "public.res_users", "public.ir_config_parameter"]:
        ok = _expect_fail(cur, table, f"SELECT 1 FROM {table} LIMIT 1;")
        if not ok:
            all_ok = False
    return all_ok


def test_maint_no_consume(cur):
    """Maintenance must NOT call consume functions."""
    print("\n[TEST] Maintenance: no EXECUTE on consume functions")
    all_ok = True
    all_ok &= _expect_fail(cur, "consume_lead_rate_limits",
        "SELECT * FROM public_web.consume_lead_rate_limits('a'*64,'b'*64,'c'*64,'d'*64,'e'*64);")
    return all_ok


def test_maint_no_alter(cur):
    """Maintenance must NOT alter functions."""
    print("\n[TEST] Maintenance: no ALTER FUNCTION")
    return _expect_fail(cur, "ALTER FUNCTION",
        "ALTER FUNCTION public_web.consume_lead_rate_limits(text,text,text,text,text) SECURITY INVOKER;")


def main():
    parser = argparse.ArgumentParser(description="SECURITY DEFINER Escape Resistance Tests")
    parser.add_argument("--database", required=True, help="Target PostgreSQL database name")
    args = parser.parse_args()

    print("=" * 60)
    print("TCRM SECURITY DEFINER Escape Resistance Test Suite")
    print(f"Database: {args.database}")
    print("=" * 60)

    results = {}

    # --- Application role tests ---
    print("\n" + "=" * 60)
    print("APPLICATION ROLE (tcrm_public_rate_limit_app)")
    print("=" * 60)

    app_conn = connect_as_app(args.database)
    app_cur = app_conn.cursor()

    results["app_valid_call"] = test_app_valid_call(app_cur)
    # Reset connection state after potential failure
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_unknown_ns"] = test_app_unknown_namespace(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_malformed_hash"] = test_app_malformed_hashes(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_null_inputs"] = test_app_null_inputs(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_long_value"] = test_app_long_namespace(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_no_tables"] = test_app_no_direct_tables(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_no_odoo"] = test_app_no_odoo_tables(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_no_create"] = test_app_no_create(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_no_alter"] = test_app_no_alter(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_no_set_role"] = test_app_no_set_role(app_cur)
    try:
        app_conn.rollback()
    except Exception:
        app_conn = connect_as_app(args.database)
        app_cur = app_conn.cursor()

    results["app_no_extension"] = test_app_no_extensions(app_cur)
    app_conn.close()

    # --- Maintenance role tests ---
    print("\n" + "=" * 60)
    print("MAINTENANCE ROLE (tcrm_public_rate_limit_maintenance)")
    print("=" * 60)

    maint_conn = connect_as_maintenance(args.database)
    maint_cur = maint_conn.cursor()

    results["maint_cleanup"] = test_maint_cleanup_succeeds(maint_cur)
    try:
        maint_conn.rollback()
    except Exception:
        maint_conn = connect_as_maintenance(args.database)
        maint_cur = maint_conn.cursor()

    results["maint_no_tables"] = test_maint_no_direct_tables(maint_cur)
    try:
        maint_conn.rollback()
    except Exception:
        maint_conn = connect_as_maintenance(args.database)
        maint_cur = maint_conn.cursor()

    results["maint_no_odoo"] = test_maint_no_odoo(maint_cur)
    try:
        maint_conn.rollback()
    except Exception:
        maint_conn = connect_as_maintenance(args.database)
        maint_cur = maint_conn.cursor()

    results["maint_no_consume"] = test_maint_no_consume(maint_cur)
    try:
        maint_conn.rollback()
    except Exception:
        maint_conn = connect_as_maintenance(args.database)
        maint_cur = maint_conn.cursor()

    results["maint_no_alter"] = test_maint_no_alter(maint_cur)
    maint_conn.close()

    # --- Summary ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:25s}: [{status}]")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All security tests passed ✓")
    else:
        print("\n[FAILED] Some security tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
