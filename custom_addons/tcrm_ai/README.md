# TCRM AI

Gemini-powered AI for TCRM: answers questions using your database (master or tenant), reports, and real-time web.

## Install / Activate

1. **From the TCRM UI (recommended)**  
   - Go to **Apps**.  
   - Remove the "Apps" filter, search for **TCRM AI**.  
   - Click **Install** (or **Upgrade** if already installed).

2. **From command line** (with TCRM server stopped):
   ```bat
   cd d:\tcrm
   .\venv\Scripts\python.exe tcrm-src\tcrm-bin -c tcrm.conf -d tcrm_master -u tcrm_ai --stop-after-init
   ```

## Settings (best practice)

1. Go to **Settings** (gear icon or General Settings).
2. Find the **TCRM AI** block.
3. Set **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/apikey)).
4. Choose **Gemini Model** (e.g. Gemini 1.5 Flash).
5. Click **Save**.

You can also open **TCRM AI → AI Settings** for the same configuration.

## Test

- **Discuss chat**: Open Discuss, open the chat with **TCRM AI**. Ask e.g. *"What is the payment plan for contract DRAFT-001"*. You should get an AI answer with tables and links to records (no more "I don't understand" or emoji tour).
- **TCRM AI menu**: **TCRM AI → Ask TCRM AI** for the full-screen chat.

## Dependencies

- **Python**: `google-generativeai` (install with `pip install google-generativeai` if missing).
