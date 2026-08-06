#!/usr/bin/env bash
set -euo pipefail
for db in disposable_test perla_villalari; do
  echo "==== $db ===="
  sudo -u postgres psql -d "$db" -Atc \
    "SELECT d.name || '=' || m.active FROM ir_ui_menu m JOIN ir_model_data d ON d.res_id=m.id AND d.model='ir.ui.menu' WHERE d.module='base' AND d.name IN ('menu_management','menu_apps','menu_module_tree');"
done
