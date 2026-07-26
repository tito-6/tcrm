# -*- coding: utf-8 -*-
"""Turkish display labels for Propertio report HTML/XLSX/PDF chrome.

Internal data keys stay in English; this map is applied at render time.
"""

from __future__ import annotations

TRANSLATIONS = {
    # Chrome
    'Generated:': 'Oluşturulma:',
    'Period:': 'Dönem:',
    'Start': 'Başlangıç',
    'End': 'Bitiş',
    'rows': 'satır',
    'TOTAL': 'TOPLAM',
    'Total': 'Toplam',
    'No data found for the selected filters.': 'Seçilen filtrelere uygun veri bulunamadı.',
    'Print / Save as PDF': 'Yazdır / PDF Olarak Kaydet',
    "Tip: Use your browser's print function (Ctrl+P) to save as PDF": (
        'İpucu: PDF kaydetmek için tarayıcının yazdır işlevini kullanın (Ctrl+P)'
    ),
    'Preview error:': 'Önizleme hatası:',
    'This report link has been closed or is invalid.': 'Bu rapor bağlantısı kapatılmış veya geçersiz.',
    'Public Report': 'Herkese Açık Rapor',
    # Statuses
    'Paid': 'Ödendi',
    'Overdue': 'Gecikmiş',
    'Upcoming': 'Yaklaşan',
    'Future': 'İleri Tarihli',
    'Active': 'Aktif',
    'Available': 'Müsait',
    'Reserved': 'Rezerve',
    'Sold': 'Satıldı',
    'Draft': 'Taslak',
    'Confirmed': 'Onaylandı',
    'Cancelled': 'İptal Edildi',
    'Pending': 'Beklemede',
    'Partial': 'Kısmi',
    # Common columns
    'Contract': 'Sözleşme',
    'Customer': 'Müşteri',
    'Unit': 'Birim',
    'Sale Value': 'Satış Tutarı',
    'Collected': 'Tahsil Edilen',
    'Outstanding': 'Kalan',
    'Collection %': 'Tahsilat %',
    'Payment Status': 'Ödeme Durumu',
    'Status': 'Durum',
    'Project': 'Proje',
    'Block': 'Blok',
    'Due Date': 'Vade Tarihi',
    'Description': 'Açıklama',
    'Type': 'Tip',
    'Amount': 'Tutar',
    'Paid Amount': 'Ödenen Tutar',
    'Residual': 'Kalan',
    'Balance': 'Bakiye',
    'Date': 'Tarih',
    'Salesperson': 'Satış Danışmanı',
    'Sales Person': 'Satış Danışmanı',
    'Unit Type': 'Birim Tipi',
    'Total Units': 'Toplam Birim',
    'Total Stock Value': 'Toplam Stok Değeri',
    'Sold Value': 'Satılan Değer',
    'Available Value': 'Müsait Değer',
    'Uncategorized': 'Kategorisiz',
    'Down Payment': 'Peşinat',
    'Installment': 'Taksit',
    'Balloon Payment': 'Balon Ödeme',
    'Name': 'Ad',
    'Phone': 'Telefon',
    'Email': 'E-posta',
    'Source': 'Kaynak',
    'Stage': 'Aşama',
    'Notes': 'Notlar',
    'Currency': 'Para Birimi',
    'Exchange Rate': 'Kur',
    'Invoice': 'Fatura',
    'Title Deed': 'Tapu',
    'Handover': 'Teslim',
    'Commission': 'Komisyon',
    'VAT': 'KDV',
    'Cash': 'Nakit',
    'Bank': 'Banka',
    # Summary cards
    'Total Sales Value': 'Toplam Satış Tutarı',
    'Total Collected': 'Toplam Tahsilat',
    'Total Outstanding': 'Toplam Kalan',
    'Collection Rate': 'Tahsilat Oranı',
    # Report titles
    'Sales Collection Summary Report': 'Satış Tahsilat Özet Raporu',
    'Type-Based Sales & Inventory Analysis': 'Tip Bazlı Satış ve Proje Stok ve Takibi Analizi',
    'Customer Journey Report': 'Müşteri Yolculuğu Raporu',
    'Sales Report': 'Satış Raporu',
    'Cash Register Report': 'Kasa Raporu',
    'Approval-Based Sales Analysis': 'Onay Bazlı Satış Analizi',
    'Total Sales Chart Report': 'Toplam Satış Grafiği',
    'Incoming & Expected Payments Forecast': 'Gelen ve Beklenen Ödemeler',
    'End-of-Day Meeting Report': 'Gün Sonu Toplantı Raporu',
    'Daily Sales Quantity Report': 'Günlük Satış Adedi Raporu',
    'Cash Flow Statement': 'Nakit Akış Tablosu',
    'Employee Performance Report': 'Personel Performans Raporu',
    'Sales Status Report': 'Satış Durum Raporu',
    'Payment Plan Table': 'Ödeme Planı Tablosu',
    'Expected Payment List': 'Beklenen Ödeme Listesi',
    'Authorization Matrix': 'Yetki Matrisi',
    'Sales Exchange Rate Analysis': 'Satış Kur Analizi',
    'Daily Cash Register Report': 'Günlük Kasa Raporu',
    'CRM Activity Log': 'CRM Aktivite Kaydı',
    'Individual Customer Journey': 'Bireysel Müşteri Yolculuğu',
    'Title Deed & Invoice Status': 'Tapu ve Fatura Durumu',
    'Independent Units Report': 'Bağımsız Bölüm Raporu',
    'Construction Progress Report': 'İnşaat İlerleme Raporu',
    'Web Form Lead Tracking': 'Web Form Lead Takibi',
    'Customer Overall Status': 'Müşteri Genel Durumu',
    'Payment Plan (VAT Included)': 'Ödeme Planı (KDV Dahil)',
    'Lead Report': 'Lead Raporu',
    'Advertising Leads Report': 'Reklam Lead Raporu',
    'Commission Report (Müşteri Prim Raporu)': 'Komisyon / Prim Raporu',
    'Title Deed Status Report (Tapu Durum Raporu)': 'Tapu Durum Raporu',
    'Handover Status Report (Teslim Durumu)': 'Teslim Durum Raporu',
    'VAT Summary Report (KDV Özet)': 'KDV Özet Raporu',
    'Cash Register Summary (Kasa Özeti)': 'Kasa Özeti',
    'Customer Segmentation Report': 'Müşteri Segmentasyon Raporu',
    'Project Profitability Analysis': 'Proje Kârlılık Analizi',
    'Communication Report (İletişim Raporu)': 'İletişim Raporu',
}


def t(text) -> str:
    """Translate a report label; unknown strings pass through."""
    if text is None:
        return ''
    if not isinstance(text, str):
        return text
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    # Case-insensitive fallback for status-like tokens
    low = text.strip()
    for key, val in TRANSLATIONS.items():
        if key.lower() == low.lower():
            return val
    return text
