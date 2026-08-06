# -*- coding: utf-8 -*-
"""Fix corrupted Propertio Turkish menu/action names (?? from bad encoding)."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# xml_id -> Turkish label (stored for en_US + tr_TR)
MENU_NAMES = {
    "tcrm_propertio.menu_propertio_dashboard": "Gösterge Paneli",
    "tcrm_propertio.menu_propertio_inventory": "Envanter",
    "tcrm_propertio.menu_propertio_sales": "Satışlar",
    "tcrm_propertio.menu_propertio_collections": "Tahsilat",
    "tcrm_propertio.menu_propertio_aftersales": "Satış Sonrası",
    "tcrm_propertio.menu_propertio_reporting": "Raporlama",
    "tcrm_propertio.menu_propertio_management": "Yönetim",
    "tcrm_propertio.menu_propertio_config": "Yapılandırma",
    "tcrm_propertio.menu_propertio_master_data": "Ana Veriler",
    "tcrm_propertio.menu_propertio_contact_mgmt": "Personel ve İş Ortakları",
    "tcrm_propertio.menu_propertio_reports_center": "Rapor Merkezi",
    "tcrm_propertio.menu_propertio_reports_hub": "Genel Bakış",
    "tcrm_propertio.menu_sale_wizard": "Yeni Satış",
    "tcrm_propertio.menu_sale": "Satış Sözleşmeleri",
    "tcrm_propertio.menu_propertio_offer": "Teklifler / Rezervasyonlar",
    "tcrm_propertio.menu_propertio_payment_cancel_request": "Ödeme İptal Talepleri",
    "tcrm_propertio.menu_payment": "Ödemeler",
    "tcrm_propertio.menu_propertio_collection_queue": "Tahsilat Kuyruğu",
    "tcrm_propertio.menu_propertio_handover": "Teslimler",
    "tcrm_propertio.menu_propertio_title_deed": "Tapular",
    "tcrm_propertio.menu_propertio_service_request": "Servis Talepleri",
    "tcrm_propertio.menu_propertio_notary": "Noter",
    "tcrm_propertio.menu_propertio_target": "Hedefler",
    "tcrm_propertio.menu_propertio_commission": "Komisyonlar",
    "tcrm_propertio.menu_propertio_commission_rule": "Komisyon Kuralları",
    "tcrm_propertio.menu_propertio_cash_register": "Kasalar",
    "tcrm_propertio.menu_propertio_feature": "Birim Özellikleri",
    "tcrm_propertio.menu_project_type": "Proje Tipleri",
    "tcrm_propertio.menu_project_stage": "Proje Aşamaları",
    "tcrm_propertio.menu_unit_category": "Gayrimenkul Kategorileri",
    "tcrm_propertio.menu_unit_status": "Detaylı Durumlar",
    "tcrm_propertio.menu_sale_stage": "Satış Aşamaları",
    "tcrm_propertio.menu_agencies_config": "Acenteler",
    "tcrm_propertio.menu_users_config": "Satış Personeli",
    "tcrm_propertio.menu_propertio_whatsapp_templates": "WhatsApp Şablonları",
    "tcrm_propertio.menu_propertio_audit_log": "Denetim Kaydı",
    "tcrm_propertio.menu_report_export_wizard": "Raporları Dışa Aktar",
    "tcrm_propertio.menu_report_category_collection": "Tahsilat ve Ödemeler",
    "tcrm_propertio.menu_report_category_sales": "Satış Raporları",
    "tcrm_propertio.menu_report_category_customer": "Müşteri Raporları",
    "tcrm_propertio.menu_report_category_finance": "Mali Raporlar",
    "tcrm_propertio.menu_report_category_performance": "Performans Raporları",
    "tcrm_propertio.menu_report_category_property": "Gayrimenkul Raporları",
    "tcrm_propertio.menu_report_category_admin": "Yönetim ve Uyum",
    "tcrm_propertio.menu_report_category_marketing": "Pazarlama ve Müşteri Adayları",
}

ACTION_NAMES = {
    "tcrm_propertio.action_propertio_sale_wizard": "Yeni Satış",
    "tcrm_propertio.action_propertio_sale": "Satış Sözleşmeleri",
    "tcrm_propertio.action_propertio_offer": "Teklifler / Rezervasyonlar",
    "tcrm_propertio.action_propertio_payment_cancel_request": "Ödeme İptal Talepleri",
    "tcrm_propertio.action_propertio_payment": "Ödemeler",
    "tcrm_propertio.action_propertio_dashboard": "Gösterge Paneli",
    "tcrm_propertio.action_propertio_handover": "Teslimler",
    "tcrm_propertio.action_propertio_title_deed": "Tapular",
    "tcrm_propertio.action_propertio_service_request": "Servis Talepleri",
    "tcrm_propertio.action_propertio_notary": "Noter Randevuları",
    "tcrm_propertio.action_propertio_target": "Hedefler",
    "tcrm_propertio.action_propertio_commission": "Komisyonlar",
    "tcrm_propertio.action_propertio_commission_rule": "Komisyon Kuralları",
    "tcrm_propertio.action_propertio_cash_register": "Kasalar",
    "tcrm_propertio.action_propertio_collection_queue": "Tahsilat Kuyruğu",
    "tcrm_propertio.action_propertio_project": "Projeler",
    "tcrm_propertio.action_propertio_unit": "Birimler",
    "tcrm_propertio.action_propertio_feature": "Birim Özellikleri",
    "tcrm_propertio.action_propertio_whatsapp_template": "WhatsApp Şablonları",
}


def _set_json_name(table, rec_id, label):
    payload = json.dumps({"en_US": label, "tr_TR": label}, ensure_ascii=False)
    env.cr.execute(
        f"UPDATE {table} SET name = %s::jsonb WHERE id = %s",
        (payload, rec_id),
    )


n = 0
for xid, label in MENU_NAMES.items():
    rec = env.ref(xid, raise_if_not_found=False)
    if not rec:
        print("MISSING MENU", xid)
        continue
    _set_json_name("ir_ui_menu", rec.id, label)
    n += 1
    print("MENU", xid, "->", label)

for xid, label in ACTION_NAMES.items():
    rec = env.ref(xid, raise_if_not_found=False)
    if not rec:
        print("MISSING ACTION", xid)
        continue
    # ir.actions.* store name as jsonb too in Odoo 19
    table = rec._table
    _set_json_name(table, rec.id, label)
    n += 1
    print("ACTION", xid, "->", label)

# Fix any remaining Propertio menus that still contain '?'
root = env.ref("tcrm_propertio.menu_propertio_root", raise_if_not_found=False)
if root:
    broken = env["ir.ui.menu"].sudo().search([("parent_id", "child_of", root.id)])
    for m in broken:
        env.cr.execute("SELECT name::text FROM ir_ui_menu WHERE id=%s", (m.id,))
        raw = env.cr.fetchone()[0] or ""
        if "?" in raw:
            print("STILL_BROKEN", m.id, raw)

env.cr.commit()

# Verify navbar parents
for xid in [
    "menu_propertio_dashboard",
    "menu_propertio_sales",
    "menu_propertio_aftersales",
    "menu_propertio_management",
    "menu_propertio_config",
    "menu_sale_wizard",
    "menu_propertio_offer",
    "menu_propertio_payment_cancel_request",
]:
    rec = env.ref(f"tcrm_propertio.{xid}", raise_if_not_found=False)
    if rec:
        env.cr.execute("SELECT name::text FROM ir_ui_menu WHERE id=%s", (rec.id,))
        print("VERIFY", xid, env.cr.fetchone()[0])

print("UPDATED", n)
