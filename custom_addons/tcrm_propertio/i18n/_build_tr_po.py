# -*- coding: utf-8 -*-
"""Build a comprehensive tr.po / tr_TR.po for tcrm_propertio from source strings."""
from __future__ import annotations

import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N = os.path.dirname(os.path.abspath(__file__))

# Explicit high-value UI glossary (EN -> TR). Covers menus, sales, CRM bridge, reports.
try:
    from extended_glossary import EXTENDED_GLOSSARY
except ImportError:
    EXTENDED_GLOSSARY = {}

GLOSSARY = {
    # Menus / navigation
    "Propertio": "Propertio",
    "Dashboard": "Gösterge Paneli",
    "Inventory": "Proje stok ve takibi",
    "Envanter": "Proje stok ve takibi",
    "Proje Stok ve Takibi": "Proje stok ve takibi",
    "Proje stok ve takibi": "Proje stok ve takibi",
    # Payments (screenshot TR coverage)
    "Enter Payment": "Ödeme Gir",
    "Post Payment": "Ödemeyi Onayla",
    "Discard": "Vazgeç",
    "Payment Ref": "Ödeme Ref",
    "Payment reference": "Ödeme referansı",
    "Amount Paid": "Ödenen Tutar",
    "Payment Currency": "Ödeme Para Birimi",
    "Payment Date": "Ödeme Tarihi",
    "Exchange Rate": "Döviz Kuru",
    "Covered Amount (Sale Curr)": "Karşılanan Tutar (Satış PB)",
    "Covered Amount": "Karşılanan Tutar",
    "Amount & currency": "Tutar ve para birimi",
    "Amount &amp; currency": "Tutar ve para birimi",
    "Refund / Reversal Entry": "İade / Ters Kayıt",
    "Posted": "Onaylandı",
    "Method": "Yöntem",
    "Option": "Opsiyon",
    "Handover": "Teslim",
    "Unit Number": "Birim No",
    "Gross M²": "Brüt m²",
    "Custom Status": "Özel Durum",
    "Document Type": "Belge Tipi",
    "Filename": "Dosya Adı",
    "File": "Dosya",
    "Upload Date": "Yükleme Tarihi",
    "Verified": "Doğrulandı",
    "Verified By": "Doğrulayan",
    "Expiry Date": "Son Geçerlilik",
    "Required for Sale": "Satış İçin Zorunlu",
    "Tapu Date": "Tapu Tarihi",
    "Appointment": "Randevu",
    "Notary Office": "Noterlik",
    "Documents Ready": "Belgeler Alındı",
    "Documents Received": "Belgeler Alındı",
    "TCMB Rate": "TCMB Kuru",
    "Down Payment Rate": "Peşinat Kuru",
    "Installment Rate": "Taksit Kuru",
    "Project Active?": "Proje Aktif mi?",
    "Sale": "Satış",
    "None": "Yok",
    "Sales": "Satışlar",
    "Collections": "Tahsilat",
    "After-Sales": "Satış Sonrası",
    "After Sales": "Satış Sonrası",
    "Reporting": "Raporlama",
    "Reports": "Raporlar",
    "Management": "Yönetim",
    "Configuration": "Yapılandırma",
    "Master Data": "Ana Veriler",
    "Personnel & Partners": "Personel ve İş Ortakları",
    "Personnel &amp; Partners": "Personel ve İş Ortakları",
    "Unit Features": "Birim Özellikleri",
    "Project Types": "Proje Tipleri",
    "Project Stages": "Proje Aşamaları",
    "Property Categories": "Gayrimenkul Kategorileri",
    "Detailed Statuses": "Detaylı Durumlar",
    "Sale Stages": "Satış Aşamaları",
    "Agencies": "Acenteler",
    "Sales Personnel": "Satış Personeli",
    "Sales Contracts": "Satış Sözleşmeleri",
    "Sale Contract": "Satış Sözleşmesi",
    "Property Sale Contract": "Satış Sözleşmesi",
    "Payment Installment": "Taksit",
    "Installment": "Taksit",
    "Projects": "Projeler",
    "Units": "Birimler",
    "Blocks": "Bloklar",
    "Offers": "Teklifler",
    "Payments": "Ödemeler",
    "Documents": "Belgeler",
    "WhatsApp": "WhatsApp",
    "Audit Log": "Denetim Kaydı",
    "Export": "Dışa Aktar",
    "Reports Center": "Rapor Merkezi",
    "Report Center": "Rapor Merkezi",
    "1. Tahsilat ve Ödemeler": "1. Tahsilat ve Ödemeler",
    "2. Satış Raporları": "2. Satış Raporları",
    "3. Müşteri Raporları": "3. Müşteri Raporları",
    "4. Mali Raporlar": "4. Mali Raporlar",
    "5. Performans Raporları": "5. Performans Raporları",
    "6. Gayrimenkul Raporları": "6. Gayrimenkul Raporları",
    "7. Yönetim ve Uyum": "7. Yönetim ve Uyum",
    "8. Pazarlama ve Müşteri Adayları": "8. Pazarlama ve Müşteri Adayları",
    "Tahsilat ve Ödemeler": "Tahsilat ve Ödemeler",
    "Satış Raporları": "Satış Raporları",
    "Müşteri Raporları": "Müşteri Raporları",
    "Mali Raporlar": "Mali Raporlar",
    "Performans Raporları": "Performans Raporları",
    "Gayrimenkul Raporları": "Gayrimenkul Raporları",
    "Yönetim ve Uyum": "Yönetim ve Uyum",
    "Pazarlama ve Müşteri Adayları": "Pazarlama ve Müşteri Adayları",
    "Hatırlatıcı oluştur": "Hatırlatıcı oluştur",
    "Create Reminder": "Hatırlatıcı oluştur",
    "Reminder To-Do": "Hatırlatıcı Yapılacak",
    "Reminder Calendar Event": "Hatırlatıcı Takvim Etkinliği",
    # Sales contract fields
    "Contract Reference": "Sözleşme Referansı",
    "Contract Ref": "Sözleşme Ref.",
    "Contract No": "Sözleşme No",
    "Manual Contract No": "Manuel Sözleşme No",
    "Customer": "Müşteri",
    "CRM Opportunity": "CRM Fırsatı",
    "Unit": "Birim",
    "Company": "Şirket",
    "Sale Stage": "Satış Aşaması",
    "Project": "Proje",
    "Block": "Blok",
    "Entrance": "Giriş",
    "Floor": "Kat",
    "Gross M2": "Brüt m²",
    "Net M2": "Net m²",
    "Gen. Gross M2": "Gen. Brüt m²",
    "Facade": "Cephe",
    "View": "Manzara",
    "Property Category": "Gayrimenkul Kategorisi",
    "Master Status": "Ana Durum",
    "Parking No": "Otopark No",
    "Parking Type": "Otopark Tipi",
    "Unit Code": "Birim Kodu",
    "Tapu Ref": "Tapu Ref.",
    "Balcony M2": "Balkon m²",
    "Terrace M2": "Teras m²",
    "Garden M2": "Bahçe m²",
    "Floor Gross M2": "Kat Brüt m²",
    "Ground M2": "Zemin m²",
    "Normal M2": "Normal m²",
    "Sale Price": "Satış Fiyatı",
    "Currency": "Para Birimi",
    "Agency 1": "Acente 1",
    "Agency 2": "Acente 2",
    "Sales Person 1": "Satış Danışmanı 1",
    "Sales Person 2": "Satış Danışmanı 2",
    "Sales Person": "Satış Danışmanı",
    "Sales Office": "Satış Ofisi",
    "Department": "Departman",
    "Contact Person": "İlgili Kişi",
    "Activity Person": "Aktivite Sorumlusu",
    "TC/National ID": "TC Kimlik No",
    "Passport No": "Pasaport No",
    "Father Name": "Baba Adı",
    "Spouse Name": "Eş Adı",
    "Accounting Code": "Muhasebe Kodu",
    "Status Detail": "Durum Detayı",
    "VIP Customer": "VIP Müşteri",
    "VIP Note": "VIP Notu",
    "Contract Date": "Sözleşme Tarihi",
    "Notary Date": "Noter Tarihi",
    "Notary Ref No": "Noter Ref. No",
    "Notarized?": "Noter Onaylı mı?",
    "Notary Note": "Noter Notu",
    "Payment Method Detail": "Ödeme Yöntemi Detayı",
    "Bank Validated?": "Banka Onaylı mı?",
    "Bank Approval Date": "Banka Onay Tarihi",
    "Discount Amount": "İndirim Tutarı",
    "Calc. Discount": "Hesaplanan İndirim",
    "Maturity Diff.": "Vade Farkı",
    "Calc. Maturity Diff.": "Hesaplanan Vade Farkı",
    "Invoice Status": "Fatura Durumu",
    "To Invoice": "Faturalanacak",
    "Invoiced": "Faturalandı",
    "Bank Doc Status": "Banka Belge Durumu",
    "Reserve Date": "Rezervasyon Tarihi",
    "Credit Usage Date": "Kredi Kullandırım Tarihi",
    "Sale Date": "Satış Tarihi",
    "Order Date": "Sipariş Tarihi",
    "Payment Plan": "Ödeme Planı",
    "Required": "Zorunlu",
    "Uploaded": "Yüklendi",
    "Total Paid": "Toplam Ödenen",
    "Balance": "Bakiye",
    "Total Amount": "Toplam Tutar",
    "Status": "Durum",
    "Draft": "Taslak",
    "Confirmed": "Onaylandı",
    "Cancelled": "İptal Edildi",
    "Canceled": "İptal Edildi",
    "Done": "Tamamlandı",
    "Confirm Sale": "Satışı Onayla",
    "Cancel": "İptal",
    "New": "Yeni",
    "Active": "Aktif",
    "Name": "Ad",
    "Description": "Açıklama",
    "Notes": "Notlar",
    "Date": "Tarih",
    "Amount": "Tutar",
    "Type": "Tip",
    "Sequence": "Sıra",
    "Color": "Renk",
    "Icon": "İkon",
    "City": "Şehir",
    "Country": "Ülke",
    "Address": "Adres",
    "Phone": "Telefon",
    "Email": "E-posta",
    "Priority": "Öncelik",
    "Source": "Kaynak",
    "Lead Source": "Müşteri Kaynağı",
    "Medium": "Kanal",
    "Campaign": "Kampanya",
    "Tags": "Etiketler",
    "Stage": "Aşama",
    "Probability": "Olasılık",
    "Expected Revenue": "Beklenen Gelir",
    "Available": "Müsait",
    "Reserved": "Rezerve",
    "Sold": "Satıldı",
    "Delivered": "Teslim Edildi",
    "Blocked": "Bloke",
    "Under Construction": "İnşaat Halinde",
    "Ready to Move": "Yerleşime Hazır",
    "Residential": "Konut",
    "Commercial": "Ticari",
    "Selling": "Satışta",
    "Planning": "Planlama",
    "Completed": "Tamamlandı",
    # Partner lead sources
    "Referral": "Referans",
    "Social Media": "Sosyal Medya",
    "Website": "Web Sitesi",
    "Walk-in": "Ofis Ziyareti",
    "Exhibition": "Fuar",
    "Other": "Diğer",
    "Instagram": "Instagram",
    "Facebook": "Facebook",
    "Sahibinden": "Sahibinden",
    "Indoor / Showroom": "İç Mekan / Showroom",
    "Landline": "Sabit Hat",
    "Sabit Hat": "Sabit Hat",
    "WhatsApp": "WhatsApp",
    "Google Ads": "Google Ads",
    "Portal": "Portal",
    # Collections / payments
    "Payment": "Ödeme",
    "Collection": "Tahsilat",
    "Due Date": "Vade Tarihi",
    "Paid": "Ödendi",
    "Partial": "Kısmi",
    "Overdue": "Gecikmiş",
    "Pending": "Beklemede",
    "Down Payment": "Peşinat",
    "Installment Amount": "Taksit Tutarı",
    "Payment Method": "Ödeme Yöntemi",
    "Cash": "Nakit",
    "Bank Transfer": "Havale/EFT",
    "Credit Card": "Kredi Kartı",
    "Cheque": "Çek",
    "Receipt": "Makbuz",
    # Reports
    "Sales & Collection Report": "Tahsilat ve Satış Durumu",
    "Sales &amp; Collection Report": "Tahsilat ve Satış Durumu",
    "Project GDV / Plan Table": "Proje Nakit Durumu",
    "Cash Flow Forecast": "Gelecek Nakit Akışı",
    "Sales Agent Leaderboard": "Danışman Karnesi",
    "Red Alert Customers": "Kırmızı Alarm Müşteriler",
    "Global period": "Global dönem",
    "From": "Başlangıç",
    "To": "Bitiş",
    "Reset": "Sıfırla",
    "Date range was adjusted so the start date is not after the end date.": (
        "Başlangıç tarihi bitiş tarihinden sonra olamayacağı için tarih aralığı otomatik düzeltildi."
    ),
    "Print": "Yazdır",
    "Generate": "Oluştur",
    "Preview": "Önizleme",
    "Filter": "Filtre",
    "Search": "Ara",
    "Group By": "Grupla",
    "Favorites": "Favoriler",
    "Save": "Kaydet",
    "Create": "Oluştur",
    "Edit": "Düzenle",
    "Delete": "Sil",
    "Confirm": "Onayla",
    "Reject": "Reddet",
    "Approve": "Onayla",
    "Close": "Kapat",
    "Open": "Açık",
    "Lost": "Kayıp",
    "Won": "Satış Yapıldı",
    "Kazanıldı": "Satış Yapıldı",
    "Satış Yapıldı": "Satış Yapıldı",
    "Discard": "Vazgeç",
    "Delete": "Sil",
    "Created": "Oluşturma Tarihi",
    "Creation Date": "Oluşturma Tarihi",
    "Oluşturuldu": "Oluşturma Tarihi",
    "Expected Revenue": "Beklenen Gelir",
    "Generate Leads": "Lead Oluştur",
    "Inbox": "Gelen Kutusu",
    "Today": "Bugün",
    "This Week": "Bu Hafta",
    "This Month": "Bu Ay",
    "Later": "Daha Sonra",
    "Done": "Tamamlandı",
    "Cancelled": "İptal Edildi",
    "Investor": "Yatırımcı",
    "Contracts": "Sözleşmeler",
    "Property": "Gayrimenkul",
    "Target Property": "Hedef Gayrimenkul",
    "Property Project": "Gayrimenkul Projesi",
    "Property Unit": "Gayrimenkul Birimi",
    "Property Contracts": "Gayrimenkul Sözleşmeleri",
    "Gayrimenkul": "Gayrimenkul",
    "Hedef Gayrimenkul": "Hedef Gayrimenkul",
    "Gayrimenkul Projesi": "Gayrimenkul Projesi",
    "Gayrimenkul Birimi": "Gayrimenkul Birimi",
    "Gayrimenkul Sözleşmeleri": "Gayrimenkul Sözleşmeleri",
    "Sözleşmeler": "Sözleşmeler",
    # Lead Havuzu filters / groups
    "Lead Havuzu": "Lead Havuzu",
    "Lead / Opportunity": "Lead / Fırsat",
    "Lead / Fırsat": "Lead / Fırsat",
    "New Leads": "Yeni Leadler",
    "Yeni Leadler": "Yeni Leadler",
    "Qualified Leads": "Nitelikli Leadler",
    "Nitelikli Leadler": "Nitelikli Leadler",
    "Opportunities": "Fırsatlar",
    "Fırsatlar": "Fırsatlar",
    "My Leads": "Leadlerim",
    "Leadlerim": "Leadlerim",
    "Unassigned": "Atanmamış",
    "Atanmamış": "Atanmamış",
    "Creation Date": "Oluşturma Tarihi",
    "Oluşturma Tarihi": "Oluşturma Tarihi",
    "Salesperson": "Satış Danışmanı",
    "Satış Danışmanı": "Satış Danışmanı",
    "Sales Team": "Satış Ekibi",
    "Satış Ekibi": "Satış Ekibi",
    "Tag": "Etiket",
    "Etiket": "Etiket",
    "Müşteri": "Müşteri",
    "Kaynak": "Kaynak",
    "Kanal": "Kanal",
    "Kampanya": "Kampanya",
    "Aşama": "Aşama",
    "Proje": "Proje",
    "Tip": "Tip",
    "Kazanıldı": "Satış Yapıldı",
    "Kaybedildi": "Kayıp",
    "Arşivlendi": "Arşivlendi",
    # Project form
    "Project Name": "Proje Adı",
    "Proje Adı": "Proje Adı",
    "Amenities & Features": "Olanaklar ve Özellikler",
    "Amenities &amp; Features": "Olanaklar ve Özellikler",
    "Olanaklar ve Özellikler": "Olanaklar ve Özellikler",
    "Standard Amenities": "Standart Olanaklar",
    "Standart Olanaklar": "Standart Olanaklar",
    "Available Upgrades": "Mevcut Yükseltmeler",
    "Mevcut Yükseltmeler": "Mevcut Yükseltmeler",
    "Bloklar": "Bloklar",
    "Total GDV": "Toplam GDV",
    "Toplam GDV": "Toplam GDV",
    "Features & Upgrades": "Özellikler ve Yükseltmeler",
    "Features &amp; Upgrades": "Özellikler ve Yükseltmeler",
    "Özellikler ve Yükseltmeler": "Özellikler ve Yükseltmeler",
    "Financial Stats": "Mali İstatistikler",
    "Mali İstatistikler": "Mali İstatistikler",
    "Addable Features": "Eklenebilir Özellikler",
    "Eklenebilir Özellikler": "Eklenebilir Özellikler",
    # Reports Center OWL
    "Rapor Merkezi": "Rapor Merkezi",
    "Category": "Kategori",
    "Kategori": "Kategori",
    "Search reports": "Rapor ara",
    "Rapor ara": "Rapor ara",
    "Ara": "Ara",
    "Run": "Çalıştır",
    "Çalıştır": "Çalıştır",
    "Kaydet": "Kaydet",
    "List": "Liste",
    "Liste": "Liste",
    "Groups": "Gruplar",
    "Gruplar": "Gruplar",
    "Chart": "Grafik",
    "Grafik": "Grafik",
    "Loading report...": "Rapor yükleniyor...",
    "Rapor yükleniyor...": "Rapor yükleniyor...",
    "Accrual": "Tahakkuk",
    "Tahakkuk": "Tahakkuk",
    "Nakit": "Nakit",
    "Group": "Grup",
    "Grup": "Grup",
    "Chart Group": "Grafik Grubu",
    "Grafik Grubu": "Grafik Grubu",
    "Chart Metric": "Grafik Metriği",
    "Grafik Metriği": "Grafik Metriği",
    "Auto": "Otomatik",
    "Otomatik": "Otomatik",
    "Yok": "Yok",
    "Tümü": "Tümü",
    "Başlangıç": "Başlangıç",
    "Bitiş": "Bitiş",
    "Uygula": "Uygula",
    "Showing first 500 rows. Exports include the filtered result set.": (
        "İlk 500 satır gösteriliyor. Dışa aktarımlar filtrelenmiş sonucu içerir."
    ),
    "İlk 500 satır gösteriliyor. Dışa aktarımlar filtrelenmiş sonucu içerir.": (
        "İlk 500 satır gösteriliyor. Dışa aktarımlar filtrelenmiş sonucu içerir."
    ),
    "The report could not be generated. Check server logs for details.": (
        "Rapor oluşturulamadı. Ayrıntılar için sunucu günlüklerine bakın."
    ),
    "Rapor oluşturulamadı. Ayrıntılar için sunucu günlüklerine bakın.": (
        "Rapor oluşturulamadı. Ayrıntılar için sunucu günlüklerine bakın."
    ),
    "Report preset name": "Rapor ön ayar adı",
    "Rapor ön ayar adı": "Rapor ön ayar adı",
    "Report preset saved.": "Rapor ön ayarı kaydedildi.",
    "Rapor ön ayarı kaydedildi.": "Rapor ön ayarı kaydedildi.",
    "No chart data for current filters.": "Mevcut filtreler için grafik verisi yok.",
    "Mevcut filtreler için grafik verisi yok.": "Mevcut filtreler için grafik verisi yok.",
    "Choose a Group field and apply.": "Bir grup alanı seçip uygulayın.",
    "Bir grup alanı seçip uygulayın.": "Bir grup alanı seçip uygulayın.",
    "No data found for the selected filters.": "Seçilen filtreler için veri bulunamadı.",
    "Seçilen filtreler için veri bulunamadı.": "Seçilen filtreler için veri bulunamadı.",
    # Activity reminders
    "Hatırlatıcı Yapılacak": "Hatırlatıcı Yapılacak",
    "Hatırlatıcı Takvim Etkinliği": "Hatırlatıcı Takvim Etkinliği",
    "Aktivite": "Aktivite",
    "Lead / Fırsat: %s": "Lead / Fırsat: %s",
    "Aktivite Tipi: %s": "Aktivite Tipi: %s",
    "Son Tarih: %s": "Son Tarih: %s",
    "Sorumlu: %s": "Sorumlu: %s",
    "Müşteri / Kişi: %s": "Müşteri / Kişi: %s",
    "Proje: %s": "Proje: %s",
    "Notlar: %s": "Notlar: %s",
    "CRM Bağlantısı: %s": "CRM Bağlantısı: %s",
    "Create a calendar event and personal To-Do when scheduling a CRM lead activity.": (
        "CRM lead aktivitesi planlanırken takvim etkinliği ve kişisel Yapılacak oluştur."
    ),
    "CRM lead aktivitesi planlanırken takvim etkinliği ve kişisel Yapılacak oluştur.": (
        "CRM lead aktivitesi planlanırken takvim etkinliği ve kişisel Yapılacak oluştur."
    ),
    # Envanter rename leftovers
    "Tip Bazlı Satış ve Envanter": "Tip Bazlı Satış ve Proje Stok ve Takibi",
    "Tipe Göre Satış ve Envanter": "Tipe Göre Satış ve Proje Stok ve Takibi",
    "Tip Bazlı Satış ve Proje Stok ve Takibi": "Tip Bazlı Satış ve Proje Stok ve Takibi",
    "Tipe Göre Satış ve Proje Stok ve Takibi": "Tipe Göre Satış ve Proje Stok ve Takibi",
    "2. Tipe Göre Satış ve Envanter": "2. Tipe Göre Satış ve Proje Stok ve Takibi",
    "Related Sale": "İlgili Satış",
    "Create Sale Contract": "Satış Sözleşmesi Oluştur",
    "Reservation": "Rezervasyon",
    "Handover": "Teslim",
    "Complaint": "Şikayet",
    "Request": "Talep",
    "Ticket": "Destek Kaydı",
    "Assigned To": "Atanan",
    "Created On": "Oluşturulma",
    "Last Update": "Son Güncelleme",
    "Total": "Toplam",
    "Subtotal": "Ara Toplam",
    "Tax": "Vergi",
    "List Price": "Liste Fiyatı",
    "Discount": "İndirim",
    "Commission": "Komisyon",
    "Broker": "Broker",
    "Agency": "Acente",
    "Customer Type": "Müşteri Tipi",
    "Individual": "Bireysel",
    "Company": "Şirket",
    "Marital Status": "Medeni Durum",
    "Single": "Bekar",
    "Married": "Evli",
    "Divorced": "Boşanmış",
    "Widowed": "Dul",
    "ID Type": "Kimlik Tipi",
    "National ID": "TC Kimlik",
    "Passport": "Pasaport",
    "Risk Level": "Risk Seviyesi",
    "Low": "Düşük",
    "Medium": "Orta",
    "High": "Yüksek",
    "Normal": "Normal",
    "Hot": "Sıcak",
    "Investor": "Yatırımcı",
    "Too expensive": "Çok pahalı",
    "Unit Reservation Fee": "Birim Rezervasyon Ücreti",
    "Residential Unit (Property Sale)": "Konut Birimi (Gayrimenkul Satışı)",
    "1+1 Apartment": "1+1 Daire",
    "2+1 Apartment": "2+1 Daire",
    "3+1 Apartment": "3+1 Daire",
    "Villa": "Villa",
    "Swimming Pool": "Yüzme Havuzu",
    "Fitness Center": "Fitness Merkezi",
    "Sea View": "Deniz Manzarası",
    "Covered Parking": "Kapalı Otopark",
    "City View": "Şehir Manzarası",
    "Garden View": "Bahçe Manzarası",
    "Pool View": "Havuz Manzarası",
    "Panoramic": "Panoramik",
    "Block A": "Blok A",
    "Block B": "Blok B",
    "Block C": "Blok C",
    "None": "Yok",
    "Yes": "Evet",
    "No": "Hayır",
    "All": "Tümü",
    "Today": "Bugün",
    "This Week": "Bu Hafta",
    "This Month": "Bu Ay",
    "This Year": "Bu Yıl",
    "Custom": "Özel",
    "Actions": "İşlemler",
    "More": "Daha Fazla",
    "Settings": "Ayarlar",
    "Help": "Yardım",
    "Information": "Bilgi",
    "General": "Genel",
    "Details": "Detaylar",
    "History": "Geçmiş",
    "Attachments": "Ekler",
    "Messages": "Mesajlar",
    "Schedule": "Planla",
    "Activity": "Aktivite",
    "Log Note": "Not Ekle",
    "Send Message": "Mesaj Gönder",
    "Mark as Done": "Tamamlandı İşaretle",
    "In Progress": "Devam Ediyor",
    "On Hold": "Beklemede",
    "Archived": "Arşivlendi",
    "Archive": "Arşivle",
    "Unarchive": "Arşivden Çıkar",
    "Duplicate": "Çoğalt",
    "Import": "İçe Aktar",
    "Refresh": "Yenile",
    "Apply": "Uygula",
    "Clear": "Temizle",
    "Back": "Geri",
    "Next": "İleri",
    "Previous": "Önceki",
    "Finish": "Bitir",
    "Start": "Başlat",
    "Stop": "Durdur",
    "Warning": "Uyarı",
    "Error": "Hata",
    "Success": "Başarılı",
    "Loading": "Yükleniyor",
    "No data": "Veri yok",
    "No records found": "Kayıt bulunamadı",
    "Are you sure?": "Emin misiniz?",
    "This action cannot be undone.": "Bu işlem geri alınamaz.",
}

GLOSSARY.update(EXTENDED_GLOSSARY)

def extract_strings() -> OrderedDict:
    found: OrderedDict[str, str] = OrderedDict()

    def add(s: str, src: str):
        s = (s or "").strip()
        if not s or len(s) < 2 or len(s) > 180:
            return
        if s.startswith(("fa-", "%", "{", "/", "#", ".")) or s.isdigit():
            return
        # skip technical xmlids / field names
        if re.fullmatch(r"[a-z0-9_.]+", s):
            return
        if s not in found:
            found[s] = src

    for dirpath, _, files in os.walk(ROOT):
        if any(x in dirpath for x in ("i18n", "__pycache__", "static/description", "node_modules")):
            continue
        for fname in files:
            if not fname.endswith((".py", ".xml", ".js")):
                continue
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, ROOT)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if fname.endswith(".py"):
                for m in re.finditer(r"""(?:string|_)\(\s*['"]([^'"]+)['"]""", text):
                    add(m.group(1), rel)
                for m in re.finditer(r"""help\s*=\s*['"]([^'"]+)['"]""", text):
                    add(m.group(1), rel)
                for m in re.finditer(
                    r"""\(\s*['"][a-z0-9_]+['"]\s*,\s*['"]([^'"]+)['"]\s*\)""", text
                ):
                    add(m.group(1), rel)
            else:
                for m in re.finditer(
                    r"""(?:string|title|placeholder|confirm|help|alt)\s*=\s*['"]([^'"]+)['"]""",
                    text,
                ):
                    add(m.group(1), rel)
                for m in re.finditer(r"""<menuitem[^>]*\sname=['"]([^'"]+)['"]""", text):
                    add(m.group(1), rel)
                for m in re.finditer(r"""<field name=['"]name['"]>([^<]+)</field>""", text):
                    add(m.group(1), rel)
                for m in re.finditer(
                    r""">([A-ZÇĞİÖŞÜa-zçğıöşü][^<>{}]{0,80})</(?:button|span|label|a|strong|h[1-6]|th)>""",
                    text,
                ):
                    add(m.group(1).replace("&amp;", "&").strip(), rel)
                # OWL / JS _t() and fallback literals
                for m in re.finditer(r"""_t\(\s*["']([^"']+)["']\s*\)""", text):
                    add(m.group(1), rel)
                for m in re.finditer(
                    r"""\|\|\s*['"]([^'"]{2,80})['"]""",
                    text,
                ):
                    add(m.group(1), rel)
    # Always include glossary keys even if extractor missed them
    for k in GLOSSARY:
        add(k, "glossary")
    return found


HEADER = """# Turkish (Turkey) translation for TCRM Propertio.
# Copyright (C) TCRM
# This file is distributed under the same license as the tcrm_propertio package.
#
msgid ""
msgstr ""
"Project-Id-Version: TCRM Propertio 1.2\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2026-07-24 00:00+0000\\n"
"PO-Revision-Date: 2026-07-24 00:00+0000\\n"
"Last-Translator: TCRM <info@tcrm.com>\\n"
"Language-Team: Turkish\\n"
"Language: tr_TR\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=1; plural=0;\\n"

"""

# CRM module overrides (loaded only if imported into crm; kept for reference / dual load)
CRM_OVERRIDES = [
    ("CRM", "Müşteri Takibi"),
    ("Leads", "Yeni Müşteriler"),
    ("Lead", "Yeni Müşteri"),
    ("Opportunity", "Satış Bekleyen"),
    ("Opportunities", "Satış Bekleyenler"),
    ("Source", "Kaynak"),
]


def po_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def translate(msgid: str) -> str:
    if msgid in GLOSSARY:
        return GLOSSARY[msgid]
    # light heuristics
    replacements = [
        ("Sale Price", "Satış Fiyatı"),
        ("Sale ", "Satış "),
        ("Sales ", "Satış "),
        ("Contract ", "Sözleşme "),
        ("Payment ", "Ödeme "),
        ("Customer ", "Müşteri "),
        ("Project ", "Proje "),
        ("Unit ", "Birim "),
        ("Report", "Rapor"),
        ("Date", "Tarih"),
        ("Amount", "Tutar"),
        ("Status", "Durum"),
        ("Type", "Tip"),
        ("Name", "Ad"),
        ("Total ", "Toplam "),
        (" & ", " ve "),
    ]
    out = msgid
    for a, b in replacements:
        if a in out:
            out = out.replace(a, b)
    return out if out != msgid else msgid  # leave untranslated if no mapping


def build():
    strings = extract_strings()
    lines = [HEADER]
    translated = 0
    for msgid, src in strings.items():
        tr = translate(msgid)
        if tr != msgid:
            translated += 1
        lines.append("#. module: tcrm_propertio\n")
        lines.append("#: %s\n" % src.replace("\\", "/"))
        lines.append('msgid "%s"\n' % po_escape(msgid))
        lines.append('msgstr "%s"\n' % po_escape(tr))
        lines.append("\n")

    lines.append("# ========== CRM term overrides (import into crm tr.po if needed) ==========\n")
    for en, tr in CRM_OVERRIDES:
        lines.append("#. module: crm\n")
        lines.append('msgid "%s"\n' % po_escape(en))
        lines.append('msgstr "%s"\n' % po_escape(tr))
        lines.append("\n")

    body = "".join(lines)
    for name in ("tr.po", "tr_TR.po"):
        path = os.path.join(I18N, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        print("Wrote", path, "entries=", len(strings), "mapped=", translated)


if __name__ == "__main__":
    build()
