# -*- coding: utf-8 -*-
from tcrm import fields, models


class TcrmOfferAccessSession(models.Model):
    _name = 'tcrm.offer.access.session'
    _description = 'Teklif Public Erişim Oturumu'
    _order = 'authenticated_at desc'

    offer_id = fields.Many2one(
        'tcrm.offer', string='Teklif', required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        related='offer_id.company_id', store=True, readonly=True,
    )
    session_token_hash = fields.Char(string='Session Token Hash', required=True, index=True)
    authenticated_at = fields.Datetime(string='Doğrulama', required=True)
    expires_at = fields.Datetime(string='Bitiş', required=True)
    last_seen_at = fields.Datetime(string='Son Görülme')
    ip_masked = fields.Char(string='IP (maskeli)')
    user_agent = fields.Char(string='User-Agent')
    revoked = fields.Boolean(string='İptal', default=False)

    def action_revoke(self):
        self.write({'revoked': True})
