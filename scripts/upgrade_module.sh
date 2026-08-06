sudo -u postgres psql -d tcrm_master -c "UPDATE ir_module_module SET state='to upgrade' WHERE name='tcrm_call_center';"
sudo systemctl restart tcrm
