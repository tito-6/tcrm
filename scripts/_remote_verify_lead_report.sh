#!/usr/bin/env bash
sudo -u postgres psql -d perla_villalari -c "SELECT cron_name, active, interval_number, interval_type FROM ir_cron WHERE cron_name ILIKE '%Marketing Hub%' ORDER BY cron_name;"
sudo -u postgres psql -d perla_villalari -c "SELECT name, state FROM ir_module_module WHERE name='tcrm_lead_report';"
