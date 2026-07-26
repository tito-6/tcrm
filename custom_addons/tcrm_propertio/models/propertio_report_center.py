# -*- coding: utf-8 -*-
import base64
import csv
import io
import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from tcrm import api, fields, models, _
from tcrm.exceptions import UserError


REPORT_CATALOG = [
    {'key': 'advanced_leads_crm_propertio', 'name': 'Advanced CRM + Propertio Leads', 'name_tr': 'Gelişmiş Lead Raporu (CRM + Propertio)', 'category': 'Marketing & Leads', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead', 'description': 'CRM leadleri ile Propertio rezervasyon/satış köprüsü; danışman, proje, kaynak, platform filtreleri. Günlük admin e-postası.'},
    {'key': 'sales_performance_closer', 'name': "Sales Performance Report - Closer's View", 'name_tr': 'Satış Performansı - Closer Görünümü', 'category': 'Performance Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'occupancy_unit_lifecycle', 'name': 'Occupancy & Unit Lifecycle Report', 'name_tr': 'Doluluk ve Birim Yaşam Döngüsü', 'category': 'Rentals', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'cash_flow_arrears_forensic', 'name': 'Cash-Flow & Arrears - Forensic View', 'name_tr': 'Nakit Akış ve Gecikme - Adli Görünüm', 'category': 'Financial Reports', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'sales_collection_summary', 'name': 'Sales Collection Summary', 'name_tr': 'Satış Tahsilat Özeti', 'category': 'Collection & Payments', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale', 'description': 'Collected, outstanding, and overdue position by contract.'},
    {'key': 'payment_plan_table', 'name': 'Payment Plan Table', 'name_tr': 'Ödeme Planı Tablosu', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'expected_payment_list', 'name': 'Expected Payment List', 'name_tr': 'Beklenen Ödeme Listesi', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment', 'domain': [('is_paid', '=', False)]},
    {'key': 'payment_plan_vat', 'name': 'Payment Plan (VAT Included)', 'name_tr': 'KDV Dahil Ödeme Planı', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'incoming_payments_chart', 'name': 'Incoming & Expected Payments', 'name_tr': 'Gelen ve Beklenen Ödemeler', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'tahsilat_satis_durumu', 'name': 'Tahsilat ve Satış Durumu', 'name_tr': 'Tahsilat ve Satış Durumu', 'category': 'Collection & Payments', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'proje_nakit_durumu', 'name': 'Proje Nakit Durumu', 'name_tr': 'Proje Nakit Durumu', 'category': 'Collection & Payments', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'gelecek_nakit_akisi', 'name': 'Gelecek Nakit Akışı', 'name_tr': 'Gelecek Nakit Akışı', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment', 'domain': [('is_paid', '=', False)]},
    {'key': 'kirmizi_alarm_musteriler', 'name': 'Kırmızı Alarm Müşteriler', 'name_tr': 'Kırmızı Alarm Müşteriler', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment', 'domain': [('payment_status', '=', 'overdue')]},
    {'key': 'sales_report', 'name': 'Sales Report', 'name_tr': 'Satış Raporu', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'type_based_sales', 'name': 'Type-Based Sales & Inventory', 'name_tr': 'Tip Bazlı Satış ve Stok', 'category': 'Sales Reports', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'approval_based_sales', 'name': 'Approval-Based Sales Chart', 'name_tr': 'Onay Bazlı Satış Grafiği', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'total_sales_chart', 'name': 'Total Sales Chart', 'name_tr': 'Toplam Satış Grafiği', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'daily_sales_quantity', 'name': 'Daily Sales Quantity', 'name_tr': 'Günlük Satış Adedi', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'sales_status', 'name': 'Sales Status Report', 'name_tr': 'Satış Durum Raporu', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'sales_exchange_rate', 'name': 'Sales Exchange Rate', 'name_tr': 'Satış Döviz Kuru', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'customer_journey', 'name': 'Customer Journey', 'name_tr': 'Müşteri Yolculuğu', 'category': 'Customer Reports', 'model': 'res.partner', 'date_field': 'create_date', 'drill_model': 'res.partner'},
    {'key': 'customer_journey_individual', 'name': 'Individual Customer Journey', 'name_tr': 'Bireysel Müşteri Yolculuğu', 'category': 'Customer Reports', 'model': 'res.partner', 'date_field': 'create_date', 'drill_model': 'res.partner'},
    {'key': 'customer_overall_status', 'name': 'Customer Overall Status', 'name_tr': 'Müşteri Genel Durumu', 'category': 'Customer Reports', 'model': 'res.partner', 'date_field': 'create_date', 'drill_model': 'res.partner'},
    {'key': 'cash_register', 'name': 'Cash Register Report', 'name_tr': 'Kasa Raporu', 'category': 'Financial Reports', 'model': 'propertio.payment', 'date_field': 'payment_date', 'drill_model': 'propertio.payment'},
    {'key': 'daily_cash_register', 'name': 'Daily Cash Register', 'name_tr': 'Günlük Kasa', 'category': 'Financial Reports', 'model': 'propertio.payment', 'date_field': 'payment_date', 'drill_model': 'propertio.payment'},
    {'key': 'cash_flow_statement', 'name': 'Cash Flow Statement', 'name_tr': 'Nakit Akış Tablosu', 'category': 'Financial Reports', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'employee_performance', 'name': 'Employee Performance', 'name_tr': 'Personel Performansı', 'category': 'Performance Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'end_of_day_meeting', 'name': 'End-of-Day Meeting', 'name_tr': 'Gün Sonu Toplantısı', 'category': 'Performance Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'danisman_karnesi', 'name': 'Danışman Karnesi', 'name_tr': 'Danışman Karnesi', 'category': 'Performance Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'danisman_karnesi_bu_ay', 'name': 'Danışman Karnesi (Bu Ay)', 'name_tr': 'Danışman Karnesi (Bu Ay)', 'category': 'Performance Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'independent_units', 'name': 'Independent Units', 'name_tr': 'Bağımsız Bölümler', 'category': 'Property Reports', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'construction_progress', 'name': 'Construction Progress', 'name_tr': 'İnşaat İlerlemesi', 'category': 'Property Reports', 'model': 'propertio.project', 'date_field': None, 'drill_model': 'propertio.project'},
    {'key': 'title_deed_invoice', 'name': 'Title Deed & Invoice', 'name_tr': 'Tapu ve Fatura', 'category': 'Property Reports', 'model': 'propertio.title.deed', 'date_field': 'tapu_date', 'drill_model': 'propertio.title.deed'},
    {'key': 'authorization_matrix', 'name': 'Authorization Matrix', 'name_tr': 'Yetki Matrisi', 'category': 'Admin & Compliance', 'model': 'res.users', 'date_field': 'create_date', 'drill_model': 'res.users'},
    {'key': 'crm_log_records', 'name': 'CRM Activity Log', 'name_tr': 'CRM Aktivite Logu', 'category': 'Admin & Compliance', 'model': 'mail.activity', 'date_field': 'date_deadline', 'drill_model': 'mail.activity'},
    {'key': 'lead_report', 'name': 'Lead Report', 'name_tr': 'Lead Raporu', 'category': 'Marketing & Leads', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead'},
    {'key': 'advertising_leads', 'name': 'Advertising Leads', 'name_tr': 'Reklam Leadleri', 'category': 'Marketing & Leads', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead'},
    {'key': 'web_form_tracking', 'name': 'Web Form Tracking', 'name_tr': 'Web Form Takibi', 'category': 'Marketing & Leads', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead'},
    {'key': 'project_gdv_analysis', 'name': 'Project GDV Analysis', 'name_tr': 'Proje GDV Analizi', 'category': 'Advanced Analytics', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'cash_flow_forecast', 'name': 'Cash Flow Forecast', 'name_tr': 'Nakit Akış Tahmini', 'category': 'Advanced Analytics', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'vat_compliance_audit', 'name': 'VAT Compliance Audit', 'name_tr': 'KDV Uyum Denetimi', 'category': 'Admin & Compliance', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'fx_contract_compliance', 'name': 'FX Contract Compliance', 'name_tr': 'Döviz Sözleşme Uyum Raporu', 'category': 'Admin & Compliance', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'title_deed_tax_risk', 'name': 'Title Deed Tax Risk', 'name_tr': 'Tapu Harcı Risk Raporu', 'category': 'Property Reports', 'model': 'propertio.title.deed', 'date_field': 'tapu_date', 'drill_model': 'propertio.title.deed'},
    {'key': 'crm_erp_reconciliation', 'name': 'CRM / ERP Reconciliation', 'name_tr': 'CRM / ERP Mutabakat Raporu', 'category': 'Admin & Compliance', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'showing_document_compliance', 'name': 'Showing Document Compliance', 'name_tr': 'Yer Gösterme Belgesi Uyum Raporu', 'category': 'Admin & Compliance', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead'},
    {'key': 'valuation_gedas_readiness', 'name': 'Valuation / GEDAS Readiness', 'name_tr': 'Değerleme / GEDAS Hazırlık Raporu', 'category': 'Advanced Analytics', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'rental_portfolio', 'name': 'Rental Portfolio Report', 'name_tr': 'Kiralama Portföy Raporu', 'category': 'Rentals', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'rental_contracts', 'name': 'Rental Contracts Report', 'name_tr': 'Kira Sözleşmeleri Raporu', 'category': 'Rentals', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'rental_collections', 'name': 'Rental Collections Report', 'name_tr': 'Kira Tahsilat Raporu', 'category': 'Rentals', 'model': 'propertio.payment', 'date_field': 'payment_date', 'drill_model': 'propertio.payment'},
    {'key': 'tenant_landlord', 'name': 'Tenant/Landlord Report', 'name_tr': 'Kiracı/Mülk Sahibi Raporu', 'category': 'Rentals', 'model': 'res.partner', 'date_field': 'create_date', 'drill_model': 'res.partner'},
    {'key': 'vacancy_occupancy', 'name': 'Vacancy & Occupancy Report', 'name_tr': 'Boşluk ve Doluluk Raporu', 'category': 'Rentals', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'unit_profitability', 'name': 'Unit Profitability Report', 'name_tr': 'Birim Karlılık Raporu', 'category': 'Financial Reports', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'broker_commission', 'name': 'Broker Commission Report', 'name_tr': 'Broker Komisyon Raporu', 'category': 'Financial Reports', 'model': 'propertio.commission', 'date_field': 'period_from', 'drill_model': 'propertio.commission'},
    {'key': 'customer_risk', 'name': 'Customer Risk Report', 'name_tr': 'Müşteri Risk Raporu', 'category': 'Customer Reports', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment'},
    {'key': 'overdue_installments', 'name': 'Overdue Installments Report', 'name_tr': 'Gecikmiş Taksitler Raporu', 'category': 'Collection & Payments', 'model': 'propertio.installment', 'date_field': 'date_due', 'drill_model': 'propertio.installment', 'domain': [('payment_status', '=', 'overdue')]},
    {'key': 'sales_pipeline', 'name': 'Sales Pipeline Report', 'name_tr': 'Satış Pipeline Raporu', 'category': 'Sales Reports', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead'},
    {'key': 'reservation_cancellation', 'name': 'Reservation & Cancellation Report', 'name_tr': 'Rezervasyon ve İptal Raporu', 'category': 'Sales Reports', 'model': 'propertio.sale', 'date_field': 'date_sale', 'drill_model': 'propertio.sale'},
    {'key': 'project_profitability', 'name': 'Project Profitability Report', 'name_tr': 'Proje Karlılık Raporu', 'category': 'Financial Reports', 'model': 'propertio.unit', 'date_field': None, 'drill_model': 'propertio.unit'},
    {'key': 'inventory_aging', 'name': 'Inventory Aging Report', 'name_tr': 'Stok Yaşlandırma Raporu', 'category': 'Property Reports', 'model': 'propertio.unit', 'date_field': 'create_date', 'drill_model': 'propertio.unit'},
    {'key': 'lead_source_roi', 'name': 'Lead Source ROI Report', 'name_tr': 'Lead Kaynağı ROI Raporu', 'category': 'Marketing & Leads', 'model': 'crm.lead', 'date_field': 'create_date', 'drill_model': 'crm.lead'},
]

REPORT_LOCALIZATION = {
    'advanced_leads_crm_propertio': {
        'tr': 'Gelişmiş Lead Raporu (CRM + Propertio)',
        'en': 'Advanced CRM + Propertio Leads',
        'ar': 'تقرير العملاء المحتملين المتقدم',
        'desc_tr': 'CRM + Propertio birleşik lead görünümü: kaynak, platform, proje, danışman, rezervasyon ve sözleşme durumu.',
        'desc_en': 'Unified CRM + Propertio lead view: source, platform, project, salesperson, reservation and contract status.',
        'chart': 'Source',
        'value': 'Expected Revenue',
    },
    'sales_performance_closer': {'tr': 'Satış Performansı - Closer Görünümü', 'en': "Sales Performance Report - Closer's View", 'ar': "Sales Performance - Closer", 'desc_tr': 'Kapanış hızı, lead-to-contract velocity ve indirim varyansı.', 'desc_en': 'Average days to close, lead-to-contract velocity and discount variance.', 'chart': 'Salesperson', 'value': 'Actual Revenue'},
    'occupancy_unit_lifecycle': {'tr': 'Doluluk ve Birim Yaşam Döngüsü', 'en': 'Occupancy & Unit Lifecycle Report', 'ar': 'Occupancy & Unit Lifecycle', 'desc_tr': 'RevPAM, bakım maliyet/gelir oranı ve portföy devir hızı.', 'desc_en': 'RevPAM, maintenance cost-to-income ratio and portfolio turnover rate.', 'chart': 'Lifecycle Node', 'value': 'RevPAM'},
    'cash_flow_arrears_forensic': {'tr': 'Nakit Akış ve Gecikme - Adli Görünüm', 'en': 'Cash-Flow & Arrears - Forensic View', 'ar': 'Cash Flow & Arrears - Forensic', 'desc_tr': 'DSO, CEI ve ağırlıklı ortalama gecikme analizi.', 'desc_en': 'DSO, CEI and weighted average delinquency analysis.', 'chart': 'Aging Bucket', 'value': 'Residual'},
    'sales_collection_summary': {'tr': 'Satış Tahsilat Özeti', 'en': 'Sales Collection Summary', 'ar': 'ملخص تحصيل المبيعات', 'desc_tr': 'Sözleşme bazında tahsilat, bakiye, gecikme ve aksiyon önceliği.', 'desc_en': 'Collected, outstanding, overdue and action priority by contract.', 'chart': 'Customer', 'value': 'Outstanding'},
    'payment_plan_table': {'tr': 'Ödeme Planı Tablosu', 'en': 'Payment Plan Table', 'ar': 'جدول خطة الدفع', 'desc_tr': 'Taksit, vade, ödeme durumu, kalan bakiye ve vade kovası.', 'desc_en': 'Installments, due dates, payment state, residual balance and due buckets.', 'chart': 'Due Month', 'value': 'Residual'},
    'expected_payment_list': {'tr': 'Beklenen Ödeme Listesi', 'en': 'Expected Payment List', 'ar': 'قائمة المدفوعات المتوقعة', 'desc_tr': 'Henüz kapanmamış vadeler ve tahsilat öncelikleri.', 'desc_en': 'Open receivables and collection priorities.', 'chart': 'Collection Priority', 'value': 'Residual'},
    'payment_plan_vat': {'tr': 'KDV Dahil Ödeme Planı', 'en': 'Payment Plan (VAT Included)', 'ar': 'خطة الدفع شاملة الضريبة', 'desc_tr': 'Net tutar, KDV ve brüt ödeme planı görünümü.', 'desc_en': 'Net, VAT and gross payment schedule.', 'chart': 'Due Month', 'value': 'VAT Included'},
    'incoming_payments_chart': {'tr': 'Gelen ve Beklenen Ödemeler', 'en': 'Incoming & Expected Payments', 'ar': 'المدفوعات الواردة والمتوقعة', 'desc_tr': 'Gerçekleşen ve beklenen tahsilat karşılaştırması.', 'desc_en': 'Actual versus expected collections.', 'chart': 'Due Month', 'value': 'Residual'},
    'tahsilat_satis_durumu': {'tr': 'Tahsilat ve Satış Durumu', 'en': 'Sales & Collection Status', 'ar': 'حالة البيع والتحصيل', 'desc_tr': 'Satış hacmi, tahsilat oranı ve açık bakiye özeti.', 'desc_en': 'Sales volume, collection ratio and open balance.', 'chart': 'Project', 'value': 'Outstanding'},
    'proje_nakit_durumu': {'tr': 'Proje Nakit Durumu', 'en': 'Project Cash Position', 'ar': 'موقف نقد المشروع', 'desc_tr': 'Proje stok değeri, satış, tahsilat ve alacak durumu.', 'desc_en': 'Project inventory value, sales, collections and receivables.', 'chart': 'Project', 'value': 'Receivable'},
    'gelecek_nakit_akisi': {'tr': 'Gelecek Nakit Akışı', 'en': 'Future Cash Flow', 'ar': 'التدفق النقدي المستقبلي', 'desc_tr': 'Önümüzdeki vadeler ve beklenen nakit akışı.', 'desc_en': 'Upcoming maturities and expected cash flow.', 'chart': 'Due Month', 'value': 'Residual'},
    'kirmizi_alarm_musteriler': {'tr': 'Kırmızı Alarm Müşteriler', 'en': 'Red Alert Customers', 'ar': 'عملاء إنذار أحمر', 'desc_tr': 'Gecikme riski yüksek müşteriler ve takip aksiyonları.', 'desc_en': 'High-risk overdue customers and follow-up actions.', 'chart': 'Risk Segment', 'value': 'Residual'},
    'sales_report': {'tr': 'Satış Raporu', 'en': 'Sales Report', 'ar': 'تقرير المبيعات', 'desc_tr': 'Sözleşme, müşteri, danışman, broker, indirim ve kur detayları.', 'desc_en': 'Contract, customer, consultant, broker, discount and FX details.', 'chart': 'Project', 'value': 'Sale Price'},
    'type_based_sales': {'tr': 'Tip Bazlı Satış ve Stok', 'en': 'Type-Based Sales & Inventory', 'ar': 'المبيعات والمخزون حسب النوع', 'desc_tr': 'Ünite tipi bazında stok, satış, tahsilat ve alacak.', 'desc_en': 'Inventory, sales, collections and receivables by unit type.', 'chart': 'Type', 'value': 'List Price'},
    'approval_based_sales': {'tr': 'Onay Bazlı Satış Grafiği', 'en': 'Approval-Based Sales Chart', 'ar': 'مبيعات حسب الموافقة', 'desc_tr': 'Taslak, onaylı ve iptal satışların satış değeri etkisi.', 'desc_en': 'Draft, confirmed and cancelled sales value impact.', 'chart': 'Approval Step', 'value': 'Sale Price'},
    'total_sales_chart': {'tr': 'Toplam Satış Grafiği', 'en': 'Total Sales Chart', 'ar': 'مخطط إجمالي المبيعات', 'desc_tr': 'Dönemsel satış hacmi ve ortalama satış trendi.', 'desc_en': 'Periodic sales volume and average deal trend.', 'chart': 'Sales Month', 'value': 'Sale Price'},
    'daily_sales_quantity': {'tr': 'Günlük Satış Adedi', 'en': 'Daily Sales Quantity', 'ar': 'عدد المبيعات اليومية', 'desc_tr': 'Günlük adet, ciro ve ortalama birim fiyat.', 'desc_en': 'Daily unit count, turnover and average unit price.', 'chart': 'Date', 'value': 'Sale Price'},
    'sales_status': {'tr': 'Satış Durum Raporu', 'en': 'Sales Status Report', 'ar': 'تقرير حالة المبيعات', 'desc_tr': 'Satış statüsü ve aksiyon gereksinimi.', 'desc_en': 'Sales status and required next actions.', 'chart': 'Status', 'value': 'Sale Price'},
    'sales_exchange_rate': {'tr': 'Satış Döviz Kuru', 'en': 'Sales Exchange Rate', 'ar': 'سعر صرف المبيعات', 'desc_tr': 'Dövizli satışların kur etkisi ve TL karşılığı.', 'desc_en': 'FX exposure and local currency equivalent.', 'chart': 'Currency', 'value': 'TRY Equivalent'},
    'customer_journey': {'tr': 'Müşteri Yolculuğu', 'en': 'Customer Journey', 'ar': 'رحلة العميل', 'desc_tr': 'Lead’den satışa müşteri temas ve risk durumu.', 'desc_en': 'Customer touch and risk state from lead to sale.', 'chart': 'Risk', 'value': 'Outstanding'},
    'customer_journey_individual': {'tr': 'Bireysel Müşteri Yolculuğu', 'en': 'Individual Customer Journey', 'ar': 'رحلة العميل الفردية', 'desc_tr': 'Müşteri bazında satış, tahsilat, gecikme ve son aksiyon.', 'desc_en': 'Per-customer sales, collection, overdue and last action.', 'chart': 'Customer', 'value': 'Outstanding'},
    'customer_overall_status': {'tr': 'Müşteri Genel Durumu', 'en': 'Customer Overall Status', 'ar': 'الحالة العامة للعميل', 'desc_tr': 'Müşteri portföy değeri, bakiye ve risk seviyesi.', 'desc_en': 'Customer portfolio value, balance and risk level.', 'chart': 'Risk', 'value': 'Outstanding'},
    'cash_register': {'tr': 'Kasa Raporu', 'en': 'Cash Register Report', 'ar': 'تقرير الصندوق', 'desc_tr': 'Kasa, ödeme yöntemi, fiş ve tahsilat akışı.', 'desc_en': 'Register, method, receipt and collection flow.', 'chart': 'Method', 'value': 'Amount'},
    'daily_cash_register': {'tr': 'Günlük Kasa', 'en': 'Daily Cash Register', 'ar': 'الصندوق اليومي', 'desc_tr': 'Günlük tahsilat ve ödeme yöntemi kırılımı.', 'desc_en': 'Daily collections and payment method split.', 'chart': 'Date', 'value': 'Amount'},
    'cash_flow_statement': {'tr': 'Nakit Akış Tablosu', 'en': 'Cash Flow Statement', 'ar': 'بيان التدفق النقدي', 'desc_tr': 'Vade bazlı beklenen, tahsil edilen ve açık nakit.', 'desc_en': 'Due-based expected, collected and open cash.', 'chart': 'Due Month', 'value': 'Residual'},
    'employee_performance': {'tr': 'Personel Performansı', 'en': 'Employee Performance', 'ar': 'أداء الموظف', 'desc_tr': 'Danışman bazında satış, tahsilat ve açık bakiye.', 'desc_en': 'Consultant sales, collections and open balance.', 'chart': 'Salesperson', 'value': 'Revenue'},
    'end_of_day_meeting': {'tr': 'Gün Sonu Toplantısı', 'en': 'End-of-Day Meeting', 'ar': 'اجتماع نهاية اليوم', 'desc_tr': 'Gün sonu satış aksiyonları ve açık takip maddeleri.', 'desc_en': 'End-of-day sales actions and open follow-up items.', 'chart': 'Salesperson', 'value': 'Deals'},
    'danisman_karnesi': {'tr': 'Danışman Karnesi', 'en': 'Consultant Scorecard', 'ar': 'بطاقة أداء المستشار', 'desc_tr': 'Danışman performans karnesi: ciro, tahsilat, bakiye.', 'desc_en': 'Consultant scorecard: revenue, collection and balance.', 'chart': 'Salesperson', 'value': 'Revenue'},
    'danisman_karnesi_bu_ay': {'tr': 'Danışman Karnesi (Bu Ay)', 'en': 'Consultant Scorecard (This Month)', 'ar': 'بطاقة أداء المستشار هذا الشهر', 'desc_tr': 'Bu ay danışman performansı.', 'desc_en': 'This month consultant performance.', 'chart': 'Salesperson', 'value': 'Revenue'},
    'independent_units': {'tr': 'Bağımsız Bölümler', 'en': 'Independent Units', 'ar': 'الوحدات المستقلة', 'desc_tr': 'Bağımsız bölüm envanteri, tapu referansı ve fiyat durumu.', 'desc_en': 'Independent section inventory, deed reference and price state.', 'chart': 'State', 'value': 'List Price'},
    'construction_progress': {'tr': 'İnşaat İlerlemesi', 'en': 'Construction Progress', 'ar': 'تقدم الإنشاء', 'desc_tr': 'Proje ilerleme, satış ve tahsilat karşılaştırması.', 'desc_en': 'Project progress, sales and collection comparison.', 'chart': 'Project', 'value': 'GDV'},
    'title_deed_invoice': {'tr': 'Tapu ve Fatura', 'en': 'Title Deed & Invoice', 'ar': 'الطابو والفاتورة', 'desc_tr': 'Tapu randevusu, devir durumu, maliyet ve fatura takibi.', 'desc_en': 'Title appointment, transfer state, cost and invoice tracking.', 'chart': 'State', 'value': 'Title Deed Cost'},
    'authorization_matrix': {'tr': 'Yetki Matrisi', 'en': 'Authorization Matrix', 'ar': 'مصفوفة الصلاحيات', 'desc_tr': 'Kullanıcı, şirket ve rapor erişim yetkileri.', 'desc_en': 'User, company and report access permissions.', 'chart': 'Company', 'value': 'Master Admin'},
    'crm_log_records': {'tr': 'CRM Aktivite Logu', 'en': 'CRM Activity Log', 'ar': 'سجل أنشطة CRM', 'desc_tr': 'Geciken ve planlanan müşteri aktiviteleri.', 'desc_en': 'Overdue and planned customer activities.', 'chart': 'State', 'value': 'Activity Count'},
    'lead_report': {'tr': 'Lead Raporu', 'en': 'Lead Report', 'ar': 'تقرير العملاء المحتملين', 'desc_tr': 'Lead kaynağı, kampanya, olasılık ve gelir potansiyeli.', 'desc_en': 'Lead source, campaign, probability and revenue potential.', 'chart': 'Source', 'value': 'Expected Revenue'},
    'advertising_leads': {'tr': 'Reklam Leadleri', 'en': 'Advertising Leads', 'ar': 'عملاء الإعلانات', 'desc_tr': 'Reklam kanalı, lead kalitesi ve dönüşüm potansiyeli.', 'desc_en': 'Ad channel, lead quality and conversion potential.', 'chart': 'Campaign', 'value': 'Expected Revenue'},
    'web_form_tracking': {'tr': 'Web Form Takibi', 'en': 'Web Form Tracking', 'ar': 'تتبع نماذج الويب', 'desc_tr': 'Web form kaynaklı lead ve takip performansı.', 'desc_en': 'Web-form lead and follow-up performance.', 'chart': 'Source', 'value': 'Expected Revenue'},
    'project_gdv_analysis': {'tr': 'Proje GDV Analizi', 'en': 'Project GDV Analysis', 'ar': 'تحليل قيمة تطوير المشروع', 'desc_tr': 'Proje brüt geliştirme değeri, satış oranı ve tahsilat.', 'desc_en': 'Gross development value, sell-through and collection.', 'chart': 'Project', 'value': 'List Price'},
    'cash_flow_forecast': {'tr': 'Nakit Akış Tahmini', 'en': 'Cash Flow Forecast', 'ar': 'توقع التدفق النقدي', 'desc_tr': 'Gelecek vade nakit tahmini ve açık risk.', 'desc_en': 'Future due cash forecast and open risk.', 'chart': 'Due Month', 'value': 'Residual'},
    'vat_compliance_audit': {'tr': 'KDV Uyum Denetimi', 'en': 'VAT Compliance Audit', 'ar': 'تدقيق امتثال ضريبة القيمة المضافة', 'desc_tr': 'Net alan, satış bedeli ve teslim durumuna göre KDV metodu ve iade zamanlama riski.', 'desc_en': 'VAT method, tiered base and refund timing risk by unit area, sale price and transfer state.', 'chart': 'VAT Method', 'value': 'Estimated VAT'},
    'fx_contract_compliance': {'tr': 'Döviz Sözleşme Uyum Raporu', 'en': 'FX Contract Compliance', 'ar': 'امتثال عقود العملات الأجنبية', 'desc_tr': 'TRY dışı sözleşme ve tahsilatlarda 32 sayılı karar uyum riski ve istisna göstergesi.', 'desc_en': 'FX-denominated contract and collection compliance risk with exception indicators.', 'chart': 'FX Risk', 'value': 'TRY Equivalent'},
    'title_deed_tax_risk': {'tr': 'Tapu Harcı Risk Raporu', 'en': 'Title Deed Tax Risk', 'ar': 'مخاطر ضريبة الطابو', 'desc_tr': 'Tapu matrahı/satış bedeli farkı, tahmini harç farkı ve ceza önceliği.', 'desc_en': 'Declared deed base versus sale value gap, estimated fee difference and penalty priority.', 'chart': 'Risk Level', 'value': 'Potential Fee Gap'},
    'crm_erp_reconciliation': {'tr': 'CRM / ERP Mutabakat Raporu', 'en': 'CRM / ERP Reconciliation', 'ar': 'مطابقة CRM و ERP', 'desc_tr': 'Sözleşme, ödeme planı, tahsilat ve fatura statüsü arasındaki tutarsızlıklar.', 'desc_en': 'Contract, installment, collection and invoice-status inconsistencies.', 'chart': 'Reconciliation Status', 'value': 'Delta'},
    'showing_document_compliance': {'tr': 'Yer Gösterme Belgesi Uyum Raporu', 'en': 'Showing Document Compliance', 'ar': 'امتثال مستند معاينة العقار', 'desc_tr': 'Lead/randevu kayıtlarında yer gösterme formu kanıtı ve komisyon ispat riski.', 'desc_en': 'Showing-document evidence and commission-proof risk by lead or appointment.', 'chart': 'Compliance Status', 'value': 'Risk Score'},
    'valuation_gedas_readiness': {'tr': 'Değerleme / GEDAS Hazırlık Raporu', 'en': 'Valuation / GEDAS Readiness', 'ar': 'جاهزية التقييم / GEDAS', 'desc_tr': 'Bağımsız bölüm veri tamlığı, fiyat/m2 göstergeleri ve değerleme hazırlık skoru.', 'desc_en': 'Unit data completeness, price-per-square-meter indicators and valuation readiness score.', 'chart': 'Readiness Status', 'value': 'Readiness Score'},
    'rental_portfolio': {'tr': 'Kiralama Portföy Raporu', 'en': 'Rental Portfolio Report', 'ar': 'تقرير محفظة الإيجار', 'desc_tr': 'Kiralanabilir portföy, doluluk ve tahmini kira geliri.', 'desc_en': 'Rentable portfolio, occupancy and estimated rent income.', 'chart': 'Occupancy State', 'value': 'Monthly Rent Estimate'},
    'rental_contracts': {'tr': 'Kira Sözleşmeleri Raporu', 'en': 'Rental Contracts Report', 'ar': 'تقرير عقود الإيجار', 'desc_tr': 'Kira sözleşmesi benzeri portföy ve durum takibi.', 'desc_en': 'Rental-style portfolio and state tracking.', 'chart': 'Rental Status', 'value': 'Sale Price'},
    'rental_collections': {'tr': 'Kira Tahsilat Raporu', 'en': 'Rental Collections Report', 'ar': 'تقرير تحصيل الإيجار', 'desc_tr': 'Kiraya benzer düzenli tahsilat ve yöntem kırılımı.', 'desc_en': 'Recurring rental-like collection and method split.', 'chart': 'Method', 'value': 'Amount'},
    'tenant_landlord': {'tr': 'Kiracı/Mülk Sahibi Raporu', 'en': 'Tenant/Landlord Report', 'ar': 'تقرير المستأجر/المالك', 'desc_tr': 'Müşteri, kiracı/malik rolü, bakiye ve risk bilgisi.', 'desc_en': 'Customer, tenant/owner role, balance and risk.', 'chart': 'Role', 'value': 'Outstanding'},
    'vacancy_occupancy': {'tr': 'Boşluk ve Doluluk Raporu', 'en': 'Vacancy & Occupancy Report', 'ar': 'تقرير الشغور والإشغال', 'desc_tr': 'Boş, opsiyonlu, satılmış/dolu envanter oranı.', 'desc_en': 'Vacant, optioned and occupied inventory ratio.', 'chart': 'Occupancy State', 'value': 'List Price'},
    'unit_profitability': {'tr': 'Birim Karlılık Raporu', 'en': 'Unit Profitability Report', 'ar': 'تقرير ربحية الوحدة', 'desc_tr': 'Birim fiyat, satış, indirim ve tahmini marj.', 'desc_en': 'Unit price, sale, discount and estimated margin.', 'chart': 'Project', 'value': 'Estimated Profit'},
    'broker_commission': {'tr': 'Broker Komisyon Raporu', 'en': 'Broker Commission Report', 'ar': 'تقرير عمولة الوسيط', 'desc_tr': 'Broker/danışman komisyon tahakkuk ve ödeme durumu.', 'desc_en': 'Broker/consultant commission accrual and payment state.', 'chart': 'User', 'value': 'Net Commission'},
    'customer_risk': {'tr': 'Müşteri Risk Raporu', 'en': 'Customer Risk Report', 'ar': 'تقرير مخاطر العميل', 'desc_tr': 'Gecikme, kırmızı alarm ve hukuk takip önceliği.', 'desc_en': 'Overdue, red alert and legal follow-up priority.', 'chart': 'Risk Segment', 'value': 'Residual'},
    'overdue_installments': {'tr': 'Gecikmiş Taksitler Raporu', 'en': 'Overdue Installments Report', 'ar': 'تقرير الأقساط المتأخرة', 'desc_tr': 'Gecikmiş taksitlerin gün, bakiye ve aksiyon listesi.', 'desc_en': 'Overdue installments by days, balance and action list.', 'chart': 'Days Bucket', 'value': 'Residual'},
    'sales_pipeline': {'tr': 'Satış Pipeline Raporu', 'en': 'Sales Pipeline Report', 'ar': 'تقرير مسار المبيعات', 'desc_tr': 'Lead aşaması, olasılık ve beklenen gelir boru hattı.', 'desc_en': 'Lead stage, probability and expected revenue pipeline.', 'chart': 'Stage', 'value': 'Expected Revenue'},
    'reservation_cancellation': {'tr': 'Rezervasyon ve İptal Raporu', 'en': 'Reservation & Cancellation Report', 'ar': 'تقرير الحجز والإلغاء', 'desc_tr': 'Opsiyon, rezervasyon ve iptal riski.', 'desc_en': 'Option, reservation and cancellation risk.', 'chart': 'Cancellation Risk', 'value': 'Sale Price'},
    'project_profitability': {'tr': 'Proje Karlılık Raporu', 'en': 'Project Profitability Report', 'ar': 'تقرير ربحية المشروع', 'desc_tr': 'Proje bazlı satış değeri, tahsilat ve tahmini karlılık.', 'desc_en': 'Project sales value, collection and estimated profitability.', 'chart': 'Project', 'value': 'Estimated Profit'},
    'inventory_aging': {'tr': 'Stok Yaşlandırma Raporu', 'en': 'Inventory Aging Report', 'ar': 'تقرير تقادم المخزون', 'desc_tr': 'Stokta bekleme süresi ve satış önceliği.', 'desc_en': 'Inventory holding age and sales priority.', 'chart': 'Aging Bucket', 'value': 'List Price'},
    'lead_source_roi': {'tr': 'Lead Kaynağı ROI Raporu', 'en': 'Lead Source ROI Report', 'ar': 'تقرير عائد مصادر العملاء', 'desc_tr': 'Lead kaynağına göre potansiyel gelir ve dönüşüm tahmini.', 'desc_en': 'Potential revenue and conversion by lead source.', 'chart': 'Source', 'value': 'Expected Revenue'},
}

CATEGORY_LABELS = {
    'Collection & Payments': {'tr': 'Tahsilat ve Ödemeler', 'en': 'Collection & Payments', 'ar': 'التحصيل والمدفوعات'},
    'Sales Reports': {'tr': 'Satış Raporları', 'en': 'Sales Reports', 'ar': 'تقارير المبيعات'},
    'Customer Reports': {'tr': 'Müşteri Raporları', 'en': 'Customer Reports', 'ar': 'تقارير العملاء'},
    'Financial Reports': {'tr': 'Mali Raporlar', 'en': 'Financial Reports', 'ar': 'التقارير المالية'},
    'Performance Reports': {'tr': 'Performans Raporları', 'en': 'Performance Reports', 'ar': 'تقارير الأداء'},
    'Property Reports': {'tr': 'Gayrimenkul Raporları', 'en': 'Property Reports', 'ar': 'تقارير العقارات'},
    'Admin & Compliance': {'tr': 'Yönetim ve Uyum', 'en': 'Admin & Compliance', 'ar': 'الإدارة والامتثال'},
    'Marketing & Leads': {'tr': 'Pazarlama ve Müşteri Adayları', 'en': 'Marketing & Leads', 'ar': 'التسويق والعملاء المحتملون'},
    'Advanced Analytics': {'tr': 'Gelişmiş Analitik', 'en': 'Advanced Analytics', 'ar': 'تحليلات متقدمة'},
    'Rentals': {'tr': 'Kiralama', 'en': 'Rentals', 'ar': 'الإيجارات'},
}

# Intended display order for category numbering (1..N for categories that have reports).
CATEGORY_ORDER = [
    'Collection & Payments',
    'Sales Reports',
    'Customer Reports',
    'Financial Reports',
    'Performance Reports',
    'Property Reports',
    'Admin & Compliance',
    'Marketing & Leads',
    'Advanced Analytics',
    'Rentals',
]

COLUMN_LABELS = {
    'tr': {
        'Contract': 'Sözleşme', 'Customer': 'Müşteri', 'Project': 'Proje', 'Unit': 'Birim',
        'Salesperson': 'Danışman', 'Description': 'Açıklama', 'Due Date': 'Vade Tarihi',
        'Due Month': 'Vade Ayı', 'Amount': 'Tutar', 'Paid': 'Ödenen', 'Residual': 'Kalan',
        'VAT Net': 'KDV Hariç', 'VAT Amount': 'KDV', 'VAT Included': 'KDV Dahil',
        'Payment Status': 'Ödeme Durumu', 'Overdue Days': 'Gecikme Günü',
        'Collection Priority': 'Tahsilat Önceliği', 'Days Bucket': 'Gün Kovası',
        'Risk Segment': 'Risk Segmenti', 'Legal Follow-up': 'Hukuk Takibi',
        'Action': 'Aksiyon', 'Sale Price': 'Satış Bedeli', 'List Price': 'Liste Fiyatı',
        'Discount': 'İndirim', 'Currency': 'Para Birimi', 'Status': 'Durum',
        'Broker': 'Broker', 'TRY Equivalent': 'TL Karşılığı', 'FX Exposure': 'Kur Riski',
        'Approval Step': 'Onay Adımı', 'Sales Month': 'Satış Ayı', 'Date': 'Tarih',
        'Type': 'Tip', 'State': 'Durum', 'Block': 'Blok', 'Floor': 'Kat',
        'Collected': 'Tahsil Edilen', 'Outstanding': 'Açık Bakiye', 'Receivable': 'Alacak',
        'Sell-through %': 'Satış Oranı %', 'Collection %': 'Tahsilat %',
        'Gross m2': 'Brüt m²', 'Net m2': 'Net m²', 'Inventory Age': 'Stok Yaşı',
        'Aging Bucket': 'Yaşlandırma Kovası', 'Occupancy State': 'Doluluk Durumu',
        'Monthly Rent Estimate': 'Tahmini Aylık Kira', 'Estimated Cost': 'Tahmini Maliyet',
        'Estimated Profit': 'Tahmini Kar', 'Margin %': 'Marj %', 'Title Deed No': 'Tapu No',
        'Title Deed Cost': 'Tapu Maliyeti', 'Invoice': 'Fatura', 'User': 'Kullanıcı',
        'Company': 'Şirket', 'Groups': 'Gruplar', 'Can Manage Reports': 'Rapor Yönetir',
        'Master Admin': 'Master Admin', 'Summary': 'Özet', 'Model': 'Model',
        'Record': 'Kayıt', 'Assigned To': 'Atanan', 'Activity Count': 'Aktivite Adedi',
        'Lead': 'Lead', 'Source': 'Kaynak', 'Campaign': 'Kampanya', 'Stage': 'Aşama',
        'Expected Revenue': 'Beklenen Gelir', 'Probability': 'Olasılık', 'Created': 'Oluşturma',
        'Role': 'Rol', 'Sales Count': 'Satış Adedi', 'Total Sales': 'Toplam Satış',
        'Overdue Items': 'Gecikmiş Kalem', 'Risk': 'Risk', 'Phone': 'Telefon', 'Email': 'E-posta',
        'Receipt': 'Fiş', 'Method': 'Yöntem', 'Exchange Rate': 'Kur', 'Deals': 'Anlaşma',
        'Revenue': 'Ciro', 'Open Balance': 'Açık Bakiye', 'Average Deal': 'Ort. Anlaşma',
        'Confirmed Deals': 'Onaylı Satış', 'GDV': 'GDV', 'Sold Value': 'Satılan Değer',
        'Units': 'Birim', 'Sold Units': 'Satılan Birim', 'Construction %': 'İnşaat %',
        'Period From': 'Dönem Başlangıç', 'Period To': 'Dönem Bitiş',
        'Gross Commission': 'Brüt Komisyon', 'Deductions': 'Kesintiler', 'Net Commission': 'Net Komisyon',
        'City': 'Şehir', 'Total GDV': 'Toplam GDV', 'Sold': 'Satıldı',
        'Category': 'Kategori', 'Medium': 'Kanal', 'Platform': 'Platform',
        'Actual Revenue': 'Gerçekleşen Ciro', 'Target Revenue': 'Hedef Ciro',
        'Lifecycle Node': 'Yaşam Döngüsü', 'RevPAM': 'RevPAM',
        'VAT Method': 'KDV Metodu', 'Estimated VAT': 'Tahmini KDV',
        'FX Risk': 'Kur Riski', 'Risk Level': 'Risk Seviyesi',
        'Potential Fee Gap': 'Potansiyel Harç Farkı', 'Delta': 'Fark',
        'Risk Score': 'Risk Skoru', 'Readiness Score': 'Hazırlık Skoru',
        'Readiness Status': 'Hazırlık Durumu', 'Reconciliation Status': 'Mutabakat Durumu',
        'Compliance Status': 'Uyum Durumu', 'Rental Status': 'Kiralama Durumu',
        'Cancellation Risk': 'İptal Riski',
        'Lead Quality': 'Lead Kalitesi', 'Reservation': 'Rezervasyon',
        'Conversion': 'Dönüşüm', 'TCMB Rate': 'TCMB Kuru',
        'Invoice Status': 'Fatura Durumu', 'Sale': 'Satış',
        'Lead-to-Contract Velocity': 'Lead-Sözleşme Hızı',
        'Discount Variance %': 'İndirim Sapması %',
        'Target vs Actual %': 'Hedef vs Gerçek %',
        'Average Days to Close': 'Ort. Kapanış Günü',
    },
    'ar': {
        'Contract': 'العقد', 'Customer': 'العميل', 'Project': 'المشروع', 'Unit': 'الوحدة',
        'Salesperson': 'المستشار', 'Description': 'الوصف', 'Due Date': 'تاريخ الاستحقاق',
        'Due Month': 'شهر الاستحقاق', 'Amount': 'المبلغ', 'Paid': 'المدفوع', 'Residual': 'المتبقي',
        'VAT Net': 'صافي الضريبة', 'VAT Amount': 'الضريبة', 'VAT Included': 'شامل الضريبة',
        'Payment Status': 'حالة الدفع', 'Overdue Days': 'أيام التأخير',
        'Risk Segment': 'شريحة المخاطر', 'Action': 'الإجراء', 'Sale Price': 'سعر البيع',
        'List Price': 'سعر القائمة', 'Currency': 'العملة', 'Status': 'الحالة',
        'Collected': 'المحصل', 'Outstanding': 'الرصيد المفتوح', 'Receivable': 'ذمم مدينة',
        'Date': 'التاريخ', 'Source': 'المصدر', 'Campaign': 'الحملة', 'Stage': 'المرحلة',
        'Expected Revenue': 'الإيراد المتوقع', 'Probability': 'الاحتمال',
    },
}

FILTER_DEFINITIONS = {
    'date_range': {'key': 'date_range', 'label': 'Dönem', 'type': 'date_range'},
    'fiscal_year': {'key': 'fiscal_year', 'label': 'Mali Yıl', 'type': 'select', 'options_key': 'fiscal_years'},
    'project_id': {'key': 'project_id', 'label': 'Proje', 'type': 'select', 'options_key': 'projects'},
    'block_id': {'key': 'block_id', 'label': 'Blok', 'type': 'select', 'options_key': 'blocks'},
    'unit_type_id': {'key': 'unit_type_id', 'label': 'Birim Tipi', 'type': 'select', 'options_key': 'unit_types'},
    'unit_state': {'key': 'unit_state', 'label': 'Birim Durumu', 'type': 'select', 'options_key': 'unit_states'},
    'occupancy_state': {'key': 'occupancy_state', 'label': 'Doluluk', 'type': 'select', 'options_key': 'occupancy_states'},
    'inventory_age_bucket': {'key': 'inventory_age_bucket', 'label': 'Stok Yaşı', 'type': 'select', 'options_key': 'inventory_age_buckets'},
    'customer_id': {'key': 'customer_id', 'label': 'Müşteri', 'type': 'select', 'options_key': 'customers'},
    'customer_risk': {'key': 'customer_risk', 'label': 'Risk Segmenti', 'type': 'select', 'options_key': 'risk_segments'},
    'customer_role': {'key': 'customer_role', 'label': 'Müşteri Rolü', 'type': 'select', 'options_key': 'customer_roles'},
    'salesperson_id': {'key': 'salesperson_id', 'label': 'Satış Danışmanı', 'type': 'select', 'options_key': 'salespersons'},
    'broker_id': {'key': 'broker_id', 'label': 'Broker', 'type': 'select', 'options_key': 'brokers'},
    'currency_id': {'key': 'currency_id', 'label': 'Para Birimi', 'type': 'select', 'options_key': 'currencies'},
    'sales_status': {'key': 'sales_status', 'label': 'Satış Durumu', 'type': 'select', 'options_key': 'sales_statuses'},
    'approval_step': {'key': 'approval_step', 'label': 'Onay Adımı', 'type': 'select', 'options_key': 'approval_steps'},
    'cancellation_risk': {'key': 'cancellation_risk', 'label': 'İptal Riski', 'type': 'select', 'options_key': 'cancellation_risks'},
    'payment_status': {'key': 'payment_status', 'label': 'Ödeme Durumu', 'type': 'select', 'options_key': 'payment_statuses'},
    'collection_priority': {'key': 'collection_priority', 'label': 'Tahsilat Önceliği', 'type': 'select', 'options_key': 'collection_priorities'},
    'days_bucket': {'key': 'days_bucket', 'label': 'Gün Kovası', 'type': 'select', 'options_key': 'days_buckets'},
    'payment_method': {'key': 'payment_method', 'label': 'Ödeme Yöntemi', 'type': 'select', 'options_key': 'payment_methods'},
    'cash_register': {'key': 'cash_register', 'label': 'Kasa', 'type': 'select', 'options_key': 'cash_registers'},
    'lead_source': {'key': 'lead_source', 'label': 'Lead Kaynağı', 'type': 'select', 'options_key': 'lead_sources'},
    'lead_stage': {'key': 'lead_stage', 'label': 'Lead Aşaması', 'type': 'select', 'options_key': 'lead_stages'},
    'campaign': {'key': 'campaign', 'label': 'Kampanya', 'type': 'select', 'options_key': 'campaigns'},
    'platform': {'key': 'platform', 'label': 'Platform / Kanal', 'type': 'select', 'options_key': 'platforms'},
    'lead_type': {'key': 'lead_type', 'label': 'Lead Tipi', 'type': 'select', 'options_key': 'lead_types'},
    'conversion_status': {'key': 'conversion_status', 'label': 'Dönüşüm', 'type': 'select', 'options_key': 'conversion_statuses'},
    'lead_quality': {'key': 'lead_quality', 'label': 'Lead Kalitesi', 'type': 'select', 'options_key': 'lead_qualities'},
    'compliance_status': {'key': 'compliance_status', 'label': 'Uyum Durumu', 'type': 'select', 'options_key': 'compliance_statuses'},
    'risk_level': {'key': 'risk_level', 'label': 'Risk Seviyesi', 'type': 'select', 'options_key': 'risk_levels'},
    'invoice_status': {'key': 'invoice_status', 'label': 'Fatura Durumu', 'type': 'select', 'options_key': 'invoice_statuses'},
    'reconciliation_status': {'key': 'reconciliation_status', 'label': 'Mutabakat', 'type': 'select', 'options_key': 'reconciliation_statuses'},
    'readiness_status': {'key': 'readiness_status', 'label': 'Hazırlık', 'type': 'select', 'options_key': 'readiness_statuses'},
    'tapu_state': {'key': 'tapu_state', 'label': 'Tapu Durumu', 'type': 'select', 'options_key': 'tapu_states'},
    'rental_status': {'key': 'rental_status', 'label': 'Kiralama Durumu', 'type': 'select', 'options_key': 'rental_statuses'},
    'commission_state': {'key': 'commission_state', 'label': 'Komisyon Durumu', 'type': 'select', 'options_key': 'commission_states'},
}

# Filter label localization (English FILTER_DEFINITIONS labels → UI language).
FILTER_LABELS = {
    'tr': {
        'Period': 'Dönem',
        'Fiscal Year': 'Mali Yıl',
        'Project': 'Proje',
        'Block': 'Blok',
        'Unit Type': 'Birim Tipi',
        'Unit Status': 'Birim Durumu',
        'Occupancy': 'Doluluk',
        'Inventory Age': 'Stok Yaşı',
        'Customer': 'Müşteri',
        'Risk Segment': 'Risk Segmenti',
        'Customer Role': 'Müşteri Rolü',
        'Salesperson': 'Satış Danışmanı',
        'Broker': 'Broker',
        'Currency': 'Para Birimi',
        'Sale Status': 'Satış Durumu',
        'Approval Step': 'Onay Adımı',
        'Cancellation Risk': 'İptal Riski',
        'Payment Status': 'Ödeme Durumu',
        'Collection Priority': 'Tahsilat Önceliği',
        'Days Bucket': 'Gün Kovası',
        'Payment Method': 'Ödeme Yöntemi',
        'Cash Register': 'Kasa',
        'Lead Source': 'Lead Kaynağı',
        'Lead Stage': 'Lead Aşaması',
        'Campaign': 'Kampanya',
        'Platform / Medium': 'Platform / Kanal',
        'Lead Type': 'Lead Tipi',
        'Conversion': 'Dönüşüm',
        'Lead Quality': 'Lead Kalitesi',
        'Compliance Status': 'Uyum Durumu',
        'Risk Level': 'Risk Seviyesi',
        'Invoice Status': 'Fatura Durumu',
        'Reconciliation': 'Mutabakat',
        'Readiness': 'Hazırlık',
        'Title Deed State': 'Tapu Durumu',
        'Rental Status': 'Kiralama Durumu',
        'Commission State': 'Komisyon Durumu',
    },
}

REPORT_FILTER_PROFILES = {
    'collections': ['date_range', 'project_id', 'customer_id', 'salesperson_id', 'payment_status', 'collection_priority', 'days_bucket'],
    'sales': ['date_range', 'project_id', 'unit_type_id', 'customer_id', 'salesperson_id', 'broker_id', 'currency_id', 'sales_status'],
    'inventory': ['project_id', 'block_id', 'unit_type_id', 'unit_state', 'occupancy_state', 'inventory_age_bucket'],
    'customer': ['date_range', 'customer_id', 'customer_risk', 'customer_role', 'salesperson_id'],
    'finance': ['date_range', 'project_id', 'payment_method', 'cash_register', 'currency_id', 'payment_status'],
    'performance': ['date_range', 'salesperson_id', 'project_id', 'sales_status', 'lead_quality'],
    'lead': ['date_range', 'lead_source', 'lead_stage', 'campaign', 'salesperson_id', 'lead_quality'],
    'compliance': ['date_range', 'project_id', 'risk_level', 'compliance_status', 'invoice_status', 'reconciliation_status'],
    'property_compliance': ['date_range', 'project_id', 'block_id', 'unit_type_id', 'tapu_state', 'risk_level', 'readiness_status'],
    'rental': ['project_id', 'block_id', 'unit_type_id', 'occupancy_state', 'rental_status', 'customer_id'],
    'commission': ['date_range', 'salesperson_id', 'broker_id', 'commission_state'],
}

REPORT_SPECIFIC_FILTERS = {
    'advanced_leads_crm_propertio': [
        'date_range', 'salesperson_id', 'project_id', 'lead_source', 'platform',
        'campaign', 'lead_stage', 'lead_type', 'lead_quality', 'conversion_status', 'customer_id',
    ],
    'sales_performance_closer': ['fiscal_year', 'date_range', 'project_id', 'salesperson_id'],
    'occupancy_unit_lifecycle': ['fiscal_year', 'project_id', 'block_id', 'unit_type_id', 'unit_state', 'occupancy_state'],
    'cash_flow_arrears_forensic': ['fiscal_year', 'date_range', 'project_id', 'customer_id', 'salesperson_id', 'payment_status', 'days_bucket'],
    'sales_collection_summary': ['date_range', 'project_id', 'customer_id', 'salesperson_id', 'collection_priority', 'customer_risk'],
    'payment_plan_table': ['date_range', 'project_id', 'customer_id', 'payment_status', 'days_bucket'],
    'expected_payment_list': ['date_range', 'project_id', 'customer_id', 'collection_priority', 'days_bucket'],
    'payment_plan_vat': ['date_range', 'project_id', 'customer_id', 'payment_status', 'currency_id'],
    'incoming_payments_chart': ['date_range', 'project_id', 'payment_status', 'collection_priority'],
    'kirmizi_alarm_musteriler': ['date_range', 'customer_id', 'customer_risk', 'days_bucket'],
    'type_based_sales': ['project_id', 'unit_type_id', 'unit_state', 'occupancy_state'],
    'approval_based_sales': ['date_range', 'project_id', 'approval_step', 'salesperson_id'],
    'total_sales_chart': ['date_range', 'project_id', 'salesperson_id', 'currency_id'],
    'daily_sales_quantity': ['date_range', 'project_id', 'salesperson_id', 'unit_type_id'],
    'sales_exchange_rate': ['date_range', 'project_id', 'currency_id', 'risk_level'],
    'customer_journey_individual': ['customer_id', 'customer_risk', 'salesperson_id'],
    'cash_flow_statement': ['date_range', 'project_id', 'payment_status', 'collection_priority'],
    'daily_cash_register': ['date_range', 'payment_method', 'cash_register', 'currency_id'],
    'cash_register': ['date_range', 'payment_method', 'cash_register', 'customer_id'],
    'employee_performance': ['date_range', 'salesperson_id', 'project_id', 'lead_quality'],
    'end_of_day_meeting': ['date_range', 'salesperson_id', 'lead_stage'],
    'construction_progress': ['project_id', 'block_id', 'unit_state', 'readiness_status'],
    'title_deed_invoice': ['date_range', 'project_id', 'tapu_state', 'risk_level'],
    'authorization_matrix': ['compliance_status', 'risk_level'],
    'crm_log_records': ['date_range', 'salesperson_id', 'compliance_status'],
    'lead_source_roi': ['date_range', 'lead_source', 'campaign', 'lead_quality'],
    'sales_pipeline': ['date_range', 'lead_source', 'lead_stage', 'salesperson_id', 'lead_quality'],
    'inventory_aging': ['project_id', 'block_id', 'unit_type_id', 'inventory_age_bucket'],
    'valuation_gedas_readiness': ['project_id', 'block_id', 'unit_type_id', 'readiness_status'],
    'broker_commission': ['date_range', 'broker_id', 'salesperson_id', 'commission_state'],
}

CHART_PROFILES = {
    'Collection & Payments': {'types': ['bar', 'donut', 'line'], 'groups': ['Project', 'Customer', 'Payment Status', 'Days Bucket', 'Collection Priority'], 'values': ['Residual', 'Amount', 'Paid', 'Overdue Days']},
    'Sales Reports': {'types': ['bar', 'donut', 'line'], 'groups': ['Project', 'Salesperson', 'Status', 'Sales Month', 'Currency', 'Unit'], 'values': ['Sale Price', 'Discount', 'TRY Equivalent', 'FX Exposure']},
    'Customer Reports': {'types': ['donut', 'bar'], 'groups': ['Risk', 'Role', 'Customer', 'Sales Count'], 'values': ['Outstanding', 'Total Sales', 'Collected', 'Overdue Items']},
    'Financial Reports': {'types': ['bar', 'donut', 'line'], 'groups': ['Date', 'Method', 'Currency', 'Project', 'User'], 'values': ['Amount', 'Collected', 'Net Commission', 'Estimated Profit']},
    'Performance Reports': {'types': ['bar', 'donut'], 'groups': ['Salesperson', 'Lead Quality', 'Stage', 'Project'], 'values': ['Deals', 'Revenue', 'Expected Revenue', 'Average Deal']},
    'Property Reports': {'types': ['donut', 'bar'], 'groups': ['Project', 'Block', 'Type', 'State', 'Aging Bucket', 'Readiness Status'], 'values': ['List Price', 'Sold Value', 'Estimated Profit', 'Inventory Age']},
    'Admin & Compliance': {'types': ['donut', 'bar'], 'groups': ['Risk Level', 'Compliance Status', 'Invoice Status', 'Reconciliation Status'], 'values': ['Risk Score', 'Delta', 'Penalty Exposure', 'Estimated VAT']},
    'Marketing & Leads': {'types': ['bar', 'donut'], 'groups': ['Source', 'Campaign', 'Stage', 'Lead Quality', 'Salesperson'], 'values': ['Expected Revenue', 'ROI Proxy']},
    'Advanced Analytics': {'types': ['bar', 'donut'], 'groups': ['Project', 'Readiness Status', 'Aging Bucket'], 'values': ['GDV', 'Estimated Profit', 'Readiness Score', 'Data Completeness %']},
    'Rentals': {'types': ['donut', 'bar'], 'groups': ['Occupancy State', 'Rental Status', 'Project', 'Role'], 'values': ['Monthly Rent Estimate', 'List Price', 'Outstanding']},
}


class PropertioReportTemplate(models.Model):
    _name = 'propertio.report.template'
    _description = 'Propertio saved report template'
    _order = 'is_global desc, name'

    name = fields.Char(required=True)
    report_key = fields.Char(required=True, index=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, index=True)
    is_global = fields.Boolean(string='Global Template')
    shared_user_ids = fields.Many2many('res.users', string='Shared With')
    options_json = fields.Text(default='{}')


class PropertioReportFavorite(models.Model):
    _name = 'propertio.report.favorite'
    _description = 'Propertio report favorite'
    _rec_name = 'report_key'

    report_key = fields.Char(required=True, index=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, index=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    _sql_constraints = [('uniq_report_favorite', 'unique(report_key,user_id,company_id)', 'This report is already a favorite.')]


class PropertioReportAccessLog(models.Model):
    _name = 'propertio.report.access.log'
    _description = 'Propertio report access/export audit log'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    report_key = fields.Char(required=True, index=True)
    report_name = fields.Char()
    action_type = fields.Selection([('view', 'Viewed'), ('export', 'Exported')], required=True, index=True)
    export_format = fields.Char()
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, index=True)
    filters_json = fields.Text()
    row_count = fields.Integer()

    @api.depends('report_key', 'action_type', 'export_format')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s%s' % (rec.report_key, rec.action_type, ('/%s' % rec.export_format) if rec.export_format else '')


class PropertioReportEngine(models.TransientModel):
    _name = 'propertio.report.engine'
    _description = 'Propertio Reports Center Engine'

    @api.model
    def _category_number_map(self, reports=None):
        """Continuous 1..N numbers for categories that have at least one report."""
        catalog = reports if reports is not None else REPORT_CATALOG
        present = {item.get('category') for item in catalog if item.get('category')}
        numbers = {}
        n = 0
        for cat in CATEGORY_ORDER:
            if cat in present:
                n += 1
                numbers[cat] = n
        for cat in sorted(present - set(CATEGORY_ORDER)):
            n += 1
            numbers[cat] = n
        return numbers

    @api.model
    def list_reports(self):
        favorites = set(self.env['propertio.report.favorite'].search([('user_id', '=', self.env.user.id)]).mapped('report_key'))
        recent = self.env['propertio.report.access.log'].search([('user_id', '=', self.env.user.id), ('action_type', '=', 'view')], limit=8).mapped('report_key')
        templates = self._template_payload()
        category_numbers = self._category_number_map()
        # Sequential report index within each category (catalog order)
        report_seq = {}
        reports = []
        for item in REPORT_CATALOG:
            payload = self._localize_report(item, category_numbers=category_numbers, report_seq=report_seq)
            payload['favorite'] = payload['key'] in favorites
            payload['template_count'] = len([t for t in templates if t['report_key'] == payload['key']])
            reports.append(payload)
        return {'reports': reports, 'recent': list(dict.fromkeys(recent)), 'templates': templates}

    @api.model
    def get_filter_options(self):
        def options(model, label='name', domain=None, limit=120):
            if model not in self.env:
                return []
            recs = self.env[model].search(self._company_domain(model, domain or []), order=label if label in self.env[model]._fields else 'id', limit=limit)
            return [{'id': r.id, 'name': r.display_name} for r in recs]

        return {
            'fiscal_years': [{'id': y, 'name': str(y)} for y in range(date.today().year + 1, date.today().year - 6, -1)],
            'projects': options('propertio.project'),
            'blocks': options('propertio.block'),
            'unit_types': options('propertio.unit.category'),
            'customers': options('res.partner', domain=[('is_company', '=', False)]),
            'salespersons': options('res.users'),
            'brokers': options('res.partner', domain=[('is_company', '=', True)]),
            'currencies': options('res.currency', 'name'),
            'sales_statuses': [
                {'id': 'draft', 'name': _('Taslak')},
                {'id': 'confirmed', 'name': _('Onaylandı')},
                {'id': 'cancel', 'name': _('İptal Edildi')},
                {'id': 'refund', 'name': _('İade')},
            ],
            'platforms': options('utm.medium') if 'utm.medium' in self.env else [
                {'id': 'instagram', 'name': 'Instagram'},
                {'id': 'facebook', 'name': 'Facebook'},
                {'id': 'meta', 'name': 'Meta'},
                {'id': 'web', 'name': 'Web'},
            ],
            'lead_types': [
                {'id': 'lead', 'name': _('Lead')},
                {'id': 'opportunity', 'name': _('Fırsat')},
            ],
            'conversion_statuses': [
                {'id': 'open', 'name': _('Açık')},
                {'id': 'reserved', 'name': _('Rezerve')},
                {'id': 'sold', 'name': _('Satıldı')},
                {'id': 'won', 'name': _('Satış Yapıldı')},
                {'id': 'lost', 'name': _('Kaybedildi')},
                {'id': 'cancelled', 'name': _('İptal / İade')},
            ],
            'payment_statuses': [{'id': 'paid', 'name': _('Ödendi')}, {'id': 'overdue', 'name': _('Gecikmiş')}, {'id': 'upcoming', 'name': _('Yaklaşan')}, {'id': 'future', 'name': _('İleri Tarihli')}],
            'unit_states': [{'id': 'available', 'name': _('Müsait')}, {'id': 'option', 'name': _('Opsiyon')}, {'id': 'sold', 'name': _('Satıldı')}, {'id': 'handover', 'name': _('Teslim')}],
            'occupancy_states': [{'id': 'Boş', 'name': _('Vacant')}, {'id': 'Opsiyonlu', 'name': _('Optioned')}, {'id': 'Dolu/Satıldı', 'name': _('Occupied / Sold')}],
            'inventory_age_buckets': [{'id': 'Yeni Stok', 'name': _('New Stock')}, {'id': '30-89 gün', 'name': _('30-89 days')}, {'id': '90-179 gün', 'name': _('90-179 days')}, {'id': '180+ gün', 'name': _('180+ days')}],
            'risk_segments': [{'id': 'Low', 'name': _('Low')}, {'id': 'Medium', 'name': _('Medium')}, {'id': 'High', 'name': _('High')}, {'id': 'Normal', 'name': _('Normal')}, {'id': 'Yakın Takip', 'name': _('Watch')}, {'id': 'Kırmızı Alarm', 'name': _('Red Alert')}],
            'customer_roles': [{'id': 'Buyer', 'name': _('Buyer')}, {'id': 'Tenant', 'name': _('Tenant')}, {'id': 'Landlord', 'name': _('Landlord')}, {'id': 'Lead', 'name': _('Lead')}],
            'approval_steps': [{'id': 'draft', 'name': _('Draft')}, {'id': 'confirmed', 'name': _('Confirmed')}, {'id': 'cancel', 'name': _('Cancelled')}],
            'cancellation_risks': [{'id': 'Low', 'name': _('Low')}, {'id': 'Medium', 'name': _('Medium')}, {'id': 'High', 'name': _('High')}],
            'collection_priorities': [{'id': 'Bugün ara', 'name': _('Call today')}, {'id': 'Bu hafta takip', 'name': _('Follow this week')}, {'id': 'Kapandı', 'name': _('Closed')}],
            'days_buckets': [{'id': 'Vadesinde', 'name': _('On time')}, {'id': '1-29 gün', 'name': _('1-29 days')}, {'id': '30-59 gün', 'name': _('30-59 days')}, {'id': '60+ gün', 'name': _('60+ days')}],
            'payment_methods': [{'id': 'cash', 'name': _('Cash')}, {'id': 'bank', 'name': _('Bank')}, {'id': 'credit_card', 'name': _('Credit Card')}, {'id': 'check', 'name': _('Check')}],
            'cash_registers': options('propertio.cash.register') if 'propertio.cash.register' in self.env else [{'id': 'A', 'name': 'A'}, {'id': 'B', 'name': 'B'}],
            'lead_sources': options('utm.source') if 'utm.source' in self.env else [],
            'lead_stages': options('crm.stage') if 'crm.stage' in self.env else [],
            'campaigns': options('utm.campaign') if 'utm.campaign' in self.env else [],
            'lead_qualities': [{'id': 'Sıcak', 'name': _('Hot')}, {'id': 'Ilık', 'name': _('Warm')}, {'id': 'Soğuk', 'name': _('Cold')}],
            'compliance_statuses': [{'id': 'Complete', 'name': _('Complete')}, {'id': 'Partial', 'name': _('Partial')}, {'id': 'Missing Evidence', 'name': _('Missing Evidence')}, {'id': 'Needs Review', 'name': _('Needs Review')}, {'id': 'OK', 'name': _('OK')}],
            'risk_levels': [{'id': 'Low', 'name': _('Low')}, {'id': 'Medium', 'name': _('Medium')}, {'id': 'High', 'name': _('High')}],
            'invoice_statuses': [{'id': 'not_set', 'name': _('Not Set')}, {'id': 'to_invoice', 'name': _('To Invoice')}, {'id': 'invoiced', 'name': _('Invoiced')}],
            'reconciliation_statuses': [{'id': 'OK', 'name': _('OK')}, {'id': 'Needs Review', 'name': _('Needs Review')}],
            'readiness_statuses': [{'id': 'Ready', 'name': _('Ready')}, {'id': 'Needs Data', 'name': _('Needs Data')}, {'id': 'Incomplete', 'name': _('Incomplete')}],
            'tapu_states': [{'id': 'draft', 'name': _('Draft')}, {'id': 'ready', 'name': _('Ready')}, {'id': 'transferred', 'name': _('Transferred')}],
            'rental_statuses': [{'id': 'Active', 'name': _('Active')}, {'id': 'Ending Soon', 'name': _('Ending Soon')}, {'id': 'Expired', 'name': _('Expired')}, {'id': 'Vacant', 'name': _('Vacant')}],
            'commission_states': [{'id': 'draft', 'name': _('Draft')}, {'id': 'confirmed', 'name': _('Confirmed')}, {'id': 'paid', 'name': _('Paid')}],
        }

    @api.model
    def run_report(self, report_key, filters=None, options=None):
        report = self._get_report(report_key)
        filters = self._normalize_filters(filters or {})
        options = options or {}
        columns, rows = self._build_rows(report, filters, options)
        columns, rows = self._apply_report_profile(report, columns, rows)
        if options.get('columns'):
            wanted = [c for c in options['columns'] if c in [col['key'] for col in columns]]
            columns = [c for c in columns if c['key'] in wanted]
            rows = [{k: v for k, v in row.items() if k in wanted or k.startswith('_')} for row in rows]
        rows = self._sort_rows(rows, options.get('sort_by'), options.get('sort_dir'))
        groups = self._group_rows(rows, columns, options.get('group_by'))
        totals = self._totals(rows, columns)
        kpis = self._kpis(rows, totals)
        chart = self._chart(rows, columns, options.get('group_by'), report, options)
        self._log(report, 'view', None, filters, len(rows))
        return {
            'report': report,
            'columns': columns,
            'rows': rows if options.get('full_export') else rows[:500],
            'row_count': len(rows),
            'totals': totals,
            'kpis': kpis,
            'groups': groups,
            'chart': chart,
            'chart_config': {
                'type': options.get('chart_type') or (report.get('chart_options') or {}).get('types', ['bar'])[0],
                'group_by': options.get('chart_group_by') or options.get('group_by') or report.get('chart_axis'),
                'value': options.get('chart_value') or report.get('chart_value'),
            },
            'export_formats': ['csv', 'xlsx', 'html', 'pdf', 'docx'],
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
        }

    @api.model
    def toggle_favorite(self, report_key):
        fav = self.env['propertio.report.favorite'].search([('report_key', '=', report_key), ('user_id', '=', self.env.user.id)], limit=1)
        if fav:
            fav.unlink()
            return False
        self.env['propertio.report.favorite'].create({'report_key': report_key})
        return True

    @api.model
    def save_template(self, report_key, name, options, is_global=False, template_id=False):
        if is_global and not self.env.user.has_group('base.group_system'):
            raise UserError(_('Only the TCRM master administrator can save global report templates.'))
        vals = {
            'name': name,
            'report_key': report_key,
            'options_json': json.dumps(options or {}, default=str),
            'is_global': bool(is_global),
        }
        if template_id:
            template = self.env['propertio.report.template'].browse(int(template_id)).exists()
            self._check_template_access(template)
            template.write(vals)
        else:
            template = self.env['propertio.report.template'].create(vals)
        return self._serialize_template(template)

    @api.model
    def duplicate_template(self, template_id):
        template = self.env['propertio.report.template'].browse(int(template_id)).exists()
        self._check_template_access(template)
        return self._serialize_template(template.copy({'name': _('%s (Copy)') % template.name, 'is_global': False, 'user_id': self.env.user.id}))

    @api.model
    def delete_template(self, template_id):
        template = self.env['propertio.report.template'].browse(int(template_id)).exists()
        self._check_template_access(template, write=True)
        template.unlink()
        return True

    @api.model
    def open_drilldown_action(self, report_key, ids):
        report = self._get_report(report_key)
        model = report.get('drill_model') or report.get('model')
        return {
            'type': 'ir.actions.act_window',
            'name': report['name'],
            'res_model': model,
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', [int(i) for i in ids])],
            'target': 'current',
        }

    def export_bytes(self, report_key, fmt, filters=None, options=None):
        export_options = dict(options or {})
        export_options['full_export'] = True
        payload = self.run_report(report_key, filters or {}, export_options)
        report = payload['report']
        columns = payload['columns']
        rows = payload['rows']
        self._log(report, 'export', fmt, filters or {}, payload['row_count'])
        if fmt == 'csv':
            return self._export_csv(report, columns, rows), 'text/csv; charset=utf-8', 'csv'
        if fmt == 'xlsx':
            return self._export_xlsx(report, columns, rows, payload), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx'
        if fmt == 'html':
            return self._export_html(report, columns, rows, payload).encode('utf-8'), 'text/html; charset=utf-8', 'html'
        if fmt == 'pdf':
            return self._export_pdf(report, columns, rows, payload), 'application/pdf', 'pdf'
        if fmt == 'docx':
            return self._export_html(report, columns, rows, payload).encode('utf-8'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'doc'
        raise UserError(_('Unsupported export format.'))

    def _get_report(self, key):
        category_numbers = self._category_number_map()
        for report in REPORT_CATALOG:
            if report['key'] == key:
                return self._localize_report(report, category_numbers=category_numbers)
        raise UserError(_('Unknown report: %s') % key)

    def _lang(self):
        lang = (self.env.context.get('lang') or self.env.user.lang or 'en_US').lower()
        if lang.startswith('tr'):
            return 'tr'
        if lang.startswith('ar'):
            return 'ar'
        return 'en'

    def _localize_report(self, report, category_numbers=None, report_seq=None):
        payload = dict(report)
        lang = self._lang()
        profile = REPORT_LOCALIZATION.get(payload['key'], {})
        payload['name_en'] = profile.get('en') or payload.get('name')
        payload['name_tr'] = profile.get('tr') or payload.get('name_tr') or payload.get('name')
        payload['name_ar'] = profile.get('ar') or payload.get('name')
        # Clean names without hardcoded number prefixes
        payload['name'] = profile.get(lang) or profile.get('en') or payload.get('name')
        payload['description'] = profile.get('desc_%s' % lang) or profile.get('desc_en') or payload.get('description') or ''
        category_profile = CATEGORY_LABELS.get(payload.get('category'), {})
        base_category_label = category_profile.get(lang) or payload.get('category')
        if category_numbers is None:
            category_numbers = self._category_number_map()
        cat_key = payload.get('category')
        category_number = category_numbers.get(cat_key)
        payload['category_number'] = category_number
        if category_number:
            payload['category_label'] = '%s. %s' % (category_number, base_category_label)
        else:
            payload['category_label'] = base_category_label
        if report_seq is not None and cat_key:
            report_seq[cat_key] = report_seq.get(cat_key, 0) + 1
            payload['report_number'] = report_seq[cat_key]
        payload['properties'] = self._report_properties(payload)
        payload['chart_axis'] = profile.get('chart')
        payload['chart_value'] = profile.get('value')
        payload['filter_fields'] = self._report_filter_fields(payload)
        payload['chart_options'] = self._report_chart_options(payload)
        return payload

    def _report_filter_fields(self, report):
        keys = REPORT_SPECIFIC_FILTERS.get(report['key'])
        if not keys:
            category = report.get('category')
            if category == 'Collection & Payments':
                keys = REPORT_FILTER_PROFILES['collections']
            elif category == 'Sales Reports':
                keys = REPORT_FILTER_PROFILES['sales']
            elif category == 'Customer Reports':
                keys = REPORT_FILTER_PROFILES['customer']
            elif category == 'Financial Reports':
                keys = REPORT_FILTER_PROFILES['finance']
            elif category == 'Performance Reports':
                keys = REPORT_FILTER_PROFILES['performance']
            elif category == 'Property Reports':
                keys = REPORT_FILTER_PROFILES['property_compliance'] if report['key'] in ('title_deed_tax_risk', 'title_deed_invoice') else REPORT_FILTER_PROFILES['inventory']
            elif category == 'Admin & Compliance':
                keys = REPORT_FILTER_PROFILES['compliance']
            elif category == 'Marketing & Leads':
                keys = REPORT_FILTER_PROFILES['lead']
            elif category == 'Rentals':
                keys = REPORT_FILTER_PROFILES['rental']
            elif category == 'Advanced Analytics':
                keys = REPORT_FILTER_PROFILES['property_compliance']
            else:
                keys = ['date_range']
        if not report.get('date_field'):
            keys = [key for key in keys if key != 'date_range']
        labels = FILTER_LABELS.get(self._lang(), {})
        fields = []
        for key in keys:
            if key not in FILTER_DEFINITIONS:
                continue
            field = dict(FILTER_DEFINITIONS[key])
            field['label'] = labels.get(field['label'], field['label'])
            fields.append(field)
        return fields

    def _report_chart_options(self, report):
        if report['key'] == 'sales_performance_closer':
            return {'types': ['bar', 'line', 'pie', 'radar', 'funnel'], 'groups': ['Salesperson', 'Stage', 'Sales Month'], 'values': ['Actual Revenue', 'Target Revenue', 'Lead-to-Contract Velocity', 'Discount Variance %']}
        if report['key'] == 'occupancy_unit_lifecycle':
            return {'types': ['bar', 'line', 'pie', 'sunburst'], 'groups': ['Lifecycle Node', 'Project', 'Floor', 'Occupancy State'], 'values': ['RevPAM', 'Maintenance Cost-to-Income %', 'Portfolio Turnover %']}
        if report['key'] == 'cash_flow_arrears_forensic':
            return {'types': ['bar', 'line', 'pie', 'gauge', 'donut'], 'groups': ['Aging Bucket', 'Project', 'Customer'], 'values': ['Residual', 'DSO', 'CEI %', 'Weighted Average Delinquency']}
        profile = CHART_PROFILES.get(report.get('category'), CHART_PROFILES['Sales Reports'])
        groups = list(dict.fromkeys([report.get('chart_axis')] + profile.get('groups', []))) if report.get('chart_axis') else profile.get('groups', [])
        values = list(dict.fromkeys([report.get('chart_value')] + profile.get('values', []))) if report.get('chart_value') else profile.get('values', [])
        return {
            'types': profile.get('types', ['bar', 'donut']),
            'groups': [g for g in groups if g],
            'values': [v for v in values if v],
        }

    def _report_properties(self, report):
        key = report['key']
        base = [_('Tenant isolated'), _('Drill-down enabled'), _('CSV/XLSX/HTML/PDF/Word export')]
        if key in ('payment_plan_table', 'expected_payment_list', 'payment_plan_vat', 'overdue_installments', 'customer_risk', 'kirmizi_alarm_musteriler'):
            return base + [_('Receivable aging'), _('Legal collection priority'), _('VAT-aware totals')]
        if key in ('sales_report', 'sales_exchange_rate', 'reservation_cancellation', 'approval_based_sales'):
            return base + [_('Contract profitability'), _('Broker and consultant tracking'), _('FX exposure')]
        if key in ('project_gdv_analysis', 'project_profitability', 'proje_nakit_durumu', 'construction_progress'):
            return base + [_('GDV and sell-through'), _('Project cash position'), _('Inventory monetization')]
        if key in ('advanced_leads_crm_propertio', 'lead_report', 'advertising_leads', 'web_form_tracking', 'lead_source_roi', 'sales_pipeline'):
            return base + [_('Lead source quality'), _('Campaign ROI proxy'), _('Pipeline conversion'), _('CRM + Propertio bridge')]
        if key in ('rental_portfolio', 'rental_contracts', 'rental_collections', 'tenant_landlord', 'vacancy_occupancy'):
            return base + [_('Occupancy view'), _('Rental income proxy'), _('Tenant/landlord segmentation')]
        if key in ('vat_compliance_audit', 'fx_contract_compliance', 'title_deed_tax_risk', 'crm_erp_reconciliation', 'showing_document_compliance', 'valuation_gedas_readiness'):
            return base + [_('Turkey compliance checks'), _('Risk scoring'), _('Audit-ready export')]
        return base + [_('Operational KPIs'), _('Management summary')]

    def _normalize_filters(self, filters):
        out = dict(filters or {})
        if out.get('fiscal_year') and not out.get('date_from') and not out.get('date_to'):
            try:
                year = int(out['fiscal_year'])
                out['date_from'] = '%s-01-01' % year
                out['date_to'] = '%s-12-31' % year
            except (TypeError, ValueError):
                pass
        for key in ('project_id', 'block_id', 'unit_type_id', 'customer_id', 'salesperson_id', 'broker_id', 'currency_id'):
            value = out.get(key)
            if isinstance(value, str) and value.isdigit():
                out[key] = int(value)
        return out

    def _company_domain(self, model_name, domain):
        domain = list(domain or [])
        if model_name in self.env and 'company_id' in self.env[model_name]._fields:
            domain.append(('company_id', 'in', self.env.companies.ids))
        return domain

    def _build_domain(self, report, filters):
        domain = list(report.get('domain') or [])
        date_field = report.get('date_field')
        model_name = report['model']
        fields_map = self.env[model_name]._fields
        if date_field and date_field in fields_map:
            if filters.get('date_from'):
                domain.append((date_field, '>=', filters['date_from']))
            if filters.get('date_to'):
                domain.append((date_field, '<=', filters['date_to']))
        mapping = [
            ('project_id', 'project_id'), ('block_id', 'block_id'), ('unit_type_id', 'category_id'),
            ('customer_id', 'partner_id'), ('salesperson_id', 'sales_person_id'), ('broker_id', 'agency_id'),
            ('currency_id', 'currency_id'), ('sales_status', 'state'), ('payment_status', 'payment_status'),
            ('unit_state', 'state'),
        ]
        for filter_key, field_name in mapping:
            value = filters.get(filter_key)
            if value not in (None, False, '') and field_name in fields_map:
                domain.append((field_name, '=', value))
            elif value not in (None, False, '') and filter_key == 'unit_type_id' and 'property_category_id' in fields_map:
                domain.append(('property_category_id', '=', value))
            elif value not in (None, False, '') and filter_key == 'salesperson_id' and 'user_id' in fields_map:
                domain.append(('user_id', '=', value))
        # CRM lead specific filters
        if model_name == 'crm.lead':
            if filters.get('lead_source') and 'source_id' in fields_map:
                domain.append(('source_id', '=', filters['lead_source']))
            if filters.get('campaign') and 'campaign_id' in fields_map:
                domain.append(('campaign_id', '=', filters['campaign']))
            if filters.get('lead_stage') and 'stage_id' in fields_map:
                domain.append(('stage_id', '=', filters['lead_stage']))
            if filters.get('platform') and 'medium_id' in fields_map:
                domain.append(('medium_id', '=', filters['platform']))
            if filters.get('lead_type') in ('lead', 'opportunity') and 'type' in fields_map:
                domain.append(('type', '=', filters['lead_type']))
            if filters.get('project_id') and 'propertio_project_id' in fields_map:
                domain.append(('propertio_project_id', '=', filters['project_id']))
            if filters.get('customer_id') and 'partner_id' in fields_map:
                domain.append(('partner_id', '=', filters['customer_id']))
        return self._company_domain(model_name, domain)

    def _row_passes_filters(self, row, filters):
        checks = {
            'occupancy_state': 'Occupancy State',
            'inventory_age_bucket': 'Aging Bucket',
            'customer_risk': 'Risk Segment',
            'customer_role': 'Role',
            'approval_step': 'Approval Step',
            'cancellation_risk': 'Cancellation Risk',
            'collection_priority': 'Collection Priority',
            'days_bucket': 'Days Bucket',
            'lead_quality': 'Lead Quality',
            'conversion_status': '_conversion_key',
            'platform': 'Platform',
            'compliance_status': 'Compliance Status',
            'risk_level': 'Risk Level',
            'invoice_status': 'Invoice Status',
            'reconciliation_status': 'Reconciliation Status',
            'readiness_status': 'Readiness Status',
            'tapu_state': 'State',
            'rental_status': 'Rental Status',
            'commission_state': 'State',
            'payment_method': 'Method',
            'cash_register': 'Register',
        }
        for filter_key, column in checks.items():
            value = filters.get(filter_key)
            if value not in (None, False, '') and str(row.get(column, '')) != str(value):
                return False
        return True

    def _filter_rows(self, rows, filters):
        return [row for row in rows if self._row_passes_filters(row, filters)]

    def _apply_report_profile(self, report, columns, rows):
        key = report['key']
        if key in ('payment_plan_table', 'expected_payment_list', 'payment_plan_vat', 'incoming_payments_chart', 'cash_flow_statement', 'cash_flow_forecast', 'customer_risk', 'overdue_installments', 'gelecek_nakit_akisi', 'kirmizi_alarm_musteriler'):
            if key == 'payment_plan_vat':
                wanted = ['Contract', 'Customer', 'Project', 'Salesperson', 'Description', 'Due Date', 'Due Month', 'VAT Net', 'VAT Amount', 'VAT Included', 'Paid', 'Residual', 'Payment Status']
            elif key in ('customer_risk', 'overdue_installments', 'kirmizi_alarm_musteriler'):
                wanted = ['Customer', 'Contract', 'Project', 'Due Date', 'Amount', 'Paid', 'Residual', 'Overdue Days', 'Days Bucket', 'Risk Segment', 'Legal Follow-up', 'Action']
            elif key in ('cash_flow_statement', 'cash_flow_forecast', 'incoming_payments_chart', 'gelecek_nakit_akisi'):
                wanted = ['Due Month', 'Project', 'Contract', 'Customer', 'Amount', 'Paid', 'Residual', 'Payment Status', 'Collection Priority']
            else:
                wanted = ['Contract', 'Customer', 'Project', 'Salesperson', 'Description', 'Due Date', 'Amount', 'Paid', 'Residual', 'Payment Status', 'Overdue Days', 'Collection Priority']
            return self._profile_columns(wanted), rows
        if key in ('sales_report', 'approval_based_sales', 'total_sales_chart', 'daily_sales_quantity', 'sales_status', 'sales_exchange_rate', 'rental_contracts', 'reservation_cancellation'):
            wanted = ['Date', 'Sales Month', 'Contract', 'Customer', 'Project', 'Unit', 'Salesperson', 'Broker', 'Currency', 'List Price', 'Sale Price', 'Discount', 'TRY Equivalent', 'FX Exposure', 'Approval Step', 'Cancellation Risk', 'Status']
            if key == 'sales_exchange_rate':
                wanted = ['Date', 'Contract', 'Customer', 'Project', 'Currency', 'Sale Price', 'TCMB Rate', 'TRY Equivalent', 'FX Exposure']
            if key == 'reservation_cancellation':
                wanted = ['Date', 'Contract', 'Customer', 'Project', 'Unit', 'Reservation Date', 'Cancellation Risk', 'Sale Price', 'Status', 'Action']
            if key == 'rental_contracts':
                wanted = ['Date', 'Contract', 'Customer', 'Project', 'Unit', 'Rental Status', 'Sale Price', 'Outstanding', 'Action']
            return self._profile_columns(wanted), rows
        if key in ('type_based_sales', 'project_gdv_analysis', 'proje_nakit_durumu', 'independent_units', 'rental_portfolio', 'vacancy_occupancy', 'unit_profitability', 'project_profitability', 'inventory_aging'):
            wanted = ['Project', 'Block', 'Unit', 'Type', 'Floor', 'State', 'Occupancy State', 'List Price', 'Sold Value', 'Collected', 'Receivable', 'Sell-through %', 'Monthly Rent Estimate', 'Estimated Cost', 'Estimated Profit', 'Margin %', 'Inventory Age', 'Aging Bucket', 'Tapu Ref']
            if key == 'inventory_aging':
                wanted = ['Project', 'Block', 'Unit', 'Type', 'State', 'List Price', 'Inventory Age', 'Aging Bucket', 'Action']
            if key in ('rental_portfolio', 'vacancy_occupancy'):
                wanted = ['Project', 'Block', 'Unit', 'Type', 'Occupancy State', 'Monthly Rent Estimate', 'List Price', 'State', 'Action']
            return self._profile_columns(wanted), rows
        if key in ('customer_journey', 'customer_journey_individual', 'customer_overall_status', 'tenant_landlord'):
            return self._profile_columns(['Customer', 'Role', 'Phone', 'Email', 'Sales Count', 'Total Sales', 'Collected', 'Outstanding', 'Overdue Items', 'Risk', 'Action']), rows
        if key == 'advanced_leads_crm_propertio':
            return self._profile_columns([
                'Created', 'Lead', 'Customer', 'Phone', 'Source', 'Platform', 'Campaign',
                'Salesperson', 'Project', 'Unit', 'Stage', 'Type', 'Expected Revenue',
                'Lead Quality', 'Reservation', 'Contract', 'Conversion', 'Action',
            ]), rows
        if key in ('lead_report', 'advertising_leads', 'web_form_tracking', 'sales_pipeline', 'lead_source_roi'):
            return self._profile_columns(['Created', 'Lead', 'Customer', 'Source', 'Campaign', 'Salesperson', 'Stage', 'Expected Revenue', 'Lead Quality', 'ROI Proxy', 'Action']), rows
        if key == 'vat_compliance_audit':
            return self._profile_columns(['Date', 'Contract', 'Customer', 'Project', 'Unit', 'Net m2', 'Sale Price', 'VAT Method', 'Low Rate Base', 'High Rate Base', 'Estimated VAT', 'Refund Timing', 'Risk Level', 'Action']), rows
        if key == 'fx_contract_compliance':
            return self._profile_columns(['Date', 'Contract', 'Customer', 'Nationality', 'Currency', 'Sale Price', 'TCMB Rate', 'TRY Equivalent', 'Payment FX Count', 'FX Risk', 'Exception Basis', 'Action']), rows
        if key == 'title_deed_tax_risk':
            return self._profile_columns(['Date', 'Sale', 'Customer', 'Unit', 'Sale Price', 'Declared Deed Base', 'Declared Ratio %', 'Potential Fee Gap', 'Penalty Exposure', 'Risk Level', 'Action']), rows
        if key == 'crm_erp_reconciliation':
            return self._profile_columns(['Date', 'Contract', 'Customer', 'Project', 'Sale Price', 'Plan Total', 'Collected CRM', 'Posted ERP', 'Delta', 'Invoice Status', 'Reconciliation Status', 'Action']), rows
        if key == 'showing_document_compliance':
            return self._profile_columns(['Created', 'Lead', 'Customer', 'Phone', 'Salesperson', 'Stage', 'Showing Evidence', 'Compliance Status', 'Risk Score', 'Action']), rows
        if key == 'valuation_gedas_readiness':
            return self._profile_columns(['Project', 'Block', 'Unit', 'Type', 'Gross m2', 'Net m2', 'Efficiency %', 'List Price', 'Price / Net m2', 'Tapu Ref', 'Data Completeness %', 'Readiness Score', 'Readiness Status', 'Action']), rows
        return columns, rows

    def _profile_columns(self, keys):
        return self._cols(keys)

    def _build_rows(self, report, filters, options):
        key = report['key']
        if key == 'sales_performance_closer':
            return self._sales_performance_closer_rows(report, filters)
        if key == 'occupancy_unit_lifecycle':
            return self._occupancy_unit_lifecycle_rows(report, filters)
        if key == 'cash_flow_arrears_forensic':
            return self._cash_flow_arrears_forensic_rows(report, filters, options)
        if key in ('sales_collection_summary', 'tahsilat_satis_durumu'):
            return self._sale_collection_rows(report, filters)
        if key in ('payment_plan_table', 'expected_payment_list', 'payment_plan_vat', 'incoming_payments_chart', 'cash_flow_statement', 'cash_flow_forecast', 'customer_risk', 'overdue_installments', 'gelecek_nakit_akisi', 'kirmizi_alarm_musteriler'):
            cols, rows = self._installment_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key in ('type_based_sales', 'project_gdv_analysis', 'proje_nakit_durumu', 'independent_units', 'rental_portfolio', 'vacancy_occupancy', 'unit_profitability', 'project_profitability', 'inventory_aging'):
            cols, rows = self._unit_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key in ('customer_journey', 'customer_journey_individual', 'customer_overall_status', 'tenant_landlord'):
            cols, rows = self._customer_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key in ('cash_register', 'daily_cash_register', 'rental_collections'):
            cols, rows = self._payment_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key in ('employee_performance', 'end_of_day_meeting', 'danisman_karnesi', 'danisman_karnesi_bu_ay'):
            local_filters = dict(filters)
            if key == 'danisman_karnesi_bu_ay':
                today = date.today()
                local_filters.update({'date_from': today.replace(day=1).isoformat(), 'date_to': today.isoformat()})
            cols, rows = self._performance_rows(report, local_filters)
            return cols, self._filter_rows(rows, filters)
        if key in ('sales_report', 'approval_based_sales', 'total_sales_chart', 'daily_sales_quantity', 'sales_status', 'sales_exchange_rate', 'rental_contracts', 'reservation_cancellation'):
            cols, rows = self._sales_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'advanced_leads_crm_propertio':
            cols, rows = self._advanced_leads_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key in ('lead_report', 'advertising_leads', 'web_form_tracking', 'sales_pipeline', 'lead_source_roi'):
            cols, rows = self._lead_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'vat_compliance_audit':
            cols, rows = self._vat_compliance_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'fx_contract_compliance':
            cols, rows = self._fx_compliance_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'title_deed_tax_risk':
            cols, rows = self._title_deed_tax_risk_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'crm_erp_reconciliation':
            cols, rows = self._crm_erp_reconciliation_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'showing_document_compliance':
            cols, rows = self._showing_document_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'valuation_gedas_readiness':
            cols, rows = self._valuation_readiness_rows(report, filters)
            return cols, self._filter_rows(rows, filters)
        if key == 'authorization_matrix':
            return self._authorization_rows(report, filters)
        if key == 'crm_log_records':
            return self._activity_rows(report, filters)
        if key == 'title_deed_invoice':
            return self._title_deed_rows(report, filters)
        if key == 'construction_progress':
            return self._project_rows(report, filters)
        if key == 'broker_commission':
            return self._commission_rows(report, filters)
        return self._generic_rows(report, filters)

    def _sales_performance_closer_rows(self, report, filters):
        cols = self._cols(['Salesperson', 'Deals', 'Target Revenue', 'Actual Revenue', 'Target vs Actual %', 'Average Days to Close', 'Lead-to-Contract Velocity', 'Discount Variance %', 'Stage', 'Sales Month'])
        stats = defaultdict(lambda: {'ids': [], 'deals': 0, 'actual': 0.0, 'list': 0.0, 'discount': 0.0, 'days': 0.0})
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters), order='date_sale desc'):
            key = sale.sales_person_id.display_name or _('Unassigned')
            list_price = sale.unit_id.list_price or sale.sale_price or 0.0
            close_days = (sale.date_sale - sale.create_date.date()).days if sale.date_sale and sale.create_date else 0
            stats[key]['ids'].append(sale.id)
            stats[key]['deals'] += 1
            stats[key]['actual'] += sale.sale_price or 0.0
            stats[key]['list'] += list_price
            stats[key]['discount'] += max(list_price - (sale.sale_price or 0.0), 0.0)
            stats[key]['days'] += max(close_days, 0)
        rows = []
        Target = self.env['propertio.target'].sudo()
        for salesperson, values in stats.items():
            user = self.env['res.users'].search([('name', '=', salesperson)], limit=1)
            target_domain = [('user_id', '=', user.id)] if user else [('id', '=', 0)]
            if filters.get('date_from'):
                target_domain.append(('date_to', '>=', filters['date_from']))
            if filters.get('date_to'):
                target_domain.append(('date_from', '<=', filters['date_to']))
            targets = Target.search(self._company_domain('propertio.target', target_domain))
            target_revenue = sum(targets.mapped('target_amount'))
            avg_days = values['days'] / values['deals'] if values['deals'] else 0.0
            velocity = values['deals'] / max(avg_days, 1.0)
            rows.append({
                'Salesperson': salesperson,
                'Deals': values['deals'],
                'Target Revenue': target_revenue,
                'Actual Revenue': values['actual'],
                'Target vs Actual %': round((values['actual'] / target_revenue * 100) if target_revenue else 0, 2),
                'Average Days to Close': round(avg_days, 2),
                'Lead-to-Contract Velocity': round(velocity, 2),
                'Discount Variance %': round((values['discount'] / values['list'] * 100) if values['list'] else 0, 2),
                'Stage': 'Closed Won',
                'Sales Month': filters.get('date_from', '')[:7] if filters.get('date_from') else '',
                '_ids': values['ids'],
            })
        return cols, rows

    def _occupancy_unit_lifecycle_rows(self, report, filters):
        cols = self._cols(['Lifecycle Node', 'Project', 'Floor', 'Occupancy State', 'Units', 'RevPAM', 'Maintenance Cost-to-Income %', 'Portfolio Turnover %', 'Revenue', 'Available m2'])
        groups = defaultdict(lambda: {'ids': [], 'units': 0, 'revenue': 0.0, 'm2': 0.0, 'sold': 0, 'maintenance': 0.0})
        for unit in self.env['propertio.unit'].search(self._build_domain(report, filters), order='project_id, floor, name'):
            occupancy = 'Occupied / Sold' if unit.state in ('sold', 'handover') else 'Optioned' if unit.state == 'option' else 'Vacant'
            node = '%s / Floor %s / %s' % (unit.project_id.display_name, unit.floor or '-', occupancy)
            revenue = unit.sold_value or unit.collected_amount or 0.0
            maintenance = (unit.list_price or 0.0) * 0.015
            g = groups[node]
            g['ids'].append(unit.id)
            g['units'] += 1
            g['revenue'] += revenue
            g['m2'] += unit.net_m2 or unit.gross_m2 or 0.0
            g['sold'] += 1 if unit.state in ('sold', 'handover') else 0
            g['maintenance'] += maintenance
            g['project'] = unit.project_id.display_name
            g['floor'] = unit.floor or ''
            g['occupancy'] = occupancy
        rows = []
        for node, g in groups.items():
            rows.append({
                'Lifecycle Node': node,
                'Project': g['project'],
                'Floor': g['floor'],
                'Occupancy State': g['occupancy'],
                'Units': g['units'],
                'RevPAM': round(g['revenue'] / g['m2'], 2) if g['m2'] else 0.0,
                'Maintenance Cost-to-Income %': round((g['maintenance'] / g['revenue'] * 100) if g['revenue'] else 0.0, 2),
                'Portfolio Turnover %': round((g['sold'] / g['units'] * 100) if g['units'] else 0.0, 2),
                'Revenue': g['revenue'],
                'Available m2': g['m2'],
                '_ids': g['ids'],
            })
        return cols, self._filter_rows(rows, filters)

    def _cash_flow_arrears_forensic_rows(self, report, filters, options):
        cols = self._cols(['Aging Bucket', 'Project', 'Customer', 'Amount', 'Paid', 'Residual', 'DSO', 'CEI %', 'Weighted Average Delinquency', 'Collection Health %', 'Accounting View'])
        accounting_view = options.get('accounting_view') or 'accrual'
        buckets = defaultdict(lambda: {'ids': [], 'amount': 0.0, 'paid': 0.0, 'residual': 0.0, 'weighted_days': 0.0})
        for inst in self.env['propertio.installment'].search(self._build_domain(report, filters), order='date_due asc'):
            days = inst.overdue_days or 0
            bucket = 'Current' if days <= 0 else '1-30' if days <= 30 else '31-60' if days <= 60 else '61-90' if days <= 90 else '90+'
            key = (bucket, inst.project_id.display_name, inst.partner_id.display_name)
            g = buckets[key]
            amount = inst.amount or 0.0
            paid = inst.amount_paid or 0.0
            residual = inst.residual or 0.0
            if accounting_view == 'cash':
                amount = paid
                residual = 0.0
            g['ids'].append(inst.id)
            g['amount'] += amount
            g['paid'] += paid
            g['residual'] += residual
            g['weighted_days'] += residual * days
        rows = []
        for (bucket, project, customer), g in buckets.items():
            cei_base = g['amount'] or 1.0
            dso = (g['residual'] / max(g['paid'], 1.0)) * 30 if g['paid'] else (90 if g['residual'] else 0)
            cei = (g['paid'] / cei_base) * 100
            rows.append({
                'Aging Bucket': bucket,
                'Project': project,
                'Customer': customer,
                'Amount': g['amount'],
                'Paid': g['paid'],
                'Residual': g['residual'],
                'DSO': round(dso, 2),
                'CEI %': round(cei, 2),
                'Weighted Average Delinquency': round(g['weighted_days'] / g['residual'], 2) if g['residual'] else 0.0,
                'Collection Health %': round(max(0.0, min(100.0, cei - (dso / 2))), 2),
                'Accounting View': accounting_view.title(),
                '_ids': g['ids'],
            })
        return cols, self._filter_rows(rows, filters)

    def _sale_collection_rows(self, report, filters):
        cols = self._cols(['Contract', 'Customer', 'Project', 'Unit', 'Sale Price', 'Collected', 'Outstanding', 'Collection %', 'Status'])
        rows = []
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters), order='date_sale desc'):
            total = sale.sale_price or 0
            paid = sale.total_paid or 0
            outstanding = sale.balance if sale.balance is not None else total - paid
            rows.append({'Contract': sale.name, 'Customer': sale.partner_id.display_name, 'Project': sale.project_id.display_name, 'Unit': sale.unit_id.display_name, 'Sale Price': total, 'Collected': paid, 'Outstanding': outstanding, 'Collection %': round((paid / total * 100) if total else 0, 2), 'Status': sale.state, '_id': sale.id})
        return cols, rows

    def _installment_rows(self, report, filters):
        cols = self._cols(['Contract', 'Customer', 'Project', 'Salesperson', 'Description', 'Due Date', 'Amount', 'Paid', 'Residual', 'VAT Included', 'Payment Status', 'Overdue Days'])
        rows = []
        for inst in self.env['propertio.installment'].search(self._build_domain(report, filters), order='date_due asc'):
            amount = inst.amount or 0
            residual = inst.residual or 0
            overdue_days = inst.overdue_days or 0
            risk_segment = 'Kırmızı Alarm' if overdue_days >= 60 or residual >= 1000000 else 'Yakın Takip' if overdue_days >= 15 else 'Normal'
            days_bucket = '60+ gün' if overdue_days >= 60 else '30-59 gün' if overdue_days >= 30 else '1-29 gün' if overdue_days else 'Vadesinde'
            priority = 'Bugün ara' if risk_segment == 'Kırmızı Alarm' else 'Bu hafta takip' if residual else 'Kapandı'
            row = {
                'Contract': inst.sale_id.name,
                'Customer': inst.partner_id.display_name,
                'Project': inst.project_id.display_name,
                'Salesperson': inst.sales_person_id.display_name,
                'Description': inst.name,
                'Due Date': self._date(inst.date_due),
                'Due Month': inst.date_due.strftime('%Y-%m') if inst.date_due else '',
                'Amount': amount,
                'Paid': inst.amount_paid or 0,
                'Residual': residual,
                'VAT Net': round(amount / 1.20, 2),
                'VAT Amount': round(amount - (amount / 1.20), 2),
                'VAT Included': round(amount * 1.20, 2),
                'Payment Status': inst.payment_status,
                'Overdue Days': overdue_days,
                'Days Bucket': days_bucket,
                'Risk Segment': risk_segment,
                'Legal Follow-up': 'Evet' if overdue_days >= 60 else 'Hayır',
                'Collection Priority': priority,
                'Action': 'Hukuk/Noter hazırlığı' if overdue_days >= 60 else 'Tahsilat araması' if residual else 'Aksiyon yok',
                '_id': inst.id,
            }
            rows.append(row)
        return cols, rows

    def _unit_rows(self, report, filters):
        cols = self._cols(['Project', 'Block', 'Unit', 'Type', 'Floor', 'State', 'List Price', 'Sold Value', 'Collected', 'Receivable', 'Gross m2', 'Net m2', 'Inventory Age'])
        rows = []
        today = fields.Date.context_today(self)
        for unit in self.env['propertio.unit'].search(self._build_domain(report, filters), order='project_id, block_id, name'):
            age = (today - unit.create_date.date()).days if unit.create_date else 0
            estimated_cost = (unit.list_price or 0) * 0.68
            estimated_profit = (unit.sold_value or unit.list_price or 0) - estimated_cost
            margin = (estimated_profit / (unit.sold_value or unit.list_price) * 100) if (unit.sold_value or unit.list_price) else 0
            age_bucket = '180+ gün' if age >= 180 else '90-179 gün' if age >= 90 else '30-89 gün' if age >= 30 else 'Yeni Stok'
            occupancy = 'Dolu/Satıldı' if unit.state in ('sold', 'handover') else 'Opsiyonlu' if unit.state == 'option' else 'Boş'
            rows.append({'Project': unit.project_id.display_name, 'Block': unit.block_id.display_name, 'Unit': unit.display_name, 'Type': unit.category_id.display_name, 'Floor': unit.floor or '', 'State': unit.state, 'Occupancy State': occupancy, 'List Price': unit.list_price or 0, 'Sold Value': unit.sold_value or 0, 'Collected': unit.collected_amount or 0, 'Receivable': unit.receivable_amount or 0, 'Sell-through %': 100 if unit.state in ('sold', 'handover') else 0, 'Monthly Rent Estimate': round((unit.list_price or 0) * 0.0045, 2), 'Estimated Cost': round(estimated_cost, 2), 'Estimated Profit': round(estimated_profit, 2), 'Margin %': round(margin, 2), 'Gross m2': unit.gross_m2 or 0, 'Net m2': unit.net_m2 or 0, 'Inventory Age': age, 'Aging Bucket': age_bucket, 'Tapu Ref': unit.tapu_ref or '', 'Action': 'Fiyat revizyonu' if age >= 180 and unit.state == 'available' else 'Portföyde tut', '_id': unit.id})
        return cols, rows

    def _sales_rows(self, report, filters):
        cols = self._cols(['Date', 'Contract', 'Customer', 'Project', 'Unit', 'Salesperson', 'Broker', 'Currency', 'List Price', 'Sale Price', 'Discount', 'TCMB Rate', 'Status'])
        rows = []
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters), order='date_sale desc'):
            rate = sale.rate_tcmb or 1.0
            try_equivalent = (sale.sale_price or 0) * rate
            cancel_risk = 'Yüksek' if sale.state == 'cancel' else 'Orta' if sale.balance and sale.balance > sale.sale_price * 0.7 else 'Düşük'
            rows.append({'Date': self._date(sale.date_sale), 'Sales Month': sale.date_sale.strftime('%Y-%m') if sale.date_sale else '', 'Contract': sale.name, 'Customer': sale.partner_id.display_name, 'Project': sale.project_id.display_name, 'Unit': sale.unit_id.display_name, 'Salesperson': sale.sales_person_id.display_name, 'Broker': sale.agency_id.display_name, 'Currency': sale.currency_id.name, 'List Price': sale.unit_id.list_price or 0, 'Sale Price': sale.sale_price or 0, 'Discount': sale.discount_amount or 0, 'TCMB Rate': rate, 'TRY Equivalent': try_equivalent, 'FX Exposure': 'Var' if sale.currency_id != self.env.company.currency_id else 'Yok', 'Approval Step': 'Onaylandı' if sale.state == 'confirmed' else 'Taslak/İptal', 'Reservation Date': self._date(sale.reserve_date), 'Rental Status': 'Kiralanabilir/Satıştan türetilmiş', 'Cancellation Risk': cancel_risk, 'Outstanding': sale.balance or 0, 'Status': sale.state, 'Action': 'Sözleşme güvence kontrolü' if cancel_risk != 'Düşük' else 'Normal takip', '_id': sale.id})
        return cols, rows

    def _customer_rows(self, report, filters):
        cols = self._cols(['Customer', 'Phone', 'Email', 'Sales Count', 'Total Sales', 'Collected', 'Outstanding', 'Overdue Items', 'Risk'])
        rows = []
        partners = self.env['res.partner'].search([('is_company', '=', False)], limit=400)
        for partner in partners:
            sales = self.env['propertio.sale'].search(self._company_domain('propertio.sale', [('partner_id', '=', partner.id)]))
            if not sales and report['key'] != 'tenant_landlord':
                continue
            total = sum(sales.mapped('sale_price'))
            paid = sum(sales.mapped('total_paid'))
            overdue = self.env['propertio.installment'].search_count(self._company_domain('propertio.installment', [('partner_id', '=', partner.id), ('payment_status', '=', 'overdue')]))
            risk = 'High' if overdue >= 3 else 'Medium' if overdue else 'Low'
            rows.append({'Customer': partner.display_name, 'Role': 'Mülk Sahibi' if sales else 'Kiracı/Lead', 'Phone': (getattr(partner, 'phone', '') or getattr(partner, 'mobile', '') or ''), 'Email': getattr(partner, 'email', '') or '', 'Sales Count': len(sales), 'Total Sales': total, 'Collected': paid, 'Outstanding': total - paid, 'Overdue Items': overdue, 'Risk': risk, 'Action': 'Risk araması' if risk != 'Low' else 'Portföy iletişimi', '_id': partner.id})
        return cols, rows

    def _payment_rows(self, report, filters):
        cols = self._cols(['Date', 'Receipt', 'Customer', 'Contract', 'Amount', 'Currency', 'Method', 'State', 'Exchange Rate'])
        rows = []
        for pay in self.env['propertio.payment'].search(self._build_domain(report, filters), order='payment_date desc'):
            rows.append({'Date': self._date(pay.payment_date), 'Receipt': pay.name, 'Customer': pay.partner_id.display_name, 'Contract': pay.sale_id.name, 'Amount': pay.amount or 0, 'Currency': pay.currency_id.name, 'Method': pay.payment_method, 'State': pay.state, 'Exchange Rate': pay.exchange_rate or 0, '_id': pay.id})
        return cols, rows

    def _performance_rows(self, report, filters):
        cols = self._cols(['Salesperson', 'Deals', 'Revenue', 'Collected', 'Open Balance', 'Average Deal', 'Confirmed Deals'])
        stats = defaultdict(lambda: {'ids': [], 'deals': 0, 'revenue': 0, 'paid': 0, 'confirmed': 0})
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters)):
            key = sale.sales_person_id.display_name or _('Unassigned')
            stats[key]['ids'].append(sale.id)
            stats[key]['deals'] += 1
            stats[key]['revenue'] += sale.sale_price or 0
            stats[key]['paid'] += sale.total_paid or 0
            stats[key]['confirmed'] += 1 if sale.state == 'confirmed' else 0
        rows = [{'Salesperson': k, 'Deals': v['deals'], 'Revenue': v['revenue'], 'Collected': v['paid'], 'Open Balance': v['revenue'] - v['paid'], 'Average Deal': (v['revenue'] / v['deals']) if v['deals'] else 0, 'Confirmed Deals': v['confirmed'], '_ids': v['ids']} for k, v in stats.items()]
        return cols, rows

    def _lead_rows(self, report, filters):
        cols = self._cols(['Lead', 'Customer', 'Source', 'Campaign', 'Salesperson', 'Stage', 'Expected Revenue', 'Created'])
        rows = []
        if 'crm.lead' not in self.env:
            return cols, rows
        for lead in self.env['crm.lead'].search(self._build_domain(report, filters), order='create_date desc', limit=500):
            probability = lead.probability or 0
            expected = lead.expected_revenue or 0
            rows.append({'Lead': lead.name, 'Customer': lead.partner_id.display_name, 'Source': lead.source_id.display_name if 'source_id' in lead._fields else 'Direct', 'Campaign': lead.campaign_id.display_name if 'campaign_id' in lead._fields else '', 'Salesperson': lead.user_id.display_name, 'Stage': lead.stage_id.display_name, 'Expected Revenue': expected, 'Lead Quality': 'Sıcak' if probability >= 60 else 'Ilık' if probability >= 30 else 'Soğuk', 'ROI Proxy': round(expected * probability / 100, 2), 'Action': 'Randevu al' if probability >= 60 else 'Nurture kampanyası', 'Created': self._date(lead.create_date), '_id': lead.id})
        return cols, rows

    def _advanced_leads_rows(self, report, filters):
        """Unified CRM lead + Propertio reservation/sale bridge report."""
        cols = self._cols([
            'Created', 'Lead', 'Customer', 'Phone', 'Source', 'Platform', 'Campaign',
            'Salesperson', 'Project', 'Unit', 'Stage', 'Type', 'Expected Revenue',
            'Lead Quality', 'Reservation', 'Contract', 'Conversion', 'Action',
        ])
        rows = []
        if 'crm.lead' not in self.env:
            return cols, rows
        Offer = self.env['propertio.offer'] if 'propertio.offer' in self.env else None
        Sale = self.env['propertio.sale'] if 'propertio.sale' in self.env else None
        leads = self.env['crm.lead'].search(
            self._build_domain(report, filters),
            order='create_date desc',
            limit=1000,
        )
        for lead in leads:
            probability = lead.probability or 0
            expected = lead.expected_revenue or 0
            quality = 'Sıcak' if probability >= 60 else 'Ilık' if probability >= 30 else 'Soğuk'
            source = lead.source_id.display_name if 'source_id' in lead._fields and lead.source_id else ''
            platform = ''
            if 'medium_id' in lead._fields and lead.medium_id:
                platform = lead.medium_id.display_name
            elif source:
                low = source.lower()
                if 'instagram' in low:
                    platform = 'Instagram'
                elif 'facebook' in low:
                    platform = 'Facebook'
                elif 'meta' in low:
                    platform = 'Meta'
            campaign = lead.campaign_id.display_name if 'campaign_id' in lead._fields and lead.campaign_id else ''
            project = lead.propertio_project_id.display_name if 'propertio_project_id' in lead._fields and lead.propertio_project_id else ''
            unit = lead.propertio_unit_id.display_name if 'propertio_unit_id' in lead._fields and lead.propertio_unit_id else ''
            phone = (
                getattr(lead, 'phone', None)
                or getattr(lead, 'mobile', None)
                or (lead.partner_id.phone if lead.partner_id else None)
                or (getattr(lead.partner_id, 'mobile', None) if lead.partner_id else None)
                or ''
            )
            reservation = ''
            contract = ''
            conversion = 'open'
            offer = Offer.browse() if Offer is not None else None
            if Offer is not None:
                if 'opportunity_id' in Offer._fields:
                    offer = Offer.search([('opportunity_id', '=', lead.id)], order='date_offer desc, id desc', limit=1)
                if not offer and lead.partner_id:
                    offer = Offer.search([('partner_id', '=', lead.partner_id.id)], order='date_offer desc, id desc', limit=1)
                if offer:
                    state_label = self._selection_label(offer, 'state')
                    reservation = '%s (%s)' % (offer.name, state_label)
                    if offer.state == 'accepted':
                        conversion = 'reserved'
                    elif offer.state in ('cancel', 'refund'):
                        conversion = 'cancelled'
                    elif offer.state in ('refused', 'expired'):
                        conversion = 'lost'
            sales = None
            if Sale is not None:
                sales = Sale.search([('opportunity_id', '=', lead.id)], order='date_sale desc', limit=1)
                if not sales and lead.partner_id:
                    sales = Sale.search([('partner_id', '=', lead.partner_id.id)], order='date_sale desc', limit=1)
                if sales:
                    state_label = self._selection_label(sales, 'state')
                    contract = '%s (%s)' % (sales.name, state_label)
                    if sales.state == 'confirmed':
                        conversion = 'sold'
                    elif sales.state in ('cancel', 'refund'):
                        conversion = 'cancelled'
            if getattr(lead, 'probability', 0) == 100 or getattr(lead, 'won_status', False) == 'won':
                if conversion == 'open':
                    conversion = 'won'
            if getattr(lead, 'active', True) is False or getattr(lead, 'won_status', False) == 'lost':
                if conversion == 'open':
                    conversion = 'lost'

            wanted_conv = filters.get('conversion_status')
            if wanted_conv not in (None, False, '') and conversion != wanted_conv:
                continue

            conversion_labels = {
                'sold': _('Satıldı'),
                'reserved': _('Rezerve'),
                'won': _('Satış Yapıldı'),
                'lost': _('Kaybedildi'),
                'cancelled': _('İptal / İade'),
                'open': _('Açık'),
            }
            action = {
                'sold': 'Sözleşme takibi',
                'reserved': 'Satışa dönüştür',
                'won': 'Propertio satış bağla',
                'lost': 'Nurture / yeniden aç',
                'cancelled': 'İptal/iade arşivle',
                'open': 'Randevu al' if probability >= 60 else 'Takip planla',
            }.get(conversion, 'Takip et')

            rows.append({
                'Created': self._date(lead.create_date),
                'Lead': lead.name,
                'Customer': lead.partner_id.display_name or lead.contact_name or '',
                'Phone': phone or '',
                'Source': source or '—',
                'Platform': platform or '—',
                'Campaign': campaign or '',
                'Salesperson': lead.user_id.display_name or '',
                'Project': project or '',
                'Unit': unit or '',
                'Stage': lead.stage_id.display_name if lead.stage_id else '',
                'Type': _('Fırsat') if lead.type == 'opportunity' else _('Lead'),
                'Expected Revenue': expected,
                'Lead Quality': quality,
                'Reservation': reservation or '—',
                'Contract': contract or '—',
                'Conversion': conversion_labels.get(conversion, conversion),
                '_conversion_key': conversion,
                'Action': action,
                '_id': lead.id,
            })
        return cols, rows

    @api.model
    def _cron_send_daily_advanced_leads_report(self):
        """End-of-day advanced leads report emailed to company/admin addresses."""
        day = date.today() - timedelta(days=1)
        filters = {
            'date_from': day.isoformat(),
            'date_to': day.isoformat(),
        }
        options = {
            'full_export': True,
            'chart_type': 'donut',
            'group_by': 'Source',
            'chart_group_by': 'Source',
            'chart_value': 'Expected Revenue',
        }
        companies = self.env['res.company'].search([])
        Mail = self.env['mail.mail'].sudo()
        for company in companies:
            emails = set()
            if company.email:
                emails.add(company.email.strip())
            # Propertio managers / admins + system admins
            users = self.env['res.users'].sudo().search([
                ('company_ids', 'in', company.id),
                ('active', '=', True),
                ('share', '=', False),
            ])
            for user in users:
                role = getattr(user, 'propertio_role', False)
                if role in ('manager', 'admin') or user.has_group('base.group_system'):
                    if user.email:
                        emails.add(user.email.strip())
            if not emails:
                continue
            payload = self.with_company(company).run_report(
                'advanced_leads_crm_propertio', filters, options,
            )
            html = self._export_html(payload['report'], payload['columns'], payload['rows'], payload)
            subject = _(
                '%(company)s — Günlük Gelişmiş Lead Raporu (%(day)s)'
            ) % {'company': company.name, 'day': day.strftime('%d.%m.%Y')}
            body = _(
                '<p>Merhaba,</p>'
                '<p><b>%(day)s</b> için birleşik CRM + Propertio lead raporu ektedir / aşağıdadır.</p>'
                '<p>Toplam satır: <b>%(n)s</b></p>'
                '%(html)s'
                '<p>— Propertio Rapor Merkezi (otomatik)</p>'
            ) % {
                'day': day.strftime('%d.%m.%Y'),
                'n': payload.get('row_count') or 0,
                'html': html,
            }
            for email in sorted(emails):
                mail = Mail.create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': email,
                    'email_from': company.email or self.env.user.email_formatted or self.env.user.email,
                    'auto_delete': True,
                })
                try:
                    mail.send()
                except Exception:
                    # Keep cron resilient if SMTP is misconfigured
                    _logger = __import__('logging').getLogger(__name__)
                    _logger.exception('Daily advanced leads email failed for %s', email)
        return True

    def _vat_compliance_rows(self, report, filters):
        cols = self._cols(['Date', 'Contract', 'Customer', 'Project', 'Unit', 'Net m2', 'Sale Price', 'VAT Method', 'Low Rate Base', 'High Rate Base', 'Estimated VAT', 'Refund Timing', 'Risk Level', 'Action'])
        rows = []
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters), order='date_sale desc'):
            net_m2 = sale.unit_id.net_m2 or 0
            price = sale.sale_price or 0
            if not net_m2:
                method = 'Missing net m2'
                low_base = high_base = vat = 0
                risk = 'High'
            elif net_m2 <= 150:
                method = 'Standard 10%'
                low_base = price
                high_base = 0
                vat = price * 0.10
                risk = 'Low'
            else:
                method = 'Tiered 150 m2 10% / excess 20%'
                low_base = price * (150.0 / net_m2)
                high_base = price - low_base
                vat = (low_base * 0.10) + (high_base * 0.20)
                risk = 'Medium'
            deed = self.env['propertio.title.deed'].search([('sale_id', '=', sale.id)], limit=1)
            refund_timing = 'Transfer complete' if deed and deed.state == 'transferred' else 'Wait for title transfer'
            if refund_timing != 'Transfer complete' and risk == 'Low':
                risk = 'Medium'
            rows.append({'Date': self._date(sale.date_sale), 'Contract': sale.name, 'Customer': sale.partner_id.display_name, 'Project': sale.project_id.display_name, 'Unit': sale.unit_id.display_name, 'Net m2': net_m2, 'Sale Price': price, 'VAT Method': method, 'Low Rate Base': round(low_base, 2), 'High Rate Base': round(high_base, 2), 'Estimated VAT': round(vat, 2), 'Refund Timing': refund_timing, 'Risk Level': risk, 'Action': 'Complete unit tax attributes' if not net_m2 else 'Check deed before refund claim' if refund_timing != 'Transfer complete' else 'Ready for invoice control', '_id': sale.id})
        return cols, rows

    def _fx_compliance_rows(self, report, filters):
        cols = self._cols(['Date', 'Contract', 'Customer', 'Nationality', 'Currency', 'Sale Price', 'TCMB Rate', 'TRY Equivalent', 'Payment FX Count', 'FX Risk', 'Exception Basis', 'Action'])
        rows = []
        company_currency = self.env.company.currency_id
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters), order='date_sale desc'):
            partner = sale.partner_id
            nationality = partner.nationality.code if getattr(partner, 'nationality', False) else ''
            foreign_customer = bool((nationality and nationality != 'TR') or getattr(partner, 'id_type', False) in ('passport', 'foreign'))
            fx_contract = sale.currency_id and sale.currency_id != company_currency
            fx_payments = self.env['propertio.payment'].search_count([('sale_id', '=', sale.id), ('currency_id', '!=', company_currency.id), ('state', '!=', 'cancel')])
            exception_basis = 'Foreign buyer indicator' if foreign_customer else 'No exception captured'
            risk = 'High' if fx_contract and not foreign_customer else 'Medium' if fx_payments and not foreign_customer else 'Low'
            rate = sale.rate_tcmb or 1.0
            rows.append({'Date': self._date(sale.date_sale), 'Contract': sale.name, 'Customer': partner.display_name, 'Nationality': nationality or '', 'Currency': sale.currency_id.name, 'Sale Price': sale.sale_price or 0, 'TCMB Rate': rate, 'TRY Equivalent': round((sale.sale_price or 0) * rate, 2), 'Payment FX Count': fx_payments, 'FX Risk': risk, 'Exception Basis': exception_basis, 'Action': 'Convert official contract/payment plan to TRY or capture exception proof' if risk == 'High' else 'Keep FX basis documentation' if risk == 'Medium' else 'No action', '_id': sale.id})
        return cols, rows

    def _title_deed_tax_risk_rows(self, report, filters):
        cols = self._cols(['Date', 'Sale', 'Customer', 'Unit', 'Sale Price', 'Declared Deed Base', 'Declared Ratio %', 'Potential Fee Gap', 'Penalty Exposure', 'Risk Level', 'Action'])
        rows = []
        if 'propertio.title.deed' not in self.env:
            return cols, rows
        for deed in self.env['propertio.title.deed'].search(self._build_domain(report, filters), order='tapu_date desc'):
            sale_price = deed.sale_id.sale_price or 0
            declared_base = (deed.tapu_cost or 0) / 0.02 if deed.tapu_cost else 0
            gap = max(0, sale_price - declared_base)
            ratio = (declared_base / sale_price * 100) if sale_price else 0
            fee_gap = gap * 0.04
            penalty = fee_gap * 1.25
            risk = 'High' if sale_price and ratio < 70 else 'Medium' if sale_price and ratio < 90 else 'Low'
            rows.append({'Date': self._date(deed.tapu_date), 'Sale': deed.sale_id.display_name, 'Customer': deed.partner_id.display_name, 'Unit': deed.unit_id.display_name, 'Sale Price': sale_price, 'Declared Deed Base': round(declared_base, 2), 'Declared Ratio %': round(ratio, 2), 'Potential Fee Gap': round(fee_gap, 2), 'Penalty Exposure': round(penalty, 2), 'Risk Level': risk, 'Action': 'Reconcile deed base with actual sale and bank evidence' if risk != 'Low' else 'Archive deed/invoice evidence', '_id': deed.id})
        return cols, rows

    def _crm_erp_reconciliation_rows(self, report, filters):
        cols = self._cols(['Date', 'Contract', 'Customer', 'Project', 'Sale Price', 'Plan Total', 'Collected CRM', 'Posted ERP', 'Delta', 'Invoice Status', 'Reconciliation Status', 'Action'])
        rows = []
        for sale in self.env['propertio.sale'].search(self._build_domain(report, filters), order='date_sale desc'):
            plan_total = sum(sale.installment_ids.mapped('amount'))
            posted_payments = self.env['propertio.payment'].search([('sale_id', '=', sale.id), ('state', '=', 'posted')])
            posted_total = sum(posted_payments.mapped('covered_amount'))
            crm_collected = sale.total_paid or 0
            delta = abs((sale.sale_price or 0) - plan_total) + abs(crm_collected - posted_total)
            invoice_status = sale.invoice_status or 'not_set'
            status = 'OK' if delta < 0.01 and invoice_status != 'not_set' else 'Needs Review'
            rows.append({'Date': self._date(sale.date_sale), 'Contract': sale.name, 'Customer': sale.partner_id.display_name, 'Project': sale.project_id.display_name, 'Sale Price': sale.sale_price or 0, 'Plan Total': round(plan_total, 2), 'Collected CRM': round(crm_collected, 2), 'Posted ERP': round(posted_total, 2), 'Delta': round(delta, 2), 'Invoice Status': invoice_status, 'Reconciliation Status': status, 'Action': 'Rebalance payment plan / sync ERP payment / set invoice status' if status != 'OK' else 'Matched', '_id': sale.id})
        return cols, rows

    def _showing_document_rows(self, report, filters):
        cols = self._cols(['Created', 'Lead', 'Customer', 'Phone', 'Salesperson', 'Stage', 'Showing Evidence', 'Compliance Status', 'Risk Score', 'Action'])
        rows = []
        if 'crm.lead' not in self.env:
            return cols, rows
        for lead in self.env['crm.lead'].search(self._build_domain(report, filters), order='create_date desc', limit=500):
            messages = lead.message_ids[:20] if 'message_ids' in lead._fields else self.env['mail.message']
            evidence_text = ' '.join((m.body or '') for m in messages).lower()
            has_attachment = bool(getattr(lead, 'message_main_attachment_id', False))
            has_keyword = any(token in evidence_text for token in ('yer göster', 'yer goster', 'showing', 'simsarlik', 'simsarlık'))
            has_contact = bool(lead.partner_id and (lead.partner_id.phone or getattr(lead.partner_id, 'mobile', False) or getattr(lead.partner_id, 'whatsapp_number', False)))
            risk_score = (0 if has_attachment or has_keyword else 70) + (0 if has_contact else 20)
            status = 'Complete' if risk_score <= 20 else 'Missing Evidence' if risk_score >= 70 else 'Partial'
            rows.append({'Created': self._date(lead.create_date), 'Lead': lead.name, 'Customer': lead.partner_id.display_name, 'Phone': (lead.partner_id.phone or getattr(lead.partner_id, 'mobile', '') or getattr(lead.partner_id, 'whatsapp_number', '') or '') if lead.partner_id else '', 'Salesperson': lead.user_id.display_name, 'Stage': lead.stage_id.display_name, 'Showing Evidence': 'Attachment/message evidence' if has_attachment or has_keyword else 'Not found', 'Compliance Status': status, 'Risk Score': risk_score, 'Action': 'Upload signed showing form before visit/commission claim' if status != 'Complete' else 'Archive retained', '_id': lead.id})
        return cols, rows

    def _valuation_readiness_rows(self, report, filters):
        cols = self._cols(['Project', 'Block', 'Unit', 'Type', 'Gross m2', 'Net m2', 'Efficiency %', 'List Price', 'Price / Net m2', 'Tapu Ref', 'Data Completeness %', 'Readiness Score', 'Readiness Status', 'Action'])
        rows = []
        for unit in self.env['propertio.unit'].search(self._build_domain(report, filters), order='project_id, block_id, name'):
            checks = [bool(unit.project_id), bool(unit.block_id), bool(unit.category_id), bool(unit.gross_m2), bool(unit.net_m2), bool(unit.list_price), bool(unit.tapu_ref), bool(unit.floor), bool(unit.facade or unit.view_type)]
            completeness = round(sum(1 for item in checks if item) / len(checks) * 100, 2)
            efficiency = (unit.net_m2 / unit.gross_m2 * 100) if unit.gross_m2 else 0
            price_per_net = (unit.list_price / unit.net_m2) if unit.net_m2 else 0
            readiness = round((completeness * 0.7) + (min(100, efficiency) * 0.2) + (10 if unit.attachment_ids else 0), 2)
            status = 'Ready' if readiness >= 80 else 'Needs Data' if readiness >= 55 else 'Incomplete'
            rows.append({'Project': unit.project_id.display_name, 'Block': unit.block_id.display_name, 'Unit': unit.display_name, 'Type': unit.category_id.display_name, 'Gross m2': unit.gross_m2 or 0, 'Net m2': unit.net_m2 or 0, 'Efficiency %': round(efficiency, 2), 'List Price': unit.list_price or 0, 'Price / Net m2': round(price_per_net, 2), 'Tapu Ref': unit.tapu_ref or '', 'Data Completeness %': completeness, 'Readiness Score': readiness, 'Readiness Status': status, 'Action': 'Complete GEDAS valuation inputs' if status != 'Ready' else 'Ready for valuation packet', '_id': unit.id})
        return cols, rows

    def _authorization_rows(self, report, filters):
        cols = self._cols(['User', 'Login', 'Company', 'Groups', 'Can Manage Reports', 'Master Admin'])
        rows = []
        for user in self.env['res.users'].search([]):
            group_field = 'groups_id' if 'groups_id' in user._fields else 'group_ids' if 'group_ids' in user._fields else False
            group_names = user[group_field].mapped('name')[:8] if group_field else []
            rows.append({'User': user.name, 'Login': user.login, 'Company': user.company_id.display_name, 'Groups': ', '.join(group_names), 'Can Manage Reports': user.has_group('base.group_user'), 'Master Admin': user.has_group('base.group_system'), '_id': user.id})
        return cols, rows

    def _activity_rows(self, report, filters):
        cols = self._cols(['Due Date', 'Summary', 'Model', 'Record', 'Assigned To', 'State'])
        rows = []
        for activity in self.env['mail.activity'].search(self._build_domain(report, filters), order='date_deadline desc', limit=500):
            rows.append({'Due Date': self._date(activity.date_deadline), 'Summary': activity.summary or activity.activity_type_id.display_name, 'Model': activity.res_model, 'Record': activity.res_name, 'Assigned To': activity.user_id.display_name, 'State': activity.state, 'Activity Count': 1, '_id': activity.id})
        return cols, rows

    def _title_deed_rows(self, report, filters):
        cols = self._cols(['Sale', 'Customer', 'Unit', 'Title Deed No', 'Date', 'State', 'Invoice'])
        rows = []
        if 'propertio.title.deed' not in self.env:
            return cols, rows
        for deed in self.env['propertio.title.deed'].search(self._build_domain(report, filters), limit=500):
            rows.append({'Sale': deed.sale_id.display_name, 'Customer': deed.partner_id.display_name, 'Unit': deed.unit_id.display_name, 'Title Deed No': getattr(deed, 'tapu_no', '') or '', 'Date': self._date(getattr(deed, 'tapu_date', False)), 'State': getattr(deed, 'state', '') or '', 'Invoice': '', 'Title Deed Cost': getattr(deed, 'tapu_cost', 0) or 0, '_id': deed.id})
        return cols, rows

    def _project_rows(self, report, filters):
        cols = self._cols(['Project', 'City', 'Units', 'Sold Units', 'GDV', 'Sold Value', 'Collected', 'Construction %'])
        rows = []
        for project in self.env['propertio.project'].search(self._build_domain(report, filters)):
            units = project.unit_ids
            rows.append({'Project': project.display_name, 'City': project.city or '', 'Units': len(units), 'Sold Units': len(units.filtered(lambda u: u.state == 'sold')), 'GDV': project.gdv or sum(units.mapped('list_price')), 'Sold Value': sum(units.mapped('sold_value')), 'Collected': sum(units.mapped('collected_amount')), 'Construction %': getattr(project, 'construction_progress', 0) or 0, '_id': project.id})
        return cols, rows

    def _commission_rows(self, report, filters):
        cols = self._cols(['User', 'Period From', 'Period To', 'Gross Commission', 'Deductions', 'Net Commission', 'State'])
        rows = []
        for rec in self.env['propertio.commission'].search(self._build_domain(report, filters), order='period_from desc'):
            rows.append({'User': rec.user_id.display_name, 'Period From': self._date(rec.period_from), 'Period To': self._date(rec.period_to), 'Gross Commission': rec.gross_commission or 0, 'Deductions': rec.deductions or 0, 'Net Commission': rec.net_commission or 0, 'State': rec.state, '_id': rec.id})
        return cols, rows

    def _generic_rows(self, report, filters):
        cols = self._cols(['Record', 'Created'])
        rows = [{'Record': rec.display_name, 'Created': self._date(rec.create_date), '_id': rec.id} for rec in self.env[report['model']].search(self._build_domain(report, filters), limit=500)]
        return cols, rows

    def _selection_label(self, record, field_name):
        """Safe selection display label (handles list or callable selection)."""
        field = record._fields.get(field_name)
        if not field:
            return getattr(record, field_name, '') or ''
        selection = field.selection
        if callable(selection):
            selection = selection(record)
        return dict(selection or {}).get(getattr(record, field_name), getattr(record, field_name))

    def _cols(self, names):
        labels = COLUMN_LABELS.get(self._lang(), {})
        return [{
            'key': n,
            'label': labels.get(n) or n,
            'type': 'number' if any(x in n.lower() for x in ['amount', 'price', 'value', 'paid', 'balance', 'revenue', 'commission', 'gdv', 'collected', 'residual', 'deals', 'units', 'count', '%', 'rate', 'age', 'days', 'cost', 'profit', 'margin', 'probability']) else 'text',
        } for n in names]

    def _sort_rows(self, rows, sort_by, sort_dir):
        if not sort_by:
            return rows
        reverse = sort_dir == 'desc'
        return sorted(rows, key=lambda r: (r.get(sort_by) is None, r.get(sort_by)), reverse=reverse)

    def _group_rows(self, rows, columns, group_by):
        if not group_by:
            return []
        numeric = [c['key'] for c in columns if c.get('type') == 'number']
        groups = defaultdict(lambda: {'count': 0, 'totals': defaultdict(float), 'ids': []})
        for row in rows:
            key = row.get(group_by) or _('Empty')
            groups[key]['count'] += 1
            groups[key]['ids'].extend(row.get('_ids') or ([row.get('_id')] if row.get('_id') else []))
            for col in numeric:
                if isinstance(row.get(col), (int, float)):
                    groups[key]['totals'][col] += row[col]
        return [{'key': k, 'count': v['count'], 'totals': dict(v['totals']), 'ids': v['ids'][:200]} for k, v in groups.items()]

    def _totals(self, rows, columns):
        totals = {}
        for col in columns:
            if col.get('type') == 'number':
                values = [row.get(col['key']) for row in rows if isinstance(row.get(col['key']), (int, float))]
                if values:
                    totals[col['key']] = sum(values)
        return totals

    def _kpis(self, rows, totals):
        lang = self._lang()
        labels = {
            'tr': ('Satır', 'Toplam Değer', 'Tahsil Edilen', 'Açık/Risk'),
            'ar': ('الصفوف', 'القيمة الإجمالية', 'المحصل', 'المفتوح/المخاطر'),
            'en': ('Rows', 'Total Value', 'Collected', 'Open / Risk'),
        }.get(lang)
        total_amount = totals.get('Sale Price') or totals.get('List Price') or totals.get('Amount') or totals.get('Expected Revenue') or totals.get('GDV') or 0
        collected = totals.get('Collected') or totals.get('Paid') or 0
        outstanding = totals.get('Outstanding') or totals.get('Residual') or totals.get('Receivable') or 0
        return [{'label': labels[0], 'value': len(rows), 'tone': 'neutral'}, {'label': labels[1], 'value': total_amount, 'tone': 'primary'}, {'label': labels[2], 'value': collected, 'tone': 'success'}, {'label': labels[3], 'value': outstanding, 'tone': 'danger' if outstanding else 'neutral'}]

    def _chart(self, rows, columns, group_by, report, options=None):
        options = options or {}
        label_key = options.get('chart_group_by') or group_by or report.get('chart_axis') or next((c['key'] for c in columns if c['type'] == 'text'), None)
        value_key = options.get('chart_value') or report.get('chart_value') or next((c['key'] for c in columns if c['type'] == 'number' and c['key'] not in ('Overdue Days', 'Inventory Age')), None)
        if not label_key or not value_key:
            return []
        data = defaultdict(float)
        for row in rows:
            data[str(row.get(label_key) or _('Empty'))] += row.get(value_key) if isinstance(row.get(value_key), (int, float)) else 0
        limit = options.get('chart_limit') or 12
        try:
            limit = max(3, min(24, int(limit)))
        except (TypeError, ValueError):
            limit = 12
        total = sum(data.values()) or 1
        return [
            {'label': k, 'value': v, 'percent': round((v / total) * 100, 2)}
            for k, v in sorted(data.items(), key=lambda i: i[1], reverse=True)[:limit]
        ]

    def _template_payload(self):
        domain = ['|', ('user_id', '=', self.env.user.id), '|', ('is_global', '=', True), ('shared_user_ids', 'in', [self.env.user.id])]
        return [self._serialize_template(t) for t in self.env['propertio.report.template'].search(domain)]

    def _serialize_template(self, template):
        return {'id': template.id, 'name': template.name, 'report_key': template.report_key, 'is_global': template.is_global, 'options': json.loads(template.options_json or '{}')}

    def _check_template_access(self, template, write=False):
        if not template:
            raise UserError(_('Template not found.'))
        if self.env.user.has_group('base.group_system'):
            return
        if write and template.is_global:
            raise UserError(_('Only the TCRM master administrator can edit global templates.'))
        if template.user_id != self.env.user and self.env.user not in template.shared_user_ids:
            raise UserError(_('You do not have access to this report template.'))

    def _log(self, report, action, fmt, filters, row_count):
        self.env['propertio.report.access.log'].sudo().create({'report_key': report['key'], 'report_name': report['name'], 'action_type': action, 'export_format': fmt, 'company_id': self.env.company.id, 'user_id': self.env.user.id, 'filters_json': json.dumps(filters or {}, default=str), 'row_count': row_count})

    def _date(self, value):
        if not value:
            return ''
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M')
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return str(value)

    def _export_csv(self, report, columns, rows):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([report['name']])
        writer.writerow([report.get('description', '')])
        writer.writerow([fields.Datetime.to_string(fields.Datetime.now())])
        writer.writerow([])
        writer.writerow(['Totals'])
        totals = self._totals(rows, columns)
        for col in columns:
            if col['key'] in totals:
                writer.writerow([col['label'], totals[col['key']]])
        writer.writerow([])
        writer.writerow(['Chart'])
        for point in self._chart(rows, columns, False, report):
            writer.writerow([point['label'], point['value']])
        writer.writerow([])
        writer.writerow([c['label'] for c in columns])
        for row in rows:
            writer.writerow([row.get(c['key'], '') for c in columns])
        if totals:
            writer.writerow(['TOTAL'] + [totals.get(c['key'], '') for c in columns[1:]])
        return output.getvalue().encode('utf-8-sig')

    def _export_xlsx(self, report, columns, rows, payload):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('xlsxwriter is required for Excel exports.'))
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = book.add_worksheet(report['name'][:31])
        header = book.add_format({'bold': True, 'bg_color': '#0f172a', 'font_color': '#ffffff', 'border': 1, 'align': 'center'})
        subheader = book.add_format({'bold': True, 'bg_color': '#dbeafe', 'font_color': '#0f172a', 'border': 1})
        money = book.add_format({'num_format': '#,##0.00', 'border': 1})
        normal = book.add_format({'border': 1})
        warning = book.add_format({'bg_color': '#fef3c7', 'border': 1})
        danger = book.add_format({'bg_color': '#fee2e2', 'font_color': '#991b1b', 'border': 1})
        success = book.add_format({'bg_color': '#dcfce7', 'font_color': '#166534', 'border': 1})
        total_fmt = book.add_format({'bold': True, 'bg_color': '#e2e8f0', 'border': 1, 'num_format': '#,##0.00'})
        title = book.add_format({'bold': True, 'font_size': 16, 'font_color': '#0f172a'})
        sheet.write(0, 0, report['name'], title)
        sheet.write(1, 0, report.get('description', ''))
        sheet.write(2, 0, fields.Datetime.to_string(fields.Datetime.now()))
        totals = payload.get('totals') or self._totals(rows, columns)
        sheet.write(4, 0, 'Totals', subheader)
        trow = 5
        for column in columns:
            if column['key'] in totals:
                sheet.write(trow, 0, column['label'], normal)
                sheet.write(trow, 1, totals[column['key']], money)
                trow += 1
        start_row = max(8, trow + 2)
        for col, column in enumerate(columns):
            sheet.write(start_row, col, column['label'], header)
            sheet.set_column(col, col, max(14, min(32, len(column['label']) + 8)))
        for ridx, row in enumerate(rows, start=start_row + 1):
            for cidx, column in enumerate(columns):
                value = row.get(column['key'], '')
                cell_fmt = money if isinstance(value, (int, float)) else normal
                text_value = str(value).lower()
                if any(x in text_value for x in ['kırmızı', 'high', 'yüksek', 'overdue', 'gecik']):
                    cell_fmt = danger
                elif any(x in text_value for x in ['paid', 'kapandı', 'low', 'düşük']):
                    cell_fmt = success
                elif any(x in text_value for x in ['orta', 'medium', 'takip']):
                    cell_fmt = warning
                sheet.write(ridx, cidx, value, cell_fmt)
        if totals:
            total_row = start_row + 1 + len(rows)
            sheet.write(total_row, 0, 'TOTAL', total_fmt)
            for cidx, column in enumerate(columns[1:], start=1):
                value = totals.get(column['key'], '')
                sheet.write(total_row, cidx, value, total_fmt if isinstance(value, (int, float)) else normal)
        chart_data = payload.get('chart') or []
        if chart_data:
            chart_sheet = book.add_worksheet('Chart')
            chart_sheet.write(0, 0, report.get('chart_axis') or 'Group', header)
            chart_sheet.write(0, 1, report.get('chart_value') or 'Value', header)
            for idx, point in enumerate(chart_data, start=1):
                chart_sheet.write(idx, 0, point['label'], normal)
                chart_sheet.write(idx, 1, point['value'], money)
            chart = book.add_chart({'type': 'column'})
            chart.add_series({
                'name': report['name'],
                'categories': ['Chart', 1, 0, len(chart_data), 0],
                'values': ['Chart', 1, 1, len(chart_data), 1],
                'fill': {'color': '#2dd4bf'},
            })
            chart.set_title({'name': report['name']})
            chart.set_legend({'none': True})
            chart_sheet.insert_chart(1, 3, chart, {'x_scale': 1.5, 'y_scale': 1.2})
        book.close()
        output.seek(0)
        return output.read()

    def _export_html(self, report, columns, rows, payload):
        def esc(value):
            return str(value if value is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        head = ''.join('<th>%s</th>' % esc(c['label']) for c in columns)
        body = ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % esc(row.get(c['key'], '')) for c in columns) for row in rows)
        kpis = ''.join('<div class="kpi"><b>{}</b><br>{}</div>'.format(esc(k['label']), esc(k['value'])) for k in payload.get('kpis', []))
        return """<!doctype html><html><head><meta charset="utf-8"><style>
        body{{font-family:Arial,sans-serif;color:#111827;padding:24px}}h1{{margin:0 0 6px}}table{{width:100%;border-collapse:collapse;margin-top:18px}}th{{background:#0f172a;color:#fff;text-align:left}}th,td{{border:1px solid #dbe3ef;padding:8px;font-size:12px}}.kpis{{display:flex;gap:12px}}.kpi{{border:1px solid #dbe3ef;padding:10px 14px;border-radius:8px}}
        </style></head><body><h1>{}</h1><p>{} · {} rows</p><div class="kpis">{}</div><table><thead><tr>{}</tr></thead><tbody>{}</tbody></table></body></html>""".format(
            esc(report['name']), esc(fields.Datetime.to_string(fields.Datetime.now())), len(rows), kpis, head, body)

    def _export_pdf(self, report, columns, rows, payload):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            raise UserError(_('reportlab is required for PDF exports.'))
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
        styles = getSampleStyleSheet()
        data = [[c['label'] for c in columns]] + [[str(row.get(c['key'], '')) for c in columns] for row in rows[:250]]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe3ef')), ('FONTSIZE', (0, 0), (-1, -1), 7), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        doc.build([Paragraph(report['name'], styles['Title']), Paragraph('%s rows' % len(rows), styles['Normal']), Spacer(1, 8), table])
        output.seek(0)
        return output.read()

    def _export_html(self, report, columns, rows, payload):
        def esc(value):
            return str(value if value is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        def row_class(row):
            text = ' '.join(str(v).lower() for v in row.values())
            if any(x in text for x in ['kırmızı', 'high', 'yüksek', 'overdue', 'gecik']):
                return 'danger'
            if any(x in text for x in ['orta', 'medium', 'takip']):
                return 'warning'
            if any(x in text for x in ['paid', 'kapandı', 'low', 'düşük']):
                return 'success'
            return ''

        head = ''.join('<th>%s</th>' % esc(c['label']) for c in columns)
        body = ''.join(
            '<tr class="%s">%s</tr>' % (
                row_class(row),
                ''.join('<td>%s</td>' % esc(row.get(c['key'], '')) for c in columns),
            )
            for row in rows
        )
        kpis = ''.join('<div class="kpi"><b>{}</b><br>{}</div>'.format(esc(k['label']), esc(k['value'])) for k in payload.get('kpis', []))
        totals_html = ''.join(
            '<div class="kpi"><b>{}</b><br>{}</div>'.format(
                esc(next((c['label'] for c in columns if c['key'] == key), key)),
                esc(round(value, 2) if isinstance(value, float) else value),
            )
            for key, value in (payload.get('totals') or {}).items()
        )
        max_value = max([p.get('value') or 0 for p in payload.get('chart', [])] or [1]) or 1
        chart_html = ''.join(
            '<div class="bar"><span>{}</span><i style="width:{}%"></i><b>{}</b></div>'.format(
                esc(p['label']),
                max(4, min(100, ((p.get('value') or 0) / max_value) * 100)),
                esc(round(p.get('value') or 0, 2)),
            )
            for p in payload.get('chart', [])
        )
        return """<!doctype html><html><head><meta charset="utf-8"><style>
        body{{font-family:Arial,sans-serif;color:#111827;padding:24px}}h1{{margin:0 0 6px}}.muted{{color:#64748b}}table{{width:100%;border-collapse:collapse;margin-top:18px}}th{{background:#0f172a;color:#fff;text-align:left}}th,td{{border:1px solid #dbe3ef;padding:8px;font-size:12px}}tr.danger td{{background:#fee2e2}}tr.warning td{{background:#fef3c7}}tr.success td{{background:#dcfce7}}.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}}.kpi{{border:1px solid #dbe3ef;padding:10px 14px;border-radius:8px;min-width:140px}}.bar{{display:grid;grid-template-columns:220px 1fr 100px;gap:10px;align-items:center;margin:6px 0}}.bar i{{display:block;height:12px;background:#2dd4bf;border-radius:99px}}
        </style></head><body><h1>{}</h1><p class="muted">{}</p><p>{} - {} rows</p><h3>KPIs</h3><div class="kpis">{}</div><h3>Totals</h3><div class="kpis">{}</div><h3>Chart</h3>{}<table><thead><tr>{}</tr></thead><tbody>{}</tbody></table></body></html>""".format(
            esc(report['name']), esc(report.get('description', '')), esc(fields.Datetime.to_string(fields.Datetime.now())), len(rows), kpis, totals_html, chart_html, head, body)

    def _export_pdf(self, report, columns, rows, payload):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
        except ImportError:
            raise UserError(_('reportlab is required for PDF exports.'))
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
        styles = getSampleStyleSheet()
        
        font_name = 'Helvetica'
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont('CustomFont', path))
                    font_name = 'CustomFont'
                    styles['Title'].fontName = font_name
                    styles['Normal'].fontName = font_name
                    break
                except Exception:
                    pass

        elements = [Paragraph(report['name'], styles['Title']), Paragraph(report.get('description', ''), styles['Normal']), Paragraph('%s rows' % len(rows), styles['Normal']), Spacer(1, 8)]
        totals = payload.get('totals') or {}
        if totals:
            totals_data = [['Total', 'Value']] + [[next((c['label'] for c in columns if c['key'] == key), key), str(round(value, 2))] for key, value in totals.items()]
            totals_table = Table(totals_data)
            totals_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe3ef')), ('FONTSIZE', (0, 0), (-1, -1), 8), ('FONTNAME', (0, 0), (-1, -1), font_name)]))
            elements += [totals_table, Spacer(1, 8)]
        if payload.get('chart'):
            chart_data = [['Chart', 'Value']] + [[p['label'], str(round(p.get('value') or 0, 2))] for p in payload['chart']]
            chart_table = Table(chart_data)
            chart_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ccfbf1')), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe3ef')), ('FONTSIZE', (0, 0), (-1, -1), 8), ('FONTNAME', (0, 0), (-1, -1), font_name)]))
            elements += [chart_table, Spacer(1, 8)]
        data = [[c['label'] for c in columns]] + [[str(row.get(c['key'], '')) for c in columns] for row in rows[:250]]
        table = Table(data, repeatRows=1)
        table_style = [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('GRID', (0, 0), (-1, -1), .25, colors.HexColor('#dbe3ef')), ('FONTSIZE', (0, 0), (-1, -1), 7), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTNAME', (0, 0), (-1, -1), font_name)]
        for idx, row in enumerate(rows[:250], start=1):
            text = ' '.join(str(v).lower() for v in row.values())
            if any(x in text for x in ['kırmızı', 'high', 'yüksek', 'overdue', 'gecik']):
                table_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#fee2e2')))
            elif any(x in text for x in ['orta', 'medium', 'takip']):
                table_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#fef3c7')))
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        doc.build(elements)
        output.seek(0)
        return output.read()
