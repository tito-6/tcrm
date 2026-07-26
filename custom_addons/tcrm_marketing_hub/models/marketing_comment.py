# -*- coding: utf-8 -*-
import json

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import META_PLATFORMS, ZernioError


class MarketingComment(models.Model):
    _name = 'tcrm.marketing.comment'
    _description = 'Marketing Hub Yorum'
    _order = 'commented_at desc, id desc'

    name = fields.Char(string='Özet', required=True)
    zernio_id = fields.Char(string='Yorum/Post ID', required=True, index=True, copy=False)
    platform = fields.Selection(
        [('instagram', 'Instagram'), ('facebook', 'Facebook'), ('other', 'Diğer')],
        string='Platform',
        required=True,
    )
    account_id = fields.Many2one('tcrm.marketing.account', string='Hesap', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='account_id.company_id', store=True, readonly=True)
    content = fields.Text(string='İçerik')
    author_name = fields.Char(string='Yazar')
    post_id_remote = fields.Char(string='Gönderi ID')
    commented_at = fields.Datetime(string='Tarih')
    last_sync_at = fields.Datetime(string='Son Senkron')
    raw_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        ('zernio_id_uniq', 'unique(zernio_id)', 'Bu yorum zaten kayıtlı.'),
    ]

    @api.model
    def action_sync_from_zernio(self):
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        synced = 0
        for platform in META_PLATFORMS:
            rows = client.list_comments(platform=platform, limit=50)
            for item in rows:
                zid = item.get('id') or item.get('_id')
                if not zid:
                    continue
                acc = False
                if item.get('accountId'):
                    acc = self.env['tcrm.marketing.account'].search(
                        [('zernio_id', '=', item['accountId'])], limit=1
                    )
                content = item.get('content') or item.get('message') or item.get('text') or ''
                vals = {
                    'name': (content[:80] + '…') if len(content) > 80 else (content or zid),
                    'zernio_id': zid,
                    'platform': platform if platform in ('instagram', 'facebook') else 'other',
                    'account_id': acc.id if acc else False,
                    'content': content,
                    'author_name': item.get('authorName') or item.get('username') or False,
                    'post_id_remote': item.get('postId') or item.get('platformPostId') or zid,
                    'commented_at': fields.Datetime.to_datetime(
                        item.get('createdAt') or item.get('timestamp')
                    ) if (item.get('createdAt') or item.get('timestamp')) else False,
                    'last_sync_at': fields.Datetime.now(),
                    'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:8000],
                }
                existing = self.sudo().search([('zernio_id', '=', zid)], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    self.sudo().create(vals)
                synced += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('%s yorum senkronize edildi.') % synced,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_reply(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Yoruma Yanıtla'),
            'res_model': 'tcrm.marketing.comment.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_comment_id': self.id},
        }
