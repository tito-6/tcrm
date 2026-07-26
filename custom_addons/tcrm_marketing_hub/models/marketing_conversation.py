# -*- coding: utf-8 -*-
import json

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import META_PLATFORMS, ZernioError


class MarketingConversation(models.Model):
    _name = 'tcrm.marketing.conversation'
    _description = 'Marketing Hub Gelen Kutusu'
    _order = 'last_message_at desc, id desc'
    # No mail.thread: DM messages use inbox_message_ids (mail.message conflict).

    name = fields.Char(string='Katılımcı', required=True)
    zernio_id = fields.Char(string='Konuşma ID', required=True, index=True, copy=False)
    platform = fields.Selection(
        [('instagram', 'Instagram'), ('facebook', 'Facebook'), ('other', 'Diğer')],
        string='Platform',
        required=True,
        index=True,
    )
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Hesap',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='account_id.company_id', store=True, readonly=True)
    participant_id = fields.Char(string='Katılımcı ID')
    participant_username = fields.Char(string='Kullanıcı Adı')
    participant_picture = fields.Char(string='Profil Fotoğrafı')
    status = fields.Char(string='Durum')
    last_message = fields.Text(string='Son Mesaj')
    last_message_at = fields.Datetime(string='Son Mesaj Tarihi')
    unread = fields.Boolean(string='Okunmadı', default=False)
    # Must NOT be named message_ids — that field belongs to mail.thread (mail.message).
    inbox_message_ids = fields.One2many(
        'tcrm.marketing.message',
        'conversation_id',
        string='DM Mesajları',
    )
    message_count = fields.Integer(compute='_compute_message_count')
    last_sync_at = fields.Datetime(string='Son Senkron')
    raw_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        ('zernio_account_uniq', 'unique(zernio_id, account_id)', 'Bu konuşma zaten kayıtlı.'),
    ]

    @api.depends('inbox_message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.inbox_message_ids)

    @api.model
    def action_sync_from_zernio(self):
        Profile = self.env['tcrm.marketing.profile']
        try:
            client = Profile._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        Account = self.env['tcrm.marketing.account']
        synced = 0
        for platform in META_PLATFORMS:
            cursor = None
            for _page in range(5):
                data = client.list_conversations(platform=platform, limit=50, cursor=cursor)
                rows = data.get('data') or data.get('conversations') or []
                for item in rows:
                    zid = item.get('id') or item.get('_id')
                    acc_zid = item.get('accountId')
                    if not zid or not acc_zid:
                        continue
                    account = Account.search([('zernio_id', '=', acc_zid)], limit=1)
                    if not account:
                        continue
                    vals = {
                        'name': item.get('participantName') or item.get('participantUsername') or zid,
                        'zernio_id': zid,
                        'platform': platform if platform in ('instagram', 'facebook') else 'other',
                        'account_id': account.id,
                        'participant_id': item.get('participantId') or False,
                        'participant_username': item.get('participantUsername') or False,
                        'participant_picture': item.get('participantPicture') or False,
                        'status': item.get('status') or False,
                        'last_message': item.get('lastMessage') or False,
                        'last_message_at': fields.Datetime.to_datetime(item.get('lastMessageAt'))
                        if item.get('lastMessageAt') else False,
                        'last_sync_at': fields.Datetime.now(),
                        'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:8000],
                    }
                    existing = self.sudo().search([
                        ('zernio_id', '=', zid),
                        ('account_id', '=', account.id),
                    ], limit=1)
                    if existing:
                        existing.write(vals)
                    else:
                        self.sudo().create(vals)
                    synced += 1
                pagination = data.get('pagination') or {}
                cursor = pagination.get('nextCursor') or pagination.get('cursor')
                if not pagination.get('hasMore') or not cursor:
                    break

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('%s konuşma senkronize edildi.') % synced,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_load_messages(self):
        self.ensure_one()
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            messages = client.list_messages(
                self.zernio_id,
                account_id=self.account_id.zernio_id,
                limit=100,
            )
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        Message = self.env['tcrm.marketing.message'].sudo()
        for item in messages:
            mid = item.get('id') or item.get('_id')
            if not mid:
                continue
            vals = {
                'conversation_id': self.id,
                'zernio_id': mid,
                'body': item.get('message') or item.get('text') or '',
                'direction': 'outgoing' if item.get('direction') == 'outgoing' else 'incoming',
                'sender_name': item.get('senderName') or False,
                'sender_id': item.get('senderId') or False,
                'sent_at': fields.Datetime.to_datetime(item.get('createdAt'))
                if item.get('createdAt') else False,
            }
            existing = Message.search([
                ('zernio_id', '=', mid),
                ('conversation_id', '=', self.id),
            ], limit=1)
            if existing:
                existing.write(vals)
            else:
                Message.create(vals)
        self.last_sync_at = fields.Datetime.now()
        return True

    def action_open_reply_wizard(self):
        self.ensure_one()
        self.action_load_messages()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Yanıtla'),
            'res_model': 'tcrm.marketing.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_conversation_id': self.id,
            },
        }


class MarketingMessage(models.Model):
    _name = 'tcrm.marketing.message'
    _description = 'Marketing Hub Mesajı'
    _order = 'sent_at asc, id asc'

    conversation_id = fields.Many2one(
        'tcrm.marketing.conversation',
        required=True,
        ondelete='cascade',
        index=True,
    )
    zernio_id = fields.Char(string='Mesaj ID', index=True)
    body = fields.Text(string='Mesaj')
    direction = fields.Selection(
        [('incoming', 'Gelen'), ('outgoing', 'Giden')],
        string='Yön',
        default='incoming',
    )
    sender_name = fields.Char(string='Gönderen')
    sender_id = fields.Char(string='Gönderen ID')
    sent_at = fields.Datetime(string='Tarih')
