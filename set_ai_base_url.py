"""Set tcrm.ai_base_url via JSON-RPC to the running TCRM server."""
import requests
import json

url = "http://127.0.0.1:8069"
db = "tcrm_master"
user = "admin"
password = "admin"  # use your admin password if different

# 1) Authenticate
auth = requests.post(f"{url}/web/session/authenticate", json={
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": db,
        "login": user,
        "password": password,
    },
    "id": 1,
})
if auth.status_code != 200 or not auth.json().get("result"):
    print("Auth failed:", auth.text)
    exit(1)
cookies = auth.cookies

# 2) Call set_param (need to use /web/dataset/call_kw or similar)
# In Odoo 17 the RPC is /web/dataset/call_kw
rpc = requests.post(
    f"{url}/web/dataset/call_kw",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "ir.config_parameter",
            "method": "set_param",
            "args": ["tcrm.ai_base_url", "http://45.9.191.119:8000"],
            "kwargs": {},
        },
        "id": 2,
    },
    cookies=cookies,
    headers={"Content-Type": "application/json"},
)
if rpc.status_code != 200:
    print("RPC failed:", rpc.status_code, rpc.text)
    exit(1)
res = rpc.json()
if res.get("error"):
    print("Error:", res["error"])
    exit(1)
print("tcrm.ai_base_url set to http://45.9.191.119:8000")
