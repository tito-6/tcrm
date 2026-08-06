# -*- coding: utf-8 -*-
from tcrm import fields, models, _


class TcrmOfferCatalogue(models.Model):
    _name = 'tcrm.offer.catalogue'
    _description = 'Teklif Hizmet Kataloğu'
    _order = 'sequence, name'

    name = fields.Char(string='Ad', required=True)
    code = fields.Selection(
        [
            ('social_media', 'Sosyal Medya Kataloğu'),
            ('digital_ads', 'Dijital Reklam Kataloğu'),
            ('software', 'Yazılım / Web Kataloğu'),
            ('ai_automation', 'AI Otomasyon Kataloğu'),
        ],
        string='Tür',
        required=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Şirket')
    summary = fields.Html(string='Özet', sanitize=True)
    item_ids = fields.One2many('tcrm.offer.catalogue.item', 'catalogue_id', string='Kalemler')

    def name_get(self):
        result = []
        labels = dict(self._fields['code'].selection)
        for rec in self:
            result.append((rec.id, '%s — %s' % (labels.get(rec.code, rec.code), rec.name)))
        return result


class TcrmOfferCatalogueItem(models.Model):
    _name = 'tcrm.offer.catalogue.item'
    _description = 'Katalog Kalemi'
    _order = 'sort_order, id'

    catalogue_id = fields.Many2one(
        'tcrm.offer.catalogue', required=True, ondelete='cascade', index=True,
    )
    name = fields.Char(required=True)
    description = fields.Html(sanitize=True)
    price_from = fields.Float(string='Başlangıç Fiyatı (KDV hariç)', digits=(16, 2))
    price_to = fields.Float(string='Üst Fiyat (KDV hariç)', digits=(16, 2))
    price_note = fields.Char(
        string='Fiyat Notu',
        help='Örn. sektöre, teknoloji yığınına ve tahmini üretim saatine göre değişir.',
    )
    billing_period = fields.Selection(
        [
            ('one_time', 'Tek Seferlik'),
            ('monthly', 'Aylık'),
            ('per_session', 'Seans Başı'),
            ('from', 'Başlayan fiyatlar'),
        ],
        default='from',
    )
    sort_order = fields.Integer(default=10)
    highlight = fields.Boolean(string='Öne Çıkan')
