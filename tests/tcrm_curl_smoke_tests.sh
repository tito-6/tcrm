#!/usr/bin/env bash
# TCRM curl + JSON-RPC smoke tests.
#
# Verifies that the TCRM server is reachable, that the main application routes
# return authenticated TCRM pages (not a login/error page), and that the core
# cross-module relationships created by tcrm_mock_data are present and consistent.
#
# Usage:
#   TCRM_BASE_URL=http://localhost:8069 \
#   TCRM_DATABASE=tcrm_master \
#   TCRM_USERNAME=admin \
#   TCRM_PASSWORD=admin \
#   bash tests/tcrm_curl_smoke_tests.sh
#
# No credentials are committed; everything comes from the environment.
set -u

BASE_URL="${TCRM_BASE_URL:-http://localhost:8069}"
DB="${TCRM_DATABASE:-tcrm_master}"
USER="${TCRM_USERNAME:-admin}"
PASS="${TCRM_PASSWORD:-admin}"

COOKIES="$(mktemp)"
PASS_COUNT=0
FAIL_COUNT=0

pass() { echo "  [PASS] $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "  [FAIL] $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

cleanup() { rm -f "$COOKIES"; }
trap cleanup EXIT

echo "TCRM smoke tests against ${BASE_URL} (db=${DB})"

# --- 1. reachability --------------------------------------------------------
if curl -sSf -o /dev/null "${BASE_URL}/web/login"; then
  pass "server reachable"
else
  fail "server not reachable at ${BASE_URL}"
  echo "RESULT: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"; exit 1
fi

# --- 2. authentication ------------------------------------------------------
AUTH_PAYLOAD=$(printf '{"jsonrpc":"2.0","method":"call","params":{"db":"%s","login":"%s","password":"%s"}}' "$DB" "$USER" "$PASS")
AUTH_RESP=$(curl -sS -c "$COOKIES" -H "Content-Type: application/json" -d "$AUTH_PAYLOAD" "${BASE_URL}/web/session/authenticate")
if echo "$AUTH_RESP" | grep -q '"uid": *[0-9]'; then
  pass "authentication succeeded"
else
  fail "authentication failed: $AUTH_RESP"
  echo "RESULT: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"; exit 1
fi

# --- 3. routes --------------------------------------------------------------
check_route() {
  local route="$1"
  local body code
  body=$(curl -sS -b "$COOKIES" -w "\n%{http_code}" "${BASE_URL}${route}")
  code=$(echo "$body" | tail -n1)
  body=$(echo "$body" | sed '$d')
  if [ "$code" != "200" ]; then
    fail "route ${route} -> HTTP ${code}"; return
  fi
  if echo "$body" | grep -qi 'oe_login_form\|"login"[^,]*action'; then
    fail "route ${route} -> redirected to login page"; return
  fi
  if echo "$body" | grep -qi 'Internal Server Error\|Traceback (most recent\|QWeb2\|odoo.exceptions'; then
    fail "route ${route} -> error/traceback in response"; return
  fi
  pass "route ${route} -> HTTP 200 (authenticated)"
}

for route in \
  "/tcrm/discuss" \
  "/tcrm/crm" \
  "/tcrm/sales" \
  "/tcrm/action-407" \
  "/tcrm/dashboards?dashboard_id=4"; do
  check_route "$route"
done

# --- 4. JSON-RPC relationship assertions ------------------------------------
# call_kw helper: model method domain -> integer result (search_count etc.)
jsonrpc_count() {
  local model="$1"; local domain="$2"
  local payload
  payload=$(printf '{"jsonrpc":"2.0","method":"call","params":{"model":"%s","method":"search_count","args":[%s],"kwargs":{}}}' "$model" "$domain")
  curl -sS -b "$COOKIES" -H "Content-Type: application/json" -d "$payload" "${BASE_URL}/web/dataset/call_kw" \
    | sed -n 's/.*"result": *\([0-9-]*\).*/\1/p'
}

assert_min() {
  local label="$1"; local value="$2"; local min="$3"
  if [ -z "$value" ]; then fail "${label}: no result"; return; fi
  if [ "$value" -ge "$min" ]; then pass "${label} = ${value} (>= ${min})"; else fail "${label} = ${value} (< ${min})"; fi
}

assert_eq() {
  local label="$1"; local value="$2"; local expected="$3"
  if [ "$value" = "$expected" ]; then pass "${label} = ${value}"; else fail "${label} = ${value} (expected ${expected})"; fi
}

echo "JSON-RPC relationship checks:"
assert_min "CRM opportunities" "$(jsonrpc_count 'crm.lead' '[["type","=","opportunity"]]')" 6
assert_min "Sales teams" "$(jsonrpc_count 'crm.team' '[]')" 1
assert_min "Property projects" "$(jsonrpc_count 'propertio.project' '[]')" 2
assert_min "Property units" "$(jsonrpc_count 'propertio.unit' '[]')" 12
assert_min "Units referencing a project" "$(jsonrpc_count 'propertio.unit' '[["project_id","!=",false]]')" 12
assert_min "Opportunities referencing a unit" "$(jsonrpc_count 'crm.lead' '[["propertio_unit_id","!=",false]]')" 6
assert_min "Property sales w/ opportunity" "$(jsonrpc_count 'propertio.sale' '[["opportunity_id","!=",false]]')" 3
assert_min "Property sales w/ broker" "$(jsonrpc_count 'propertio.sale' '[["agency_id","!=",false]]')" 3
assert_min "Quotations referencing a customer" "$(jsonrpc_count 'sale.order' '[["partner_id","!=",false]]')" 3
assert_min "Quotations referencing an opportunity" "$(jsonrpc_count 'sale.order' '[["opportunity_id","!=",false]]')" 3
assert_eq  "Sold units" "$(jsonrpc_count 'propertio.unit' '[["state","=","sold"]]')" 3
assert_eq  "Reserved (option) units" "$(jsonrpc_count 'propertio.unit' '[["state","=","option"]]')" 2
assert_min "Posted payments" "$(jsonrpc_count 'propertio.payment' '[["state","=","posted"]]')" 3

echo ""
echo "RESULT: ${PASS_COUNT} passed, ${FAIL_COUNT} failed"
[ "$FAIL_COUNT" -eq 0 ]
