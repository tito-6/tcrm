# TCRM AI Research (`tcrm_ai_research`)

Native NotebookLM-style research assistant for TCRM (Odoo 19), backed by a **self-hosted RAGFlow** instance.

Browser → OWL UI → authenticated TCRM JSON-RPC → Python RAGFlow client → RAGFlow API.

The RAGFlow API key **never** reaches the browser.

## 1. Prerequisites

- TCRM / Odoo **19.0**
- Python packages: `requests` (declared in the manifest)
- A reachable self-hosted **RAGFlow** instance with an API key
- At least one RAGFlow **dataset** and optionally a **chat assistant**

## 2. Supported Odoo version

Detected in this repository: **TCRM 19.0** (OWL **2.8.1**, imports from `tcrm`, controllers use `type='jsonrpc'`).

## 3. RAGFlow setup assumptions

- HTTP API compatible with RAGFlow **v0.24+** (see [HTTP API reference](https://ragflow.io/docs/http_api_reference))
- Auth header: `Authorization: Bearer <API_KEY>`
- Used endpoints (encapsulated in `services/ragflow_client.py`):
  - `POST/GET /api/v1/datasets`
  - `POST/GET/DELETE /api/v1/datasets/{id}/documents`
  - `POST /api/v1/datasets/{id}/chunks` (parse)
  - `POST /api/v1/chats` and `POST /api/v1/chats/{id}/sessions`
  - `POST /api/v1/chat/completions` (`stream: false` by default)

## 4. Installation

1. Ensure `custom_addons` is on `addons_path`.
2. Update the apps list and install **TCRM AI Research**.
3. Assign users to **AI Research User** / **Manager** / **Administrator**.
4. Configure RAGFlow under **Settings → AI Research** (or via environment variables).

```bash
# Example test run (replace DB name)
python tcrm-src/tcrm-bin -c odoo.conf -d YOUR_DB -i tcrm_ai_research --stop-after-init
python tcrm-src/tcrm-bin -c odoo.conf -d YOUR_DB --test-enable --test-tags=tcrm_ai_research --stop-after-init
```

## 5. Configuration fields

| Field | ICP key | Description |
|------|---------|-------------|
| RAGFlow Base URL | `tcrm_ai_research.base_url` | e.g. `https://ragflow.internal` |
| RAGFlow API Key | `tcrm_ai_research.api_key` | Server-side only |
| Default Dataset ID | `tcrm_ai_research.default_dataset_id` | Fallback dataset |
| Default Assistant / Chat ID | `tcrm_ai_research.default_assistant_id` | Fallback chat |
| Request timeout | `tcrm_ai_research.timeout` | Seconds (5–300) |
| Max upload size | `tcrm_ai_research.max_upload_size_mb` | Default 25 |
| Default language | `tcrm_ai_research.default_language` | `tr` / `en` |
| Enable web research | `tcrm_ai_research.enable_web_research` | Feature flag |
| Enable streaming | `tcrm_ai_research.enable_streaming` | Feature flag |
| Allowed extensions | `tcrm_ai_research.allowed_extensions` | Comma-separated |

## 6. Environment variables (optional overrides)

```text
RAGFLOW_BASE_URL=https://ragflow.example.com
RAGFLOW_API_KEY=replace-me
RAGFLOW_DEFAULT_DATASET_ID=your-dataset-id
RAGFLOW_DEFAULT_ASSISTANT_ID=your-chat-id
RAGFLOW_TIMEOUT=60
```

Environment values override ICP for the mapped keys. Never commit real credentials.

### Sample configuration (no real secrets)

```ini
# odoo.conf / process env
RAGFLOW_BASE_URL=https://ragflow.example.com
RAGFLOW_API_KEY=ragflow-api-key-placeholder
RAGFLOW_DEFAULT_DATASET_ID=dataset-id-placeholder
RAGFLOW_DEFAULT_ASSISTANT_ID=chat-id-placeholder
RAGFLOW_TIMEOUT=60
```

## 7. User groups and permissions

| Group | Capabilities |
|-------|--------------|
| AI Research User | Use assistant, own conversations, workspace documents if member |
| AI Research Manager | Manage company workspaces/documents/conversations |
| AI Research Administrator | Configure RAGFlow, full diagnostic access |

Record rules enforce multi-company isolation and workspace membership.

## 8. Creating a workspace

1. Open **AI Research → Workspaces**.
2. Set company, owner, members.
3. Paste RAGFlow dataset ID and optional chat assistant ID.
4. Choose default language (`tr` / `en`).

## 9. Uploading and syncing documents

- From the assistant sidebar, upload files (validated by size/extension).
- Or create `tcrm.ai.document` records linked to an `ir.attachment`, then **Sync to RAGFlow**.
- States: `draft` → `pending` → `processing` → `ready` / `failed`.
- Cron `AI Research: sync pending documents` refreshes pending/processing docs every 5 minutes.
- Existing CRM attachments are **not** auto-uploaded; selection is explicit.
- Deleting an AI document mapping best-effort deletes the RAGFlow document.

## 10. Opening AI Research from CRM

On a **Lead/Opportunity** or **Customer**, click the **AI Research** smart button.

Context passed server-side:

- company, user, partner, lead, `res_model` / `res_id`, record name
- Permission-filtered description, tags, stage, related attachment names

## 11. Troubleshooting

| Symptom | Check |
|---------|--------|
| “RAGFlow API key is not configured” | ICP or `RAGFLOW_API_KEY` |
| Upload rejected | Extension list / max size |
| Sync failed | RAGFlow dataset ownership, API key, network |
| Empty answers | Chat assistant linked to the dataset; documents `ready` |
| Access errors | Group membership + workspace members |

Server logs use correlation IDs; API keys and document bodies are not logged.

## 12. Security recommendations

- Keep RAGFlow on a private network; allow only the TCRM server.
- Prefer env vars for the API key in production.
- Restrict Administrator group.
- Do not expose RAGFlow UI/login through TCRM.
- Review workspace membership regularly.

## 13. Backup and data-deletion

- Odoo models (`tcrm.ai.*`) are part of the normal DB backup.
- RAGFlow stores its own indexes — back up RAGFlow data volumes separately.
- Unlinking an AI document attempts remote delete; orphan RAGFlow docs may remain if RAGFlow is down — re-check from RAGFlow admin tools.
- Saving a CRM note copies text into chatter; deleting the conversation does not remove the note.

## 14. How to run tests

Tests mock RAGFlow (no live server required):

```bash
python tcrm-src/tcrm-bin -c odoo.conf -d YOUR_DB --test-enable --test-tags=tcrm_ai_research --stop-after-init
```

Coverage includes access rights, multi-company isolation, checksums, sync states, timeouts, auth failures, malformed responses, citations, Turkish Unicode, and save-as-note.

## 15. Known limitations

- Default Q&A path is **non-streaming** (reliable over JSON-RPC). Streaming helpers exist in the provider for a future SSE/polling UI path.
- Web research toggle is a feature flag; actual web crawling depends on RAGFlow dataset/chat configuration.
- Citation → Odoo document linking requires matching `ragflow_document_id`.
- Does not embed or proxy the RAGFlow UI (by design).
- Separate from `tcrm_ai` (Gemini chat) and `tcrm_research_hub` (NotebookLM sync).

## Architecture

```text
TCRM OWL (ResearchAssistant)
  → /tcrm_ai/* JSON-RPC (auth=user)
    → models / DocumentSyncService / ContextBuilder
      → RagflowResearchProvider (BaseResearchProvider)
        → Self-hosted RAGFlow HTTP API
```

To swap providers later, implement `BaseResearchProvider` and change `get_research_provider()`.
