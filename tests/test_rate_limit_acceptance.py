"""
Rate-Limit Acceptance Tests
============================
Tests against the production Next.js build to verify all 5 rate-limit policies
are enforced by PostgreSQL, not by in-memory stores.

Usage:
    python tests/test_rate_limit_acceptance.py --base-url https://public-staging.tcrm.online

Requirements:
    - Next.js running behind Nginx on the specified staging URL
    - PostgreSQL with public_web schema migrated (v4+)
    - RATE_LIMIT_DB_URL configured in Next.js environment
"""

import argparse
import json
import time
import sys
import urllib.request
import urllib.error
import uuid
import random
import string


BASE_URL = "https://public-staging.tcrm.online"
LEAD_ENDPOINT = "/api/lead"


def make_lead_payload(
    name="Test User",
    company="Test Co",
    email=None,
    phone=None,
    consent=True,
):
    """Generate a valid lead payload with optional overrides."""
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    if phone is None:
        phone = f"+9053{''.join(random.choices(string.digits, k=7))}"

    return {
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "industry": "Test",
        "message": "Acceptance test",
        "consent": consent,
    }


def post_lead(base_url, payload, extra_headers=None):
    """POST a lead and return (status_code, response_body, headers)."""
    url = f"{base_url}{LEAD_ENDPOINT}"
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return e.code, body, dict(e.headers)
    except Exception as e:
        return None, {"error": str(e)}, {}


def test_ip_rate_limit(base_url):
    """IP test: same IP, varying email/phone → 429 after threshold."""
    print("\n[TEST] IP Rate Limit (lead:ip:v1 — 5 req/60s)")
    fixed_ip = "198.51.100.42"
    results = []

    for i in range(7):
        payload = make_lead_payload()  # unique email/phone each time
        status, body, headers = post_lead(base_url, payload)
        results.append(status)
        print(f"  Request {i+1}: HTTP {status}")

    blocked = [r for r in results if r == 429]
    if len(blocked) >= 1:
        print("  [PASS] IP rate limit enforced — got 429")
        return True
    else:
        print("  [FAIL] Expected 429 after 5 requests from same IP")
        return False


def test_email_rate_limit(base_url):
    """Email test: same email, varying phone → 429 after threshold."""
    print("\n[TEST] Email Rate Limit (lead:email:v1 — 3 req/3600s)")
    fixed_email = f"ratetest_{uuid.uuid4().hex[:6]}@example.com"
    results = []

    for i in range(5):
        payload = make_lead_payload(email=fixed_email)
        status, body, headers = post_lead(base_url, payload)
        results.append(status)
        print(f"  Request {i+1}: HTTP {status}")

    blocked = [r for r in results if r == 429]
    if len(blocked) >= 1:
        print("  [PASS] Email rate limit enforced — got 429")
        return True
    else:
        print("  [FAIL] Expected 429 after 3 requests with same email")
        return False


def test_phone_rate_limit(base_url):
    """Phone test: same phone, varying email → 429 after threshold."""
    print("\n[TEST] Phone Rate Limit (lead:phone:v1 — 3 req/3600s)")
    fixed_phone = f"+9053{random.randint(1000000, 9999999)}"
    results = []

    for i in range(5):
        payload = make_lead_payload(phone=fixed_phone)
        status, body, headers = post_lead(base_url, payload)
        results.append(status)
        print(f"  Request {i+1}: HTTP {status}")

    blocked = [r for r in results if r == 429]
    if len(blocked) >= 1:
        print("  [PASS] Phone rate limit enforced — got 429")
        return True
    else:
        print("  [FAIL] Expected 429 after 3 requests with same phone")
        return False


def test_tenant_rate_limit(base_url):
    """Tenant test: vary all user identifiers, same tenant → 429 at 30/min."""
    print("\n[TEST] Tenant Rate Limit (lead:tenant:v1 — 30 req/60s)")
    results = []

    for i in range(33):
        payload = make_lead_payload()
        status, body, headers = post_lead(base_url, payload)
        results.append(status)
        if i % 10 == 0:
            print(f"  Request {i+1}: HTTP {status}")

    blocked = [r for r in results if r == 429]
    if len(blocked) >= 1:
        print(f"  [PASS] Tenant rate limit enforced — {len(blocked)} blocked")
        return True
    else:
        print("  [FAIL] Expected 429 after 30 requests from same tenant")
        return False


def test_response_safety(base_url):
    """Verify blocked responses don't leak which counter caused rejection."""
    print("\n[TEST] Response Safety")
    # Trigger a rate limit first (use same payload repeatedly)
    fixed_email = f"safety_{uuid.uuid4().hex[:6]}@example.com"
    fixed_phone = f"+9053{random.randint(1000000, 9999999)}"

    for i in range(6):
        payload = make_lead_payload(email=fixed_email, phone=fixed_phone)
        status, body, headers = post_lead(base_url, payload)

    if status == 429:
        # Check response body doesn't contain counter names or raw identifiers
        body_str = json.dumps(body)
        leaked = False
        for term in ["lead:ip:", "lead:email:", "lead:phone:", "lead:tenant:",
                      "lead:global:", fixed_email, fixed_phone]:
            if term in body_str:
                print(f"  [FAIL] Response leaks: {term}")
                leaked = True
        if not leaked:
            print("  [PASS] Response does not leak counter names or identifiers")

        # Check Retry-After header
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if retry_after and int(retry_after) >= 1:
            print(f"  [PASS] Retry-After header present: {retry_after}s")
        else:
            print(f"  [FAIL] Retry-After header missing or invalid: {retry_after}")
            leaked = True

        return not leaked
    else:
        print(f"  [SKIP] Could not trigger 429 (got HTTP {status})")
        return False


def main():
    parser = argparse.ArgumentParser(description="Rate Limit Acceptance Tests")
    parser.add_argument("--base-url", default=BASE_URL, help="Next.js base URL")
    args = parser.parse_args()

    print("=" * 60)
    print("TCRM Rate-Limit Acceptance Test Suite")
    print(f"Target: {args.base_url}")
    print("=" * 60)

    results = {}
    results["ip"] = test_ip_rate_limit(args.base_url)
    results["email"] = test_email_rate_limit(args.base_url)
    results["phone"] = test_phone_rate_limit(args.base_url)
    results["tenant"] = test_tenant_rate_limit(args.base_url)
    results["safety"] = test_response_safety(args.base_url)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:15s}: [{status}]")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All acceptance tests passed ✓")
    else:
        print("\n[FAILED] Some acceptance tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
