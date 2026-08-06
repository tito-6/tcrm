# -*- coding: utf-8 -*-
from tcrm import fields, models


class TcrmOfferEvent(models.Model):
    _name = 'tcrm.offer.event'
    _description = 'Teklif Audit Event'
    _order = 'create_date desc, id desc'

    offer_id = fields.Many2one(
        'tcrm.offer', string='Teklif', required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        related='offer_id.company_id', store=True, readonly=True,
    )
    event_type = fields.Selection(
        [
            ('created', 'Oluşturuldu'),
            ('updated', 'Güncellendi'),
            ('published', 'Yayınlandı'),
            ('viewed', 'Görüntülendi'),
            ('passcode_failed', 'Passcode Başarısız'),
            ('passcode_reset', 'Passcode Yenilendi'),
            ('approved', 'Onaylandı'),
            ('paused', 'Duraklatıldı'),
            ('reopened', 'Yeniden Açıldı'),
            ('revoked', 'İptal Edildi'),
            ('closed', 'Kapatıldı'),
            ('expired', 'Süresi Doldu'),
            ('exported', 'Dışa Aktarıldı'),
            ('duplicated', 'Çoğaltıldı'),
            ('discount_applied', 'İndirim Uygulandı'),
        ],
        string='Olay',
        required=True,
        index=True,
    )
    actor_type = fields.Selection(
        [
            ('admin', 'Admin'),
            ('public', 'Public'),
            ('system', 'Sistem'),
        ],
        string='Aktör Tipi',
        default='admin',
        required=True,
    )
    actor_user_id = fields.Many2one('res.users', string='Kullanıcı')
    summary = fields.Char(string='Özet')
    metadata_json = fields.Text(string='Metadata (güvenli)')
