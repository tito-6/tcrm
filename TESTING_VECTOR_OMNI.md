# Vector Sync + Omni-Agent — Testing Checklist

Use this after installing/upgrading modules and deploying the RAG proxy.

---

## TCRM (local)

- [ ] **Modules upgraded**
  ```powershell
  cd d:\tcrm
  $env:PYTHONPATH = "d:\tcrm\tcrm-src"
  .\venv\Scripts\python.exe -m tcrm -c tcrm.conf -u tcrm_vector_sync -u tcrm_propertio --stop-after-init
  ```

- [ ] **System parameter**  
  **Settings → Technical → System Parameters**  
  Ensure `tcrm.ai_base_url` = `http://45.9.191.119:8000` (no trailing slash).  
  Default is set by `tcrm_ai` data; you can edit it here.

- [ ] **Start TCRM** (if not already running)  
  `.\run.ps1`  
  Then open http://localhost:8069

- [ ] **Trigger vector sync**  
  Create or edit a **Propertio Sale**, **Unit**, or **Contact** (res.partner).  
  Check **Settings → Technical → Vector Sync Queue** (or run a SQL query on `tcrm_vector_sync_queue`) — within about 1 minute you should see rows with `state = sent` (or `pending` if the VPS is down).

---

## VPS (tcrm_rag)

- [ ] **Install/update dependencies**
  ```bash
  cd /path/to/tcrm_rag
  pip install -r requirements.txt
  ```

- [ ] **Restart the app**
  ```bash
  # If using systemd:
  sudo systemctl restart tcrm-rag

  # Or run manually:
  uvicorn app:app --host 0.0.0.0 --port 8000
  ```

- [ ] **Health**
  ```bash
  curl -s http://45.9.191.119:8000/health
  ```
  Expect: `{"status":"ok","ollama":"reachable"}`

- [ ] **Ingest** (from TCRM cron or manual test)
  ```bash
  curl -s -X POST http://45.9.191.119:8000/ingest \
    -H "Content-Type: application/json" \
    -d '{"model":"propertio.sale","record_id":1,"text":"Test sale. Customer Acme. Unit A-01.","action":"upsert"}'
  ```
  Expect: `{"status":"ok","action":"upsert","id":"propertio.sale_1"}`

---

## End-to-end

- [ ] **Ollama provider in TCRM**  
  **Settings → TCRM AI → Providers**  
  Add an **Ollama** provider with base URL `http://45.9.191.119:8000` (or leave key empty and rely on `tcrm.ai_base_url`). Ensure at least one active key.

- [ ] **Chat (Omni-Agent)**  
  In TCRM, open the AI chat and ask:
  - *"List our sales"* or *"What do we know about unit A-01?"* → should use **tcrm_database_search** (internal data).
  - *"What is the weather in Istanbul?"* or *"Latest news"* → should use **web_search** (DuckDuckGo or SearXNG).

- [ ] **Disable Omni-Agent** (optional)  
  On the VPS, set `USE_OMNI_AGENT=0` and restart; chat will use the previous RAG+Ollama-only behaviour.

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| Queue rows stay `pending` | `tcrm.ai_base_url` set? VPS reachable? Firewall allows 8000? |
| Chat returns "Omni-Agent is not available" | VPS: `pip install langchain-ollama langgraph`; restart app. |
| No internal data in answers | Run ingest (create/edit a sale/unit/partner), wait for cron; confirm `/ingest` returns 200. |
| Web search fails | If using SearXNG, set `SEARXNG_URL` on the VPS; otherwise DuckDuckGo is used. |
