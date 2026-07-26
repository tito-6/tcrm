# -*- coding: utf-8 -*-
from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError


class ComposePostWizard(models.TransientModel):
    _name = 'tcrm.marketing.compose.wizard'
    _description = 'Marketing Hub Gönderi Oluştur'

    content = fields.Text(string='İçerik', required=True)
    account_ids = fields.Many2many(
        'tcrm.marketing.account',
        string='Hesaplar',
        domain="[('platform', 'in', ('instagram', 'facebook')), ('status', '=', 'connected'), ('active', '=', True)]",
        required=True,
    )
    media_urls = fields.Text(
        string='Medya URL’leri',
        help='Instagram için en az bir görsel/video URL’si önerilir. Satır başına bir URL.',
    )
    publish_mode = fields.Selection(
        [
            ('now', 'Hemen Yayınla'),
            ('schedule', 'Zamanla'),
            ('draft', 'Taslak Kaydet'),
        ],
        string='Yayın Modu',
        default='now',
        required=True,
    )
    scheduled_for = fields.Datetime(string='Zamanlama')
    timezone = fields.Char(
        string='Saat Dilimi',
        default='Europe/Istanbul',
        help='Zernio scheduledFor ile birlikte kullanılır (örn. Europe/Istanbul).',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        accounts = self.env['tcrm.marketing.account'].search([
            ('platform', 'in', ('instagram', 'facebook')),
            ('status', '=', 'connected'),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ])
        if accounts and 'account_ids' in fields_list:
            res['account_ids'] = [(6, 0, accounts.ids)]
        return res

    def action_submit(self):
        self.ensure_one()
        if not self.account_ids:
            raise UserError(_('En az bir Instagram veya Facebook hesabı seçin.'))
        if self.publish_mode == 'schedule' and not self.scheduled_for:
            raise UserError(_('Zamanlama için tarih/saat girin.'))

        media = [
            u.strip()
            for u in (self.media_urls or '').splitlines()
            if u.strip()
        ]
        platforms = [
            {'platform': acc.platform, 'accountId': acc.zernio_id}
            for acc in self.account_ids
        ]
        body = {
            'content': self.content,
            'platforms': platforms,
            'timezone': self.timezone or 'Europe/Istanbul',
        }
        if media:
            body['mediaItems'] = [{'url': url, 'type': 'image'} for url in media]
            body['mediaUrls'] = media

        if self.publish_mode == 'now':
            body['publishNow'] = True
        elif self.publish_mode == 'schedule':
            # Zernio interprets scheduledFor in the given timezone (no Z suffix)
            body['scheduledFor'] = fields.Datetime.to_string(self.scheduled_for).replace(' ', 'T')
        else:
            body['isDraft'] = True

        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            remote = client.create_post(body)
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        post = self.env['tcrm.marketing.post']._upsert_from_remote(remote)
        if media and post:
            post.media_urls = '\n'.join(media)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Gönderi'),
            'res_model': 'tcrm.marketing.post',
            'res_id': post.id,
            'view_mode': 'form',
            'target': 'current',
        }
