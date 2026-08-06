# -*- coding: utf-8 -*-
import json

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError


class MarketingPost(models.Model):
    _name = 'tcrm.marketing.post'
    _description = 'Marketing Hub Gönderisi'
    _order = 'scheduled_for desc, create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Başlık', required=True, default='Gönderi')
    zernio_id = fields.Char(string='Zernio Gönderi ID', index=True, copy=False)
    content = fields.Text(string='İçerik')
    status = fields.Selection(
        [
            ('draft', 'Taslak'),
            ('scheduled', 'Zamanlanmış'),
            ('published', 'Yayında'),
            ('failed', 'Başarısız'),
            ('deleted', 'Silindi'),
            ('unknown', 'Bilinmiyor'),
        ],
        string='Durum',
        default='draft',
        tracking=True,
    )
    platform_labels = fields.Char(string='Platformlar', readonly=True)
    scheduled_for = fields.Datetime(string='Zamanlama')
    published_at = fields.Datetime(string='Yayın Tarihi')
    platform_post_url = fields.Char(string='Platform URL')
    media_urls = fields.Text(string='Medya URL’leri', help='Satır başına bir URL')
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda self: self.env.company,
    )
    account_ids = fields.Many2many(
        'tcrm.marketing.account',
        'tcrm_marketing_post_account_rel',
        'post_id',
        'account_id',
        string='Hesaplar',
    )
    last_sync_at = fields.Datetime(string='Son Senkron')
    error_message = fields.Text(string='Hata')
    raw_json = fields.Text(string='Ham JSON', groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        (
            'zernio_id_uniq',
            'unique(zernio_id)',
            'Bu Zernio gönderisi zaten kayıtlı.',
        ),
    ]

    @api.model
    def _map_status(self, value):
        if not value:
            return 'unknown'
        value = str(value).lower()
        mapping = {
            'draft': 'draft',
            'scheduled': 'scheduled',
            'publishing': 'scheduled',
            'published': 'published',
            'success': 'published',
            'failed': 'failed',
            'error': 'failed',
            'deleted': 'deleted',
            'cancelled': 'deleted',
        }
        return mapping.get(value, 'unknown')

    @api.model
    def _upsert_from_remote(self, item):
        zid = item.get('_id') or item.get('id')
        if not zid:
            return self.browse()
        content = item.get('content') or item.get('text') or ''
        platforms = item.get('platforms') or []
        plat_names = []
        account_zids = []
        urls = []
        for p in platforms:
            if isinstance(p, dict):
                plat_names.append(p.get('platform') or '')
                if p.get('accountId'):
                    account_zids.append(p['accountId'])
                if p.get('platformPostUrl'):
                    urls.append(p['platformPostUrl'])
            else:
                plat_names.append(str(p))
        accounts = self.env['tcrm.marketing.account'].search([
            ('zernio_id', 'in', account_zids),
        ]) if account_zids else self.env['tcrm.marketing.account']
        # Extract media URLs from payload
        raw_media = (
            item.get('media')
            or item.get('mediaUrls')
            or item.get('images')
            or item.get('media_urls')
            or []
        )
        if isinstance(raw_media, str):
            raw_media = [raw_media]
        m_list = []
        for m in raw_media:
            if isinstance(m, dict):
                u = m.get('url') or m.get('src') or m.get('imageUrl') or m.get('fullUrl')
                if u:
                    m_list.append(str(u))
            elif m:
                m_list.append(str(m))
        if item.get('thumbnailUrl') and item.get('thumbnailUrl') not in m_list:
            m_list.append(str(item['thumbnailUrl']))
        if item.get('videoUrl') and item.get('videoUrl') not in m_list:
            m_list.append(str(item['videoUrl']))

        vals = {
            'name': (content[:60] + '…') if len(content) > 60 else (content or f'Gönderi {zid[-6:]}'),
            'zernio_id': zid,
            'content': content,
            'status': self._map_status(item.get('status')),
            'platform_labels': ', '.join(x for x in plat_names if x) or False,
            'scheduled_for': fields.Datetime.to_datetime(scheduled) if scheduled else False,
            'published_at': fields.Datetime.to_datetime(published) if published else False,
            'platform_post_url': urls[0] if urls else (item.get('platformPostUrl') or False),
            'media_urls': '\n'.join(m_list) if m_list else False,
            'company_id': self.env.company.id,
            'account_ids': [(6, 0, accounts.ids)],
            'last_sync_at': fields.Datetime.now(),
            'error_message': item.get('error') or item.get('errorMessage') or False,
            'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:8000],
        }
        existing = self.sudo().search([('zernio_id', '=', zid)], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.sudo().create(vals)

    @api.model
    def action_sync_from_zernio(self):
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            data = client.list_posts(page=1, limit=50)
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        posts = data.get('posts') or []
        # Prefer IG/FB only
        count = 0
        for item in posts:
            platforms = item.get('platforms') or []
            plat_set = {
                (p.get('platform') if isinstance(p, dict) else str(p)).lower()
                for p in platforms
            }
            if plat_set and not (plat_set & {'instagram', 'facebook'}):
                continue
            self._upsert_from_remote(item)
            count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('%s gönderi senkronize edildi.') % count,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_retry(self):
        self.ensure_one()
        if not self.zernio_id:
            raise UserError(_('Bu gönderinin Zernio ID’si yok.'))
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            data = client.retry_post(self.zernio_id)
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        post = data.get('post') if isinstance(data, dict) else None
        self._upsert_from_remote(post or data or {'id': self.zernio_id})
        return True

    def action_open_platform_url(self):
        self.ensure_one()
        if not self.platform_post_url:
            raise UserError(_('Platform URL’si yok.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.platform_post_url,
            'target': 'new',
        }
