# -*- coding: utf-8 -*-
import base64
import logging
from datetime import datetime, date, timedelta

from tcrm import models, fields, api, _
from tcrm.exceptions import UserError

_logger = logging.getLogger(__name__)


class PropertioUnifiedReportWizard(models.TransientModel):
    _name = 'propertio.unified.report.wizard'
    _description = 'Birleşik Rapor Görüntüleyici'

    report_type = fields.Selection([
        ('sales_collection_summary', 'Satış Tahsilat Özeti'),
        ('payment_plan_table', 'Ödeme Planı Tablosu'),
        ('expected_payment_list', 'Beklenen Ödeme Listesi'),
        ('payment_plan_vat', 'Ödeme Planı (KDV Dahil)'),
        ('incoming_payments_chart', 'Gelen ve Beklenen Ödemeler'),
        ('sales_report', 'Satış Raporu'),
        ('type_based_sales', 'Tip Bazlı Satış ve Proje Stok ve Takibi'),
        ('approval_based_sales', 'Onay Bazlı Satışlar'),
        ('total_sales_chart', 'Toplam Satış Grafiği'),
        ('daily_sales_quantity', 'Günlük Satış Adedi'),
        ('sales_status', 'Satış Durumu'),
        ('sales_exchange_rate', 'Satış Kur Analizi'),
        ('customer_journey', 'Müşteri Yolculuğu'),
        ('customer_journey_individual', 'Bireysel Müşteri Yolculuğu'),
        ('customer_overall_status', 'Müşteri Genel Durumu'),
        ('cash_register', 'Kasa Raporu'),
        ('daily_cash_register', 'Günlük Kasa'),
        ('cash_flow_statement', 'Nakit Akış Tablosu'),
        ('employee_performance', 'Personel Performansı'),
        ('end_of_day_meeting', 'Gün Sonu Toplantısı'),
        ('independent_units', 'Bağımsız Bölümler'),
        ('construction_progress', 'İnşaat İlerlemesi'),
        ('title_deed_invoice', 'Tapu ve Fatura'),
        ('authorization_matrix', 'Yetki Matrisi'),
        ('crm_log_records', 'CRM Aktivite Kaydı'),
        ('lead_report', 'Lead Raporu'),
        ('advertising_leads', 'Reklam Leadleri'),
        ('web_form_tracking', 'Web Form Takibi'),
        ('commission_report', 'Komisyon Raporu'),
        ('tapu_status', 'Tapu Durumu'),
        ('handover_status', 'Teslim Durumu'),
        ('vat_summary', 'KDV Özeti'),
        ('cash_register_summary', 'Kasa Özeti'),
        ('customer_segmentation', 'Müşteri Segmentasyonu'),
        ('project_profitability', 'Proje Kârlılığı'),
        ('communication_report', 'İletişim Raporu'),
    ], string='Rapor Tipi', required=True, default='sales_collection_summary')

    export_format = fields.Selection([
        ('xlsx', 'Excel (XLSX)'),
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
        ('html', 'HTML (Tarayıcıda Aç)'),
    ], string='Dışa Aktarma Formatı', required=True, default='xlsx')

    date_from = fields.Date(string='Başlangıç Tarihi')
    date_to = fields.Date(string='Bitiş Tarihi')

    date_filter = fields.Selection([
        ('custom', 'Özel Aralık'),
        ('today', 'Bugün'),
        ('yesterday', 'Dün'),
        ('this_week', 'Bu Hafta'),
        ('last_week', 'Geçen Hafta'),
        ('this_month', 'Bu Ay'),
        ('last_month', 'Geçen Ay'),
        ('this_quarter', 'Bu Çeyrek'),
        ('this_year', 'Bu Yıl'),
        ('last_year', 'Geçen Yıl'),
        ('all', 'Tüm Zamanlar'),
    ], string='Tarih Filtresi', default='this_month')

    project_id = fields.Many2one('propertio.project', string='Proje')
    partner_id = fields.Many2one('res.partner', string='Müşteri')
    user_id = fields.Many2one('res.users', string='Satış Danışmanı')

    file_data = fields.Binary(string='Dosya', readonly=True)
    file_name = fields.Char(string='Dosya Adı', readonly=True)
    state = fields.Selection([
        ('draft', 'Yapılandır'),
        ('done', 'Hazır'),
    ], default='draft')

    html_preview = fields.Html(string='Rapor Önizleme', readonly=True, sanitize=False)

    share_id = fields.Many2one('propertio.report.share', string='Paylaşım', readonly=True)
    share_url = fields.Char(string='Herkese Açık Bağlantı', readonly=True)
    share_is_public = fields.Boolean(string='Bağlantı Açık', related='share_id.is_public', readonly=True)

    def name_get(self):
        result = []
        for record in self:
            name = dict(self._fields['report_type'].selection).get(record.report_type) or 'Rapor Görüntüleyici'
            result.append((record.id, name))
        return result

    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        today = date.today()
        mapping = {
            'today': (today, today),
            'yesterday': (today - timedelta(days=1), today - timedelta(days=1)),
            'this_week': (today - timedelta(days=today.weekday()), today),
            'last_week': (
                today - timedelta(days=today.weekday() + 7),
                today - timedelta(days=today.weekday() + 1),
            ),
            'this_month': (today.replace(day=1), today),
            'this_year': (today.replace(month=1, day=1), today),
            'all': (False, False),
        }
        if self.date_filter == 'last_month':
            first = today.replace(day=1)
            end_prev = first - timedelta(days=1)
            self.date_from = end_prev.replace(day=1)
            self.date_to = end_prev
        elif self.date_filter == 'this_quarter':
            q = (today.month - 1) // 3
            self.date_from = today.replace(month=q * 3 + 1, day=1)
            self.date_to = today
        elif self.date_filter == 'last_year':
            self.date_from = today.replace(year=today.year - 1, month=1, day=1)
            self.date_to = today.replace(year=today.year - 1, month=12, day=31)
        elif self.date_filter in mapping:
            self.date_from, self.date_to = mapping[self.date_filter]

    def _secure_report_env(self):
        company = self.env.company
        ctx = dict(self.env.context, allowed_company_ids=[company.id], force_company=company.id)
        return self.env['res.users'].with_context(ctx).env

    def _get_report_data_instance(self):
        from ..reports.report_definitions import REPORT_REGISTRY
        report_class = REPORT_REGISTRY.get(self.report_type)
        if not report_class:
            raise UserError(_('Rapor tipi henüz uygulanmamış: %s') % self.report_type)
        secure_env = self._secure_report_env()
        return report_class(
            env=secure_env,
            date_from=self.date_from,
            date_to=self.date_to,
            project_id=self.project_id.id if self.project_id else None,
            partner_id=self.partner_id.id if self.partner_id else None,
            user_id=self.user_id.id if self.user_id else None,
        )

    def _build_preview_html(self):
        from ..reports.report_generator import ReportGenerator
        try:
            report_data = self._get_report_data_instance()
            generator = ReportGenerator(report_data)
            return generator.generate_html_fragment()
        except Exception as exc:
            _logger.warning('Report preview failed: %s', exc, exc_info=True)
            return (
                '<div style="padding:20px;color:#721c24;background:#f8d7da;border-radius:4px;">'
                f'<strong>Önizleme hatası:</strong> {exc}'
                '</div>'
            )

    def _store_html_share(self, content: bytes, filename: str):
        Share = self.env['propertio.report.share'].sudo()
        share = Share.create_from_html(
            name=filename.replace('.html', '') or 'Rapor',
            html_bytes_or_str=content,
            report_type=self.report_type,
            make_public=False,
        )
        self.write({
            'share_id': share.id,
            'share_url': share.public_url,
            'file_data': base64.b64encode(content),
            'file_name': filename,
            'state': 'done',
        })
        return share

    def action_refresh_preview(self, context=None):
        self.ensure_one()
        self.write({'html_preview': self._build_preview_html()})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_generate_report(self, context=None):
        self.ensure_one()
        from ..reports.report_generator import ReportGenerator

        report_data = self._get_report_data_instance()
        generator = ReportGenerator(report_data)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        slug = self.report_type.replace('_', '-')

        fmt = self.export_format or 'xlsx'
        if fmt == 'xlsx':
            content = generator.generate_xlsx()
            filename = f'{slug}_{timestamp}.xlsx'
        elif fmt == 'csv':
            content = generator.generate_csv()
            filename = f'{slug}_{timestamp}.csv'
        elif fmt == 'pdf':
            content = generator.generate_pdf()
            filename = f'{slug}_{timestamp}.pdf'
        else:
            content = generator.generate_html(include_print_button=True)
            filename = f'{slug}_{timestamp}.html'
            share = self._store_html_share(content, filename)
            return {
                'type': 'ir.actions.act_url',
                'url': share.view_url,
                'target': 'new',
            }

        self.write({
            'file_data': base64.b64encode(content),
            'file_name': filename,
            'state': 'done',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': (
                f'/web/content?model={self._name}&id={self.id}'
                f'&field=file_data&download=true&filename={filename}'
            ),
            'target': 'self',
        }

    def action_export_xlsx(self, context=None):
        self.ensure_one()
        self.export_format = 'xlsx'
        return self.action_generate_report()

    def action_export_csv(self, context=None):
        self.ensure_one()
        self.export_format = 'csv'
        return self.action_generate_report()

    def action_export_pdf(self, context=None):
        self.ensure_one()
        self.export_format = 'pdf'
        return self.action_generate_report()

    def action_export_html(self, context=None):
        """Open report as a real HTML page in a new tab."""
        self.ensure_one()
        self.export_format = 'html'
        return self.action_generate_report()

    def action_enable_public_link(self, context=None):
        """Make the latest HTML report publicly shareable (no login)."""
        self.ensure_one()
        from ..reports.report_generator import ReportGenerator

        if not self.share_id:
            report_data = self._get_report_data_instance()
            generator = ReportGenerator(report_data)
            content = generator.generate_html(include_print_button=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f'{self.report_type.replace("_", "-")}_{timestamp}.html'
            self._store_html_share(content, filename)

        self.share_id.action_enable_public()
        self.share_url = self.share_id.public_url
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Paylaşılabilir Bağlantı'),
                'message': _(
                    'Bağlantı herkese açıldı. Kopyalayıp paylaşabilirsiniz:\n%s'
                ) % self.share_id.public_url,
                'type': 'success',
                'sticky': True,
            },
        }

    def action_open_public_link(self, context=None):
        self.ensure_one()
        if not self.share_id:
            self.action_enable_public_link()
        if not self.share_id.is_public:
            self.share_id.action_enable_public()
            self.share_url = self.share_id.public_url
        return {
            'type': 'ir.actions.act_url',
            'url': self.share_id.public_url,
            'target': 'new',
        }

    def action_close_public_link(self, context=None):
        self.ensure_one()
        if not self.share_id:
            raise UserError(_('Önce bir rapor oluşturun.'))
        self.share_id.action_close_link()
        self.share_url = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bağlantı Kapatıldı'),
                'message': _('Herkese açık rapor bağlantısı kapatıldı. Artık erişilemez.'),
                'type': 'warning',
                'sticky': False,
            },
        }

    def action_download(self, context=None):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Lütfen önce raporu oluşturun.'))
        return {
            'type': 'ir.actions.act_url',
            'url': (
                f'/web/content?model={self._name}&id={self.id}'
                f'&field=file_data&download=true&filename={self.file_name}'
            ),
            'target': 'self',
        }
