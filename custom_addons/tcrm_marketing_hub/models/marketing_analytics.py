# -*- coding: utf-8 -*-
import json

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError


class MarketingAnalyticsSnapshot(models.Model):
    _name = 'tcrm.marketing.analytics'
    _description = 'Marketing Hub Analitik Özeti'
    _order = 'sync_at desc'

    name = fields.Char(string='Özet', required=True, default='Analitik Özeti')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    sync_at = fields.Datetime(string='Senkron', default=fields.Datetime.now)
    total_posts = fields.Integer(string='Toplam Gönderi')
    published_posts = fields.Integer(string='Yayındaki')
    scheduled_posts = fields.Integer(string='Zamanlanmış')
    last_remote_sync = fields.Char(string='Son Uzak Senkron')
    overview_json = fields.Text(string='Özet JSON')
    accounts_json = fields.Text(string='Hesap Metrikleri')
    posts_json = fields.Text(string='Gönderi Metrikleri')

    @api.model
    def action_sync_from_zernio(self):
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            data = client.get_analytics(limit=25, sort_by='engagement')
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        overview = data.get('overview') or {}
        rec = self.sudo().create({
            'name': _('Analitik — %s') % fields.Datetime.now(),
            'company_id': self.env.company.id,
            'sync_at': fields.Datetime.now(),
            'total_posts': int(overview.get('totalPosts') or 0),
            'published_posts': int(overview.get('publishedPosts') or 0),
            'scheduled_posts': int(overview.get('scheduledPosts') or 0),
            'last_remote_sync': overview.get('lastSync') or False,
            'overview_json': json.dumps(overview, ensure_ascii=False, default=str)[:8000],
            'accounts_json': json.dumps(data.get('accounts') or [], ensure_ascii=False, default=str)[:12000],
            'posts_json': json.dumps(data.get('posts') or [], ensure_ascii=False, default=str)[:12000],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Analitik'),
            'res_model': 'tcrm.marketing.analytics',
            'res_id': rec.id,
            'view_mode': 'form',
            'target': 'current',
        }
