import os
import requests
import json
import time
import hashlib
import hmac
import uuid
from threading import Thread

BASE_URL = 'https://tcrm.online/webhook/akod/lead'

SECRET = 'e275aaaf864c976f522dd845b88828c0332c3f57a5cbab4f524a7a60e196a9e5'
TENANT = 'ecfe7537-1eba-4c1d-b0c2-4d87f06dca7f'

def generate_signature(method, path, timestamp, tenant, idempotency_key, body_bytes):
    payload_sha256 = hashlib.sha256(body_bytes).hexdigest()
    canonical_input = f'v1\n{method}\n{path}\n{timestamp}\n{tenant}\n{idempotency_key}\n{payload_sha256}'
    return hmac.new(SECRET.encode('utf-8'), canonical_input.encode('utf-8'), hashlib.sha256).hexdigest()

def make_request(body_dict, idempotency_key, alter_tenant=False, alter_timestamp=False, alter_sig=False):
    body_bytes = json.dumps(body_dict).encode('utf-8')
    timestamp = str(int(time.time()))
    if alter_timestamp:
        timestamp = str(int(time.time()) - 1000) # Expired
        
    tenant_uuid = 'wrong-tenant' if alter_tenant else TENANT
    
    sig = generate_signature('POST', '/webhook/akod/lead', timestamp, tenant_uuid, idempotency_key, body_bytes)
    if alter_sig:
        sig = 'invalid_signature'

    headers = {
        'Content-Type': 'application/json',
        'X-TCRM-Signature-Version': 'v1',
        'X-TCRM-Timestamp': timestamp,
        'X-TCRM-Tenant': tenant_uuid,
        'X-TCRM-Idempotency-Key': idempotency_key,
        'X-TCRM-Correlation-ID': str(uuid.uuid4()),
        'X-TCRM-Signature': sig
    }
    
    return requests.post(BASE_URL, data=body_bytes, headers=headers)

# Test cases
idem_key = str(uuid.uuid4())
base_body = {
    'name': 'Idempotency Test Lead',
    'email': f'idem-{idem_key}@example.com',
    'phone': '+1234567890',
    'company': 'Test LLC',
    'message': 'Testing idempotency'
}

print('A. First valid request...')
res_a = make_request(base_body, idem_key)
print(res_a.status_code, res_a.text)

print('B. Exact replay...')
res_b = make_request(base_body, idem_key)
print(res_b.status_code, res_b.text)

print('C. Changed payload...')
changed_body = dict(base_body)
changed_body['message'] = 'Different message'
res_c = make_request(changed_body, idem_key)
print(res_c.status_code, res_c.text)

print('E. Invalid signature...')
res_e = make_request(base_body, str(uuid.uuid4()), alter_sig=True)
print(res_e.status_code, res_e.text)

print('F. Expired timestamp...')
res_f = make_request(base_body, str(uuid.uuid4()), alter_timestamp=True)
print(res_f.status_code, res_f.text)

print('G. Incorrect tenant UUID...')
res_g = make_request(base_body, str(uuid.uuid4()), alter_tenant=True)
print(res_g.status_code, res_g.text)

print('D. Concurrent replay...')
idem_key_concurrent = str(uuid.uuid4())
responses = []
def worker():
    res = make_request(base_body, idem_key_concurrent)
    responses.append((res.status_code, res.text))

t1 = Thread(target=worker)
t2 = Thread(target=worker)
t1.start()
t2.start()
t1.join()
t2.join()
print('Concurrent responses:', responses)

print('Done.')

