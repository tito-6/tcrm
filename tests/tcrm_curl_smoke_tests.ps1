<#
    TCRM curl + JSON-RPC smoke tests (PowerShell mirror for Windows hosts).

    Verifies server reachability, that the main TCRM routes return authenticated
    pages (not login/error), and that the cross-module relationships created by
    tcrm_mock_data are present and consistent.

    Usage (defaults shown):
        $env:TCRM_BASE_URL = "http://localhost:8069"
        $env:TCRM_DATABASE = "tcrm_master"
        $env:TCRM_USERNAME = "admin"
        $env:TCRM_PASSWORD = "admin"
        pwsh tests/tcrm_curl_smoke_tests.ps1

    No credentials are committed; everything comes from the environment.
#>
$ErrorActionPreference = "Stop"

$Base = if ($env:TCRM_BASE_URL) { $env:TCRM_BASE_URL } else { "http://localhost:8069" }
$Db   = if ($env:TCRM_DATABASE) { $env:TCRM_DATABASE } else { "tcrm_master" }
$User = if ($env:TCRM_USERNAME) { $env:TCRM_USERNAME } else { "admin" }
$Pass = if ($env:TCRM_PASSWORD) { $env:TCRM_PASSWORD } else { "admin" }

$script:PassCount = 0
$script:FailCount = 0
function Pass($m) { Write-Host "  [PASS] $m"; $script:PassCount++ }
function Fail($m) { Write-Host "  [FAIL] $m"; $script:FailCount++ }

Write-Host "TCRM smoke tests against $Base (db=$Db)"

# --- 1. reachability --------------------------------------------------------
try {
    Invoke-WebRequest -Uri "$Base/web/login" -UseBasicParsing -TimeoutSec 15 | Out-Null
    Pass "server reachable"
} catch {
    Fail "server not reachable at $Base"
    Write-Host "RESULT: $($script:PassCount) passed, $($script:FailCount) failed"
    exit 1
}

# --- 2. authentication ------------------------------------------------------
$authBody = @{ jsonrpc = "2.0"; method = "call"; params = @{ db = $Db; login = $User; password = $Pass } } | ConvertTo-Json -Compress
try {
    $auth = Invoke-WebRequest -Uri "$Base/web/session/authenticate" -Method Post -ContentType "application/json" -Body $authBody -SessionVariable sess -UseBasicParsing -TimeoutSec 30
    $authJson = $auth.Content | ConvertFrom-Json
    if ($authJson.result.uid) { Pass "authentication succeeded (uid=$($authJson.result.uid))" }
    else { Fail "authentication failed: $($auth.Content)"; Write-Host "RESULT: $($script:PassCount) passed, $($script:FailCount) failed"; exit 1 }
} catch {
    Fail "authentication request failed: $($_.Exception.Message)"
    Write-Host "RESULT: $($script:PassCount) passed, $($script:FailCount) failed"; exit 1
}

# --- 3. routes --------------------------------------------------------------
function Check-Route($route) {
    try {
        $r = Invoke-WebRequest -Uri "$Base$route" -WebSession $sess -UseBasicParsing -TimeoutSec 30
        if ($r.StatusCode -ne 200) { Fail "route $route -> HTTP $($r.StatusCode)"; return }
        if ($r.Content -match "oe_login_form") { Fail "route $route -> redirected to login page"; return }
        if ($r.Content -match "Internal Server Error|Traceback \(most recent") { Fail "route $route -> error/traceback"; return }
        Pass "route $route -> HTTP 200 (authenticated)"
    } catch { Fail "route $route -> $($_.Exception.Message)" }
}
foreach ($route in "/tcrm/discuss", "/tcrm/crm", "/tcrm/sales", "/tcrm/action-407", "/tcrm/dashboards?dashboard_id=4") {
    Check-Route $route
}

# --- 4. JSON-RPC relationship assertions ------------------------------------
function Count($model, $domainJson) {
    $body = '{"jsonrpc":"2.0","method":"call","params":{"model":"' + $model + '","method":"search_count","args":[' + $domainJson + '],"kwargs":{}}}'
    $resp = Invoke-WebRequest -Uri "$Base/web/dataset/call_kw" -Method Post -ContentType "application/json" -Body $body -WebSession $sess -UseBasicParsing -TimeoutSec 40
    $j = $resp.Content | ConvertFrom-Json
    if ($null -ne $j.error) { return $null }
    return [int]$j.result
}
function Assert-Min($label, $value, $min) {
    if ($null -eq $value) { Fail "${label}: no result"; return }
    if ($value -ge $min) { Pass "$label = $value (>= $min)" } else { Fail "$label = $value (< $min)" }
}
function Assert-Eq($label, $value, $expected) {
    if ($value -eq $expected) { Pass "$label = $value" } else { Fail "$label = $value (expected $expected)" }
}

Write-Host "JSON-RPC relationship checks:"
Assert-Min "CRM opportunities" (Count 'crm.lead' '[["type","=","opportunity"]]') 6
Assert-Min "Sales teams" (Count 'crm.team' '[]') 1
Assert-Min "Property projects" (Count 'propertio.project' '[]') 2
Assert-Min "Property units" (Count 'propertio.unit' '[]') 12
Assert-Min "Units referencing a project" (Count 'propertio.unit' '[["project_id","!=",false]]') 12
Assert-Min "Opportunities referencing a unit" (Count 'crm.lead' '[["propertio_unit_id","!=",false]]') 6
Assert-Min "Property sales w/ opportunity" (Count 'propertio.sale' '[["opportunity_id","!=",false]]') 3
Assert-Min "Property sales w/ broker" (Count 'propertio.sale' '[["agency_id","!=",false]]') 3
Assert-Min "Quotations referencing a customer" (Count 'sale.order' '[["partner_id","!=",false]]') 3
Assert-Min "Quotations referencing an opportunity" (Count 'sale.order' '[["opportunity_id","!=",false]]') 3
Assert-Eq  "Sold units" (Count 'propertio.unit' '[["state","=","sold"]]') 3
Assert-Eq  "Reserved (option) units" (Count 'propertio.unit' '[["state","=","option"]]') 2
Assert-Min "Posted payments" (Count 'propertio.payment' '[["state","=","posted"]]') 3

Write-Host ""
Write-Host "RESULT: $($script:PassCount) passed, $($script:FailCount) failed"
if ($script:FailCount -ne 0) { exit 1 } else { exit 0 }
