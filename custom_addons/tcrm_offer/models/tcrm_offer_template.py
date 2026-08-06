# -*- coding: utf-8 -*-
from tcrm import fields, models, _


class TcrmOfferTemplate(models.Model):
    _name = 'tcrm.offer.template'
    _description = 'Teklif Şablonu'
    _order = 'name'

    name = fields.Char(string='Ad', required=True)
    code = fields.Char(string='Kod', index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Şirket')
    title = fields.Char(string='Varsayılan Başlık')
    summary = fields.Html(string='Yönetici Özeti', sanitize=True)
    scope_html = fields.Html(string='Kapsam', sanitize=True)
    terms_html = fields.Html(string='Ticari Şartlar', sanitize=True)
    validity_days = fields.Integer(string='Geçerlilik (gün)', default=15)
    ad_budget_default = fields.Float(string='Varsayılan Reklam Bütçesi', default=50000.0)
    ad_budget_min = fields.Float(default=0.0)
    ad_budget_max = fields.Float(default=500000.0)
    item_ids = fields.One2many('tcrm.offer.template.item', 'template_id', string='Kalemler')
    partner_label = fields.Char(string='Örnek Müşteri Etiketi')
    catalogue_ids = fields.Many2many(
        'tcrm.offer.catalogue',
        'tcrm_offer_template_catalogue_rel',
        'template_id',
        'catalogue_id',
        string='Varsayılan Kataloglar',
    )
    contract_intro_html = fields.Html(string='Sözleşme Giriş', sanitize=True)
    provider_legal_name = fields.Char(
        default='AKOD Yazılım Bilişim ve Dijital Pazarlama Ticaret Limited Şirketi',
    )
    provider_short_name = fields.Char(default='AKOD')

    def action_create_offer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Şablondan Teklif'),
            'res_model': 'tcrm.offer.from.template',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_template_id': self.id},
        }


class TcrmOfferTemplateItem(models.Model):
    _name = 'tcrm.offer.template.item'
    _description = 'Teklif Şablon Kalemi'
    _order = 'sort_order, id'

    template_id = fields.Many2one(
        'tcrm.offer.template', required=True, ondelete='cascade',
    )
    name = fields.Char(required=True)
    description = fields.Html(sanitize=True)
    category = fields.Char()
    pricing_type = fields.Selection(
        [
            ('fixed', 'Sabit'),
            ('percentage', 'Yüzde'),
            ('quantity', 'Adet'),
            ('custom', 'Özel'),
            ('meta_budget', 'Meta Bütçe Yönetimi'),
        ],
        required=True,
        default='fixed',
    )
    unit_price = fields.Float(digits=(16, 2), default=0.0)
    percentage_rate = fields.Float(digits=(16, 4), default=0.0)
    quantity = fields.Integer(default=1)
    custom_fee = fields.Float(digits=(16, 2))
    billing_period = fields.Selection(
        [
            ('one_time', 'Tek Seferlik'),
            ('monthly', 'Aylık'),
            ('per_session', 'Seans Başı'),
        ],
        required=True,
        default='one_time',
    )
    selection_type = fields.Selection(
        [('required', 'Zorunlu'), ('optional', 'Opsiyonel')],
        required=True,
        default='optional',
    )
    default_selected = fields.Boolean(default=False)
    taxable = fields.Boolean(default=True)
    sort_order = fields.Integer(default=10)
    includes_html = fields.Html(sanitize=True)
    excludes_html = fields.Html(sanitize=True)
    exclusive_group = fields.Char()
    code = fields.Char()
    package_group = fields.Selection(
        [
            ('basic_required', 'Zorunlu Temel Paket'),
            ('optional', 'Opsiyonel'),
            ('web', 'Web / Yazılım'),
            ('production', 'Prodüksiyon'),
            ('other', 'Diğer'),
        ],
        default='optional',
    )
    client_choice_label = fields.Char()
    client_choice_options = fields.Char()
