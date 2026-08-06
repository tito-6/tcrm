#!/usr/bin/env bash
for key in web.login web.login_layout website.navbar_nav website.header_call_to_action website.option_header_brand_logo website.brand_promotion; do
  echo "############ $key ############"
  sudo -u postgres psql -d tcrm_master -Atc "SELECT arch_db FROM ir_ui_view WHERE key='$key' LIMIT 1;" | head -c 2500
  echo ""
  echo ""
done
