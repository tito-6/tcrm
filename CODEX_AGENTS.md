# TCRM Codex Agent Guide

This file is for future Codex agents and software engineers working in this
repository. It captures the local development facts, project structure, run
commands, and safe extension patterns for TCRM.

## Project Overview

TCRM is an Odoo-style ERP/CRM application built on a forked core in
`tcrm-src`. Custom business functionality lives in `custom_addons`.

Primary local database:

- Database: `tcrm_master`
- PostgreSQL host: `localhost`
- PostgreSQL port: `5432`
- PostgreSQL user/password: `odoo` / `odoo`
- App port: `8069`
- Local URL: `http://127.0.0.1:8069`

Do not use Docker for local application runs unless the user explicitly asks.
The expected local runtime is the Python virtual environment at:

```powershell
D:\tcrm\venv
```

## Important Paths

- Project root: `D:\tcrm`
- Python venv: `D:\tcrm\venv`
- Main config: `D:\tcrm\tcrm.conf`
- Core source: `D:\tcrm\tcrm-src`
- Core addons: `D:\tcrm\tcrm-src\addons`
- TCRM core package: `D:\tcrm\tcrm-src\tcrm`
- Custom addons: `D:\tcrm\custom_addons`
- Runtime data: `D:\tcrm\tcrm_data`
- App log: `D:\tcrm\tcrm_data\tcrm.log`
- Filestore: `D:\tcrm\tcrm_data\filestore`

Configured addon paths from `tcrm.conf`:

```ini
addons_path = d:/tcrm/tcrm-src/tcrm/addons,d:/tcrm/tcrm-src/addons,d:/tcrm/custom_addons
```

## Current Custom Modules

- `tcrm_saas_core`: SaaS command center, tenants, packages, billing, permission sets.
- `tcrm_propertio`: real estate CRM/ERP domain models, projects, units, sales, payments, reports.
- `tcrm_ai`: embedded AI assistant, provider management, prompt/context/tool execution logic.
- `tcrm_vector_sync`: vector/RAG sync queue and mixins.
- `tcrm_research_hub`: Research Hub UI and proxy integration.
- `tcrm_web_enhance`: UI/UX styling and frontend enhancements.

## Run The App Locally

Use PowerShell from `D:\tcrm`.

```powershell
cd D:\tcrm
$env:PYTHONPATH = "D:\tcrm\tcrm-src"
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf
```

Or use the existing script:

```powershell
cd D:\tcrm
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

The app should be available at:

```text
http://127.0.0.1:8069
```

## Run In Background For Local Use

```powershell
cd D:\tcrm
$env:PYTHONPATH = "D:\tcrm\tcrm-src"
Start-Process -FilePath "D:\tcrm\venv\Scripts\python.exe" `
  -ArgumentList @("-m", "tcrm", "-c", "D:\tcrm\tcrm.conf") `
  -WorkingDirectory "D:\tcrm" `
  -WindowStyle Hidden
```

Check that it is listening:

```powershell
Get-NetTCPConnection -LocalPort 8069 -ErrorAction SilentlyContinue |
  Where-Object { $_.State -eq "Listen" }
```

Stop TCRM server processes:

```powershell
Get-CimInstance Win32_Process |
  Where-Object {
    ($_.Name -eq "python.exe") -and
    ($_.CommandLine -like "*D:\tcrm\tcrm.conf*" -or $_.CommandLine -like "*D:/tcrm/tcrm.conf*")
  } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## Logs And Smoke Tests

Tail the app log:

```powershell
Get-Content -Path D:\tcrm\tcrm_data\tcrm.log -Tail 200
```

Search recent log output for serious errors:

```powershell
Get-Content -Path D:\tcrm\tcrm_data\tcrm.log -Tail 300 |
  Select-String -Pattern "ERROR|Traceback|UndefinedColumn|UndefinedTable"
```

Basic login page smoke test:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8069/web/login" -UseBasicParsing -TimeoutSec 20 |
  Select-Object StatusCode,StatusDescription
```

Authenticated dashboard smoke test:

```powershell
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$login = Invoke-WebRequest -Uri "http://127.0.0.1:8069/web/login" -WebSession $s -UseBasicParsing
$csrf = [regex]::Match($login.Content, 'name="csrf_token"\s+value="([^"]+)"').Groups[1].Value
$body = @{ login = "admin"; password = "admin"; csrf_token = $csrf }
Invoke-WebRequest -Uri "http://127.0.0.1:8069/web/login" -Method Post -Body $body -WebSession $s -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue | Out-Null
$json = '{"jsonrpc":"2.0","method":"call","params":{},"id":1}'
Invoke-WebRequest -Uri "http://127.0.0.1:8069/tcrm_master/dashboard" -Method Post -Body $json -ContentType "application/json" -WebSession $s -UseBasicParsing
```

## Module Upgrade Commands

When Python model fields, XML views, security, data files, or manifest entries
change, upgrade the affected module. Stop the running server first.

Upgrade one module:

```powershell
cd D:\tcrm
$env:PYTHONPATH = "D:\tcrm\tcrm-src"
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -u tcrm_saas_core --stop-after-init
```

Upgrade multiple modules:

```powershell
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -u tcrm_saas_core,tcrm_propertio --stop-after-init
```

Common schema symptom:

- `psycopg2.errors.UndefinedColumn`: the code declares a field but the module was not upgraded.
- `psycopg2.errors.UndefinedTable`: a model/table was added but the module was not installed or upgraded.
- XML parse/load errors: inspect the log around the first traceback; fix the XML, then re-run upgrade.

## Development Rules

Prefer custom addon changes over modifying core `tcrm-src` code. Core edits are
acceptable only when the bug is in the forked framework itself or local runtime
behavior cannot be fixed cleanly in a custom addon.

Before editing:

```powershell
git status --short
```

There may be existing user changes. Do not revert unrelated changes.

Use these locations:

- Models: `custom_addons/<module>/models/*.py`
- Controllers: `custom_addons/<module>/controllers/*.py`
- Wizards: `custom_addons/<module>/wizard/*.py`
- Views: `custom_addons/<module>/views/**/*.xml`
- Security groups/rules/access: `custom_addons/<module>/security/*.xml` and `ir.model.access.csv`
- Data/demo/cron: `custom_addons/<module>/data/*.xml`
- Frontend OWL/JS/XML/SCSS: `custom_addons/<module>/static/src/**`
- Reports: `custom_addons/<module>/reports/**`
- Translations: `custom_addons/<module>/i18n/*.po`

## Add A New Model

1. Add or choose a module under `custom_addons`.
2. Create a model file in `models/`, for example `models/my_model.py`.
3. Import it in `models/__init__.py`.
4. Define the model with `_name`, `_description`, fields, constraints, and methods.
5. Add access rights in `security/ir.model.access.csv`.
6. Add views/actions/menus in `views/*.xml`.
7. Include new XML files in `__manifest__.py`.
8. Upgrade the module with `-u <module>`.
9. Check `tcrm_data/tcrm.log` and smoke test the UI.

Minimal model example:

```python
from tcrm import models, fields, api, _
from tcrm.exceptions import ValidationError


class TcrmExample(models.Model):
    _name = "tcrm.example"
    _description = "TCRM Example"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if record.name and len(record.name.strip()) < 3:
                raise ValidationError(_("Name must be at least 3 characters."))
```

Access CSV example:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_tcrm_example_user,tcrm.example user,model_tcrm_example,base.group_user,1,1,1,0
```

## Extend An Existing Model

Use `_inherit` inside the relevant custom module.

```python
from tcrm import models, fields


class PropertioSale(models.Model):
    _inherit = "propertio.sale"

    external_reference = fields.Char(string="External Reference")
```

After adding stored fields, always upgrade the module:

```powershell
.\venv\Scripts\python.exe -m tcrm -c D:\tcrm\tcrm.conf -d tcrm_master -u tcrm_propertio --stop-after-init
```

## Views, Actions, And Menus

Keep XML IDs stable. Do not rename existing XML IDs unless migration impact is
understood.

Typical view file pattern:

```xml
<odoo>
    <record id="view_tcrm_example_form" model="ir.ui.view">
        <field name="name">tcrm.example.form</field>
        <field name="model">tcrm.example</field>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="notes"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_tcrm_example" model="ir.actions.act_window">
        <field name="name">Examples</field>
        <field name="res_model">tcrm.example</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

In Odoo/TCRM 19-style code, prefer `list` over legacy `tree` in `view_mode`
when the surrounding module already uses `list`.

## Controllers And JSON Routes

Use `type="jsonrpc"` for JSON endpoints. `type="json"` is deprecated and logs
warnings in this codebase.

Example:

```python
from tcrm import http
from tcrm.http import request


class MyController(http.Controller):

    @http.route("/tcrm/example/data", type="jsonrpc", auth="user")
    def example_data(self):
        return {"ok": True}
```

Use `auth="user"` for authenticated backend calls. Add explicit access checks
for admin-only or tenant-only endpoints.

## Frontend Development

OWL components and frontend assets live under:

```text
custom_addons/<module>/static/src
```

After changing JS, XML templates, SCSS, or asset declarations:

1. Upgrade the module if the manifest changed.
2. Restart the server if Python/static asset loading behaves stale.
3. Hard-refresh the browser or clear assets if necessary.
4. Check browser console and `tcrm_data/tcrm.log`.

For `tcrm_saas_core`, the command center assets are declared in
`custom_addons/tcrm_saas_core/__manifest__.py` under `web.assets_backend`.

## Security And Multi-Tenancy

Be strict with tenant/company boundaries.

- Use record rules for tenant isolation where possible.
- Use `sudo()` only when the endpoint or method is intentionally system-level.
- When using `sudo()`, manually filter by company/tenant if data is user-facing.
- Check groups with `user.has_group(...)`.
- Keep `ir.model.access.csv` minimal: grant only what the role needs.
- Field-level permission behavior exists in `tcrm_saas_core` permission sets.

Important groups include:

- `base.group_system`
- `base.group_user`
- `tcrm_saas_core.group_tcrm_tenant_admin`
- `tcrm_saas_core.group_tcrm_tenant_sales`
- `tcrm_research_hub.group_research_hub_user`

## Database And Filestore Notes

The database and filestore must stay in sync. Missing filestore attachments may
appear as debug logs when records reference files that are absent on disk. Do
not delete or regenerate database/filestore content unless the user asks.

Do not edit PostgreSQL data directories directly.

## Known Local Fixes Applied

These fixes were applied during local startup work:

- `tcrm_saas_core` was upgraded on `tcrm_master` to sync fields such as
  `tcrm.tenant.is_frozen`.
- `tcrm-src/tcrm/http.py` treats missing local GeoIP database files as disabled
  GeoIP instead of logging repeated stack traces.
- `tcrm-src/tcrm/tools/_vendor/sessions.py` logs missing expired session files
  without a stack trace.
- `custom_addons/tcrm_research_hub/controllers/research_proxy.py` uses
  `type="jsonrpc"` for its status endpoint.

## Common Troubleshooting

Server will not start:

- Confirm PostgreSQL is running.
- Confirm `tcrm.conf` points to `db_user = odoo` and `db_password = odoo`.
- Confirm `PYTHONPATH` includes `D:\tcrm\tcrm-src`.
- Check `D:\tcrm\tcrm_data\tcrm.log`.

Port already in use:

```powershell
Get-NetTCPConnection -LocalPort 8069 -ErrorAction SilentlyContinue
```

Find TCRM Python processes:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*D:\tcrm\tcrm.conf*" } |
  Select-Object ProcessId,Name,CommandLine
```

Schema errors after code changes:

- Stop server.
- Run module upgrade.
- Restart server.
- Re-test endpoint/UI.

Frontend assets stale:

- Restart server.
- Hard-refresh browser.
- Upgrade module if asset manifest changed.

## Engineering Checklist For Future Changes

1. Read the relevant module manifest and existing patterns.
2. Check current git status before editing.
3. Keep changes inside the correct custom addon when possible.
4. Add or update access/security files for new models.
5. Add views/actions/menus only when needed.
6. Upgrade affected modules after model/XML/security changes.
7. Restart the venv server.
8. Smoke test the affected route/page.
9. Tail `tcrm_data/tcrm.log` and address real errors.
10. Report what changed and what was verified.

