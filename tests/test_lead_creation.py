import requests
import psycopg2
import time
import os
import uuid

BASE_URL = 'https://public-staging.tcrm.online'

print('Submitting lead to Next.js API...')
payload = {
    'name': 'Test Lead Acceptance',
    'company': 'Automated Testing Inc',
    'email': f'test.lead.{int(time.time())}@tcrm.online',
    'phone': '+905551234567',
    'industry': 'Yazilim',
    'message': 'This is an automated test lead.',
    'consent': True
}

resp = requests.post(f'{BASE_URL}/api/lead', json=payload)
print(f'API Status: {resp.status_code}')
try:
    data = resp.json()
    print('API Response:', data)
except:
    print(resp.text)
    exit(1)

if resp.status_code != 200:
    print('Failed to create lead via API')
    exit(1)

correlation_id = data.get('correlation_id')
print(f'Correlation ID: {correlation_id}')

print('Verifying in PostgreSQL (tcrm_master)...')
conn = psycopg2.connect('dbname=tcrm_master user=postgres')
cur = conn.cursor()

cur.execute('SELECT id, name, type FROM crm_lead WHERE email_from = %s', (payload['email'],))
row = cur.fetchone()
if not row:
    print(f'CRM Lead not found for email {payload["email"]}')
    exit(1)
print(f'CRM Lead found: ID={row[0]}, Name={row[1]}, Type={row[2]}')

print('SUCCESS: Signed Lead Acceptance Test Passed')
