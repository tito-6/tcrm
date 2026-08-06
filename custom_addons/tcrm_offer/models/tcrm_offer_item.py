# -*- coding: utf-8 -*-
from tcrm import fields, models


class TcrmOfferItem(models.Model):
    _name = 'tcrm.offer.item'
    _description = 'Teklif Kalemi'
    _order = 'sort_order, id'

    offer_id = fields.Many2one(
        'tcrm.offer', string='Teklif', required=True, ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        related='offer_id.company_id', store=True, readonly=True,
    )
    name = fields.Char(string='Ad', required=True)
    description = fields.Html(string='Açıklama', sanitize=True)
    category = fields.Char(string='Kategori')
    pricing_type = fields.Selection(
        [
            ('fixed', 'Sabit'),
            ('percentage', 'Yüzde'),
            ('quantity', 'Adet'),
            ('custom', 'Özel'),
            ('meta_budget', 'Meta Bütçe Yönetimi'),
        ],
        string='Fiyat Tipi',
        required=True,
        default='fixed',
    )
    unit_price = fields.Float(string='Birim Fiyat (KDV hariç)', digits=(16, 2), default=0.0)
    percentage_rate = fields.Float(string='Yüzde Oranı', digits=(16, 4), default=0.0)
    quantity = fields.Integer(string='Adet', default=1)
    custom_fee = fields.Float(
        string='Özel Yönetim Ücreti',
        digits=(16, 2),
        help='Meta bütçe > 500.000 TL için zorunlu özel ücret.',
    )
    billing_period = fields.Selection(
        [
            ('one_time', 'Tek Seferlik'),
            ('monthly', 'Aylık'),
            ('per_session', 'Seans Başı'),
        ],
        string='Faturalama',
        required=True,
        default='one_time',
    )
    selection_type = fields.Selection(
        [
            ('required', 'Zorunlu'),
            ('optional', 'Opsiyonel'),
        ],
        string='Seçim Tipi',
        required=True,
        default='optional',
    )
    default_selected = fields.Boolean(string='Varsayılan Seçili', default=False)
    taxable = fields.Boolean(string='KDV Uygulanır', default=True)
    sort_order = fields.Integer(string='Sıra', default=10)
    active = fields.Boolean(default=True)
    includes_html = fields.Html(string='Dahil Olanlar', sanitize=True)
    excludes_html = fields.Html(string='Hariç Olanlar', sanitize=True)
    admin_note = fields.Text(string='Admin İç Notu')
    exclusive_group = fields.Char(
        string='Dışlayıcı Grup',
        help='Aynı gruptaki kalemlerden yalnızca biri seçilebilir (ör. social_media).',
    )
    code = fields.Char(string='Kod', help='Şablon / entegrasyon kodu')
    package_group = fields.Selection(
        [
            ('basic_required', 'Zorunlu Temel Paket'),
            ('optional', 'Opsiyonel'),
            ('web', 'Web / Yazılım'),
            ('production', 'Prodüksiyon'),
            ('other', 'Diğer'),
        ],
        string='Paket Grubu',
        default='optional',
    )
    client_choice_label = fields.Char(
        string='Müşteri Seçim Etiketi',
        help='Örn. Ek platform seçimi',
    )
    client_choice_options = fields.Char(
        string='Seçenekler (virgülle)',
        help='Örn. TikTok, LinkedIn, YouTube',
    )

    def _as_pricing_dict(self):
        self.ensure_one()
        from ..services.pricing import to_kurus
        return {
            'id': self.id,
            'name': self.name,
            'pricing_type': self.pricing_type,
            'unit_price_kurus': to_kurus(self.unit_price or 0),
            'percentage_rate': self.percentage_rate or 0,
            'quantity': self.quantity or 1,
            'billing_period': self.billing_period,
            'required': self.selection_type == 'required',
            'taxable': self.taxable,
            'exclusive_group': self.exclusive_group or '',
            'custom_fee_kurus': to_kurus(self.custom_fee) if self.custom_fee else None,
            'code': self.code or '',
        }
