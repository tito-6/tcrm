import requests
import json
import uuid

BASE_URL = 'https://public-staging.tcrm.online'

def test_multi_worker():
    print('\n[TEST] Multi-Worker Shared State')
    test_email = f'worker_test_{uuid.uuid4().hex[:8]}@tcrm.online'
    payload = {
        'name': 'Worker Test',
        'company': 'TCRM',
        'email': test_email,
        'phone': '+905559998877',
        'message': 'Testing multi-worker',
        'consent': True
    }

    print('  Request 1:', requests.post(f'{BASE_URL}/api/lead', json=payload).status_code)
    print('  Request 2:', requests.post(f'{BASE_URL}/api/lead', json=payload).status_code)
    print('  Request 3:', requests.post(f'{BASE_URL}/api/lead', json=payload).status_code)
    
    resp4 = requests.post(f'{BASE_URL}/api/lead', json=payload)
    print('  Request 4:', resp4.status_code)
    if resp4.status_code == 429:
        print('  [PASS] Multi-Worker Shared State test passed!')
    else:
        print('  [FAIL] Did not get 429 on 4th request')

if __name__ == '__main__':
    test_multi_worker()
