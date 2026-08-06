#!/bin/bash
set -euxo pipefail
SECRET=$(grep -E '^TCRM_LEAD_SECRET=' /opt/tcrm/.env | cut -d= -f2- | tr -d '\r')
TENANT=$(grep -E '^TCRM_TENANT_UUID=' /opt/tcrm/.env | cut -d= -f2- | tr -d '\r')
NOW=$(date +%s)
UUID=$(python3 -c 'import uuid; print(uuid.uuid4())')
EVENT_ID="evt_emq_test_${NOW}"
FBCLID="IwAR0EmqCoverage${NOW}"
FBC="fb.1.${NOW}.${FBCLID}"
FBP="fb.1.${NOW}.9876543210"
EMAIL="emq.coverage.${NOW}@akod.tech"

BODY=$(python3 - <<PY
import json
print(json.dumps({
  "name": "EMQ Coverage Test ${NOW}",
  "contact_name": "Ayse Demir",
  "email_from": "$EMAIL",
  "phone": "+905551234567",
  "description": "CAPI match quality coverage test — delete after verify",
  "service": "Lead Generation",
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
IDEM="$UUID"
TS=$NOW
CANON=$(printf 'v1\nPOST\n/webhook/akod/lead\n%s\n%s\n%s\n%s' "$TS" "$TENANT" "$IDEM" "$BODY_HASH")
SIG=$(printf '%s' "$CANON" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

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
  --data-binary "$BODY")
echo "$RESP"
LEAD_ID=$(echo "$RESP" | python3 -c "import sys,json,re; t=sys.stdin.read(); m=re.search(r'\{.*\}',t,re.S); d=json.loads(m.group(0)) if m else {}; print(d.get('lead_id') or '')")
echo LEAD_ID=$LEAD_ID
if [ -n "$LEAD_ID" ] && [ "$LEAD_ID" != "0" ] && [ "$LEAD_ID" != "None" ]; then
  sudo -u postgres psql -d akod_prod -c "SELECT id, email_from, left(meta_fbc,40) as fbc, left(meta_fbp,40) as fbp, meta_client_ip, meta_event_id, meta_capi_lead_event_sent, meta_capi_last_event, city, zip FROM crm_lead WHERE id=$LEAD_ID;"
  sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm shell -c /opt/tcrm/tcrm.prod.conf -d akod_prod <<PY
lead = env['crm.lead'].browse(int('$LEAD_ID'))
print('stored', lead.meta_fbc, lead.meta_fbp, lead.meta_client_ip, lead.meta_event_id, lead.meta_capi_lead_event_sent)
lead.write({'expected_revenue': 25000, 'probability': 100, 'won_status': 'won'})
env.cr.commit()
lead.invalidate_recordset()
print('purchase_flags', lead.meta_capi_purchase_event_sent, lead.meta_capi_last_event)
PY
fi
grep -E "akod_prod.*CAPI|akod_prod.*Sending (Lead|Purchase)|corr-emq-$NOW" /opt/tcrm/tcrm_data/tcrm.log | tail -20
'