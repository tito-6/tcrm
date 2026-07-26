# -*- coding: utf-8 -*-
from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError


class CreateAdWizard(models.TransientModel):
    _name = 'tcrm.marketing.create.ad.wizard'
    _description = 'Meta Reklam Oluştur'

    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Sosyal Hesap',
        required=True,
        domain="[('platform', 'in', ('facebook', 'instagram')), ('active', '=', True)]",
    )
    ad_account_id = fields.Many2one(
        'tcrm.marketing.ad.account',
        string='Meta Reklam Hesabı',
        required=True,
        domain="[('account_id', '=', account_id), ('selectable', '=', True)]",
    )
    name = fields.Char(string='Kampanya Adı', required=True)
    goal = fields.Selection(
        [
            ('traffic', 'Trafik'),
            ('engagement', 'Etkileşim'),
            ('awareness', 'Farkındalık'),
            ('video_views', 'Video İzlenme'),
            ('lead_generation', 'Potansiyel Müşteri'),
            ('conversions', 'Dönüşüm'),
            ('catalog_sales', 'Katalog Satış'),
        ],
        string='Hedef',
        default='traffic',
        required=True,
    )
    budget_amount = fields.Float(string='Günlük Bütçe', required=True, default=100.0)
    budget_type = fields.Selection(
        [('daily', 'Günlük'), ('lifetime', 'Toplam')],
        string='Bütçe Tipi',
        default='daily',
        required=True,
    )
    headline = fields.Char(string='Başlık', required=True)
    body = fields.Text(string='Metin', required=True)
    image_url = fields.Char(string='Görsel URL', required=True)
    link_url = fields.Char(string='Hedef URL', required=True)
    call_to_action = fields.Selection(
        [
            ('LEARN_MORE', 'Daha Fazla Bilgi'),
            ('SHOP_NOW', 'Alışveriş Yap'),
            ('SIGN_UP', 'Kayıt Ol'),
            ('CONTACT_US', 'Bize Ulaşın'),
            ('SEND_MESSAGE', 'Mesaj Gönder'),
            ('WHATSAPP_MESSAGE', 'WhatsApp'),
            ('APPLY_NOW', 'Başvur'),
            ('BOOK_TRAVEL', 'Rezervasyon'),
        ],
        string='Harekete Geçir',
        default='LEARN_MORE',
        required=True,
    )
    countries = fields.Char(
        string='Ülkeler (ISO)',
        default='TR',
        help='Virgülle ayırın, örn. TR,DE',
        required=True,
    )
    age_min = fields.Integer(string='Min Yaş', default=25)
    age_max = fields.Integer(string='Max Yaş', default=55)
    status = fields.Selection(
        [('PAUSED', 'Duraklatılmış oluştur'), ('ACTIVE', 'Aktif oluştur')],
        string='Başlangıç Durumu',
        default='PAUSED',
        required=True,
    )

    @api.onchange('account_id')
    def _onchange_account_id(self):
        self.ad_account_id = False
        if self.account_id:
            ads = self.env['tcrm.marketing.ad.account'].search([
                ('account_id', '=', self.account_id.id),
                ('selectable', '=', True),
            ], limit=1)
            self.ad_account_id = ads

    def action_create(self):
        self.ensure_one()
        countries = [c.strip().upper() for c in (self.countries or '').split(',') if c.strip()]
        if not countries:
            raise UserError(_('En az bir ülke kodu girin (örn. TR).'))
        body = {
            'accountId': self.account_id.zernio_id,
            'adAccountId': self.ad_account_id.meta_act_id,
            'name': self.name,
            'goal': self.goal,
            'budgetAmount': self.budget_amount,
            'budgetType': self.budget_type,
            'headline': self.headline,
            'body': self.body,
            'imageUrl': self.image_url,
            'callToAction': self.call_to_action,
            'linkUrl': self.link_url,
            'countries': countries,
            'ageMin': self.age_min,
            'ageMax': self.age_max,
            'status': self.status,
        }
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            client.create_standalone_ad(body)
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        self.env['tcrm.marketing.campaign'].action_sync_from_zernio()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('Meta reklam kampanyası oluşturuldu.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Kampanyalar'),
                    'res_model': 'tcrm.marketing.campaign',
                    'view_mode': 'list,form',
                },
            },
        }


class BoostPostWizard(models.TransientModel):
    _name = 'tcrm.marketing.boost.wizard'
    _description = 'Gönderiyi Öne Çıkar (Boost)'

    post_id = fields.Many2one('tcrm.marketing.post', string='Gönderi')
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Sosyal Hesap',
        required=True,
        domain="[('platform', 'in', ('facebook', 'instagram'))]",
    )
    ad_account_id = fields.Many2one(
        'tcrm.marketing.ad.account',
        string='Meta Reklam Hesabı',
        required=True,
        domain="[('account_id', '=', account_id)]",
    )
    platform_post_id = fields.Char(
        string='Platform Gönderi ID',
        help='Facebook/Instagram post ID (organic).',
        required=True,
    )
    budget_amount = fields.Float(string='Günlük Bütçe', default=50.0, required=True)
    duration_days = fields.Integer(string='Süre (gün)', default=3, required=True)
    countries = fields.Char(string='Ülkeler', default='TR', required=True)

    @api.onchange('post_id')
    def _onchange_post(self):
        if self.post_id and self.post_id.account_ids:
            self.account_id = self.post_id.account_ids[:1]
            # platformPostUrl may not equal platform post id; leave for user if unknown

    def action_boost(self):
        self.ensure_one()
        countries = [c.strip().upper() for c in (self.countries or '').split(',') if c.strip()]
        body = {
            'accountId': self.account_id.zernio_id,
            'adAccountId': self.ad_account_id.meta_act_id,
            'platformPostId': self.platform_post_id,
            'budget': {'amount': self.budget_amount, 'type': 'daily'},
            'schedule': {'durationDays': self.duration_days},
            'targeting': {'countries': countries},
        }
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            client.boost_post(body)
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        self.env['tcrm.marketing.campaign'].action_sync_from_zernio()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('Gönderi öne çıkarma (boost) isteği gönderildi.'),
                'type': 'success',
                'sticky': False,
            },
        }
