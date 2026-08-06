#!/usr/bin/env bash
echo "=== public docs ==="
curl -s -o /dev/null -w "/docs=%{http_code}\n" https://tcrm.online/docs
curl -s -o /dev/null -w "/tr/docs=%{http_code}\n" https://tcrm.online/tr/docs
curl -s -o /dev/null -w "/docs/santral=%{http_code}\n" https://tcrm.online/docs/santral
echo "=== TCRM Master menu sequence ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT m.id||' seq='||m.sequence||' name='||COALESCE(m.name->>'en_US', m.name->>'tr_TR','?') FROM ir_ui_menu m JOIN ir_model_data d ON d.res_id=m.id AND d.model='ir.ui.menu' WHERE d.module='tcrm_saas_core' AND d.name='menu_tcrm_root';"
echo "=== all top-level app menus by sequence ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT m.sequence||' | '||COALESCE(m.name->>'en_US', m.name->>'tr_TR','?') FROM ir_ui_menu m WHERE m.parent_id IS NULL ORDER BY m.sequence, m.id;"
echo "=== contact_name column ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT column_name FROM information_schema.columns WHERE table_name='tcrm_call_record' AND column_name='contact_name';"
echo "=== login eye JS present? ==="
curl -s https://tcrm.online/web/login | grep -c "o_show_password\|tcrmBound" 
