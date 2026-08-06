#!/bin/bash
set -euxo pipefail
# Signed webhook test with real-shaped Meta match params
SECRET=$(grep -E '^TCRM_LEAD_SECRET=' /opt/tcrm/.env | cut -d= -f2- | tr -d '\r')
TENANT=$(grep -E '^TCRM_TENANT_UUID=' /opt/tcrm/.env | cut -d= -f2- | tr -d '\r')
# fallbacks from lead.astro defaults if env missing
SECRET=${SECRET:-e275aaaf864c976f522dd845b88828c0332c3f57a5cbab4f524a7a60e196a9e5}
TENANT=${TENANT:-ecfe7537-1eba-4c1d-b0c2-4d87f06dca7f}

NOW=$(date +%s)
EVENT_ID="evt_emq_test_${NOW}"
FBCLID="IwAR0EmqCoverage${NOW}"
FBC="fb.1.${NOW}.${FBCLID}"
FBP="fb.1.${NOW}.9876543210"
EMAIL="emq.coverage.${NOW}@akod.tech"

BODY=$(python3 - <<PY
import json
print(json.dumps({
  "name": "EMQ Coverage Test ${NOW}",
  "contact_name": "Ayşe Demir",
  "email_from": "$EMAIL",
  "phone": "+905551234567",
  "description": "CAPI match quality coverage test — delete after verify",
  "service": "Lead Generation",
  "budget": "",
  "page_url": "https://akod.tech/tr?fbclid=$FBCLID",
  "website": "https://akod.tech/tr?fbclid=$FBCLID",
  "utm_source": "facebook",
  "utm_medium": "paid",
  "utm_campaign": "emq_test",
  "fbp": "$FBP",
  "fbc": "$FBC",
  "fbclid": "$FBCLID",
  "event_id": "$EVENT_ID",
  "client_ip": "176.240.10.55",
  "client_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
  "city": "Istanbul",
  "zip": "34710",
  "country": "tr",
}))
PY
)

BODY_HASH=$(printf '%s' "$BODY" | sha256sum | awk '{print $1}')
IDEM="idem-emq-${NOW}"
TS=$NOW
CANON=$(printf 'v1\nPOST\n/webhook/akod/lead\n%s\n%s\n%s\n%s' "$TS" "$TENANT" "$IDEM" "$BODY_HASH")
SIG=$(printf '%s' "$CANON" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

echo "POSTING..."
RESP=$(curl -sS -w "\nHTTP:%{http_code}" -X POST "http://127.0.0.1:8069/webhook/akod/lead" \
  -H "Content-Type: application/json" \
  -H "Host: akod.tcrm.online" \
  -H "X-TCRM-Signature-Version: v1" \
  -H "X-TCRM-Timestamp: $TS" \
  -H "X-TCRM-Tenant: $TENANT" \
  -H "X-TCRM-Idempotency-Key: $IDEM" \
  -H "X-TCRM-Correlation-ID: corr-emq-$NOW" \
  -H "X-TCRM-Signature: $SIG" \
  -H "X-Forwarded-For: 176.240.10.55" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  --data-binary "$BODY")
echo "$RESP"

LEAD_ID=$(echo "$RESP" | python3 -c "import sys,json,re; t=sys.stdin.read(); m=re.search(r'\{.*\}',t,re.S); d=json.loads(m.group(0)) if m else {}; print(d.get('lead_id') or '')" 2>/dev/null || true)
echo "LEAD_ID=$LEAD_ID"

if [ -n "$LEAD_ID" ]; then
  sudo -u postgres psql -d akod_prod -c "SELECT id, email_from, meta_fbc, meta_fbp, meta_client_ip, meta_event_id, meta_capi_lead_event_sent, meta_capi_last_event, city, zip FROM crm_lead WHERE id=$LEAD_ID;"
  # Mark won to fire Purchase
  sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm shell -c /opt/tcrm/tcrm.prod.conf -d akod_prod <<PY
lead = env['crm.lead'].browse($LEAD_ID)
print('before', lead.meta_capi_lead_event_sent, lead.meta_capi_purchase_event_sent, lead.meta_fbc, lead.meta_fbp, lead.meta_client_ip)
lead.write({'expected_revenue': 25000, 'probability': 100, 'won_status': 'won'})
env.cr.commit()
lead.invalidate_recordset()
print('after', lead.meta_capi_lead_event_sent, lead.meta_capi_purchase_event_sent, lead.meta_capi_last_event)
print('log', (lead.meta_capi_event_log or '')[-500:])
PY
fi

echo "=== recent CAPI log lines ==="
grep -E "CAPI|Meta CAPI|Sending (Lead|Purchase)|events\?access_token|graph.facebook" /opt/tcrm/tcrm_data/tcrm.log | tail -30
'