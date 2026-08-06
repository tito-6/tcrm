#!/usr/bin/env python3
"""Fix Santral credentials on production VPS - run on server."""
import sys
import os
import base64
import hashlib
import subprocess

sys.path.insert(0, '/opt/tcrm/tcrm-src')

DB = 'tcrm_master'

def psql(sql):
    r = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', DB, '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return r.stdout.strip()

def psql_exec(sql):
    subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', DB, '-c', sql],
        check=True
    )

# Get database.secret
db_secret = psql("SELECT value FROM ir_config_parameter WHERE key='database.secret'")
if not db_secret:
    db_secret = 'tcrm-call-center:' + DB
    print('WARNING: using fallback secret')
else:
    print('Got database.secret from DB (len=%d)' % len(db_secret))

# Build Fernet
from cryptography.fernet import Fernet
digest = hashlib.sha256(db_secret.encode('utf-8')).digest()
f = Fernet(base64.urlsafe_b64encode(digest))

ENC_PREFIX = 'enc:v1:'

# Decrypt current to show what was there
row = psql("SELECT api_key_secret_encrypted, auth_token_encrypted FROM tcrm_call_provider_config WHERE id=1")
parts = row.split('|')
for i, label in enumerate(['API Secret', 'Auth Token']):
    val = parts[i] if i < len(parts) else ''
    if val.startswith(ENC_PREFIX):
        dec = f.decrypt(val[len(ENC_PREFIX):].encode()).decode()
        print('Current %s: %s...%s (len=%d)' % (label, dec[:6], dec[-4:], len(dec)))
    else:
        print('Current %s: NOT ENCRYPTED or EMPTY' % label)

# New values (from env or args)
NEW_API_SECRET = os.environ.get('TWILIO_API_SECRET', '')
NEW_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
NEW_API_KEY_SID = os.environ.get('TWILIO_API_KEY_SID', '')

if not NEW_API_SECRET or not NEW_AUTH_TOKEN or not NEW_API_KEY_SID:
    print('ERROR: Set TWILIO_API_SECRET, TWILIO_AUTH_TOKEN, and TWILIO_API_KEY_SID environment variables.')
    sys.exit(1)

new_secret_enc = ENC_PREFIX + f.encrypt(NEW_API_SECRET.encode()).decode()
new_token_enc = ENC_PREFIX + f.encrypt(NEW_AUTH_TOKEN.encode()).decode()

# Update
sql = (
    "UPDATE tcrm_call_provider_config SET "
    "api_key_secret_encrypted='%s', "
    "auth_token_encrypted='%s', "
    "api_key_sid='%s' "
    "WHERE id=1"
) % (new_secret_enc, new_token_enc, NEW_API_KEY_SID)
psql_exec(sql)
print('Updated encrypted secrets in DB')

# Verify round-trip
row2 = psql("SELECT api_key_secret_encrypted, auth_token_encrypted FROM tcrm_call_provider_config WHERE id=1")
p2 = row2.split('|')
v_secret = f.decrypt(p2[0][len(ENC_PREFIX):].encode()).decode()
v_token = f.decrypt(p2[1][len(ENC_PREFIX):].encode()).decode()
print('Verify API Secret match: %s' % (v_secret == NEW_API_SECRET))
print('Verify Auth Token match: %s' % (v_token == NEW_AUTH_TOKEN))
print('DONE - restart tcrm service: sudo systemctl restart tcrm')
