# -*- coding: utf-8 -*-
import secrets

from tcrm import api, fields, models
from tcrm.exceptions import UserError


class PropertioReportShare(models.Model):
    """Stored HTML report with optional public share token."""

    _name = 'propertio.report.share'
    _description = 'Propertio Paylaşılabilir Rapor'
    _order = 'create_date desc'

    name = fields.Char(string='Rapor Adı', required=True)
    access_token = fields.Char(string='Erişim Anahtarı', index=True, copy=False, readonly=True)
    html_content = fields.Text(string='HTML İçerik', required=True)
    report_type = fields.Char(string='Rapor Tipi')
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Oluşturan',
        default=lambda self: self.env.user,
        readonly=True,
    )
    is_public = fields.Boolean(
        string='Herkese Açık',
        default=False,
        help='Açıkken giriş yapmadan bağlantı ile görüntülenebilir.',
    )
    active = fields.Boolean(string='Aktif', default=True)
    public_url = fields.Char(string='Herkese Açık Bağlantı', compute='_compute_urls')
    view_url = fields.Char(string='Görüntüleme Bağlantısı', compute='_compute_urls')

    _sql_constraints = [
        ('access_token_uniq', 'unique(access_token)', 'Erişim anahtarı benzersiz olmalıdır.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def _compute_urls(self):
        base = (
            self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            or 'http://localhost:8069'
        ).rstrip('/').replace('odoo', 'tcrm')
        for rec in self:
            rec.view_url = f'{base}/propertio/report/view/{rec.id}?token={rec.access_token}'
            rec.public_url = f'{base}/propertio/r/{rec.access_token}'

    def action_enable_public(self):
        self.write({'is_public': True, 'active': True})
        return True

    def action_revoke_public(self):
        self.write({'is_public': False})
        return True

    def action_close_link(self):
        """Fully close the share (public + private token invalid for public route)."""
        self.write({'is_public': False, 'active': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Propertio',
                'message': 'Rapor bağlantısı kapatıldı.',
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def create_from_html(self, *, name, html_bytes_or_str, report_type=None, make_public=False):
        if isinstance(html_bytes_or_str, bytes):
            html = html_bytes_or_str.decode('utf-8')
        else:
            html = html_bytes_or_str or ''
        if not html.strip():
            raise UserError('Rapor HTML içeriği boş.')
        return self.create({
            'name': name or 'Rapor',
            'html_content': html,
            'report_type': report_type or False,
            'is_public': bool(make_public),
            'active': True,
            'company_id': self.env.company.id,
        })
