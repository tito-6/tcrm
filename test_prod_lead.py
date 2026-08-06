import sys
import uuid
import time
import requests
import psycopg2

BASE_URL = 'https://tcrm.online'

def run():
    print(f"Submitting test lead to {BASE_URL}...")
    unique_id = uuid.uuid4().hex[:8]
    idemp_key = str(uuid.uuid4())
    payload = {
        'name': f'Production Test {unique_id}',
        'company': 'AKOD Test LLC',
        'email': f'prod.test.{unique_id}@akod.tech',
        'phone': '+905559998877',
        'message': 'Testing production go-live webhook',
        'consent': True,
        'idempotencyKey': idemp_key
    }

    # 1. Normal submission
    print("  [1] Sending first request...")
    resp = requests.post(f"{BASE_URL}/api/lead", json=payload)
    print("      Response:", resp.status_code)
    
    # 2. Replay exactly
    print("  [2] Sending exact replay...")
    resp2 = requests.post(f"{BASE_URL}/api/lead", json=payload)
    print("      Response:", resp2.status_code)
    
    # 3. Changed payload with same email
    print("  [3] Sending changed payload (should 409)")
    payload_changed = payload.copy()
    payload_changed['name'] = 'Changed Name'
    resp3 = requests.post(f"{BASE_URL}/api/lead", json=payload_changed)
    print("      Response:", resp3.status_code)

if __name__ == '__main__':
    run()
