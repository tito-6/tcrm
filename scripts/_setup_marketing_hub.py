# -*- coding: utf-8 -*-
"""One-shot Marketing Hub bootstrap (API key via ZERNIO_API_KEY env)."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ICP = env["ir.config_parameter"].sudo()
key = (os.environ.get("ZERNIO_API_KEY") or "").strip()
if key:
    ICP.set_param("tcrm_marketing_hub.zernio_api_key", key)
    print("API key set from ZERNIO_API_KEY")
else:
    print("No ZERNIO_API_KEY in env; leaving existing param")

ICP.set_param(
    "tcrm_marketing_hub.zernio_base_url",
    ICP.get_param("tcrm_marketing_hub.zernio_base_url") or "https://zernio.com/api/v1",
)

# Hide Piyasa Analizi root menu if still active
root = env.ref("tcrm_market_analysis.menu_tcrm_market_root", raise_if_not_found=False)
if root and root.active:
    root.write({"active": False})
    print("Hidden Piyasa Analizi menu")

env.cr.commit()
print("DONE")
