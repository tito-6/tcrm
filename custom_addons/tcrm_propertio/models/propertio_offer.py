# -*- coding: utf-8 -*-
from tcrm import models, fields, api, _
from tcrm.exceptions import UserError


class PropertioOffer(models.Model):
    _name = 'propertio.offer'
    _description = 'Property Offer / Option'
    _order = 'date_offer desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Referans', required=True, copy=False, readonly=True, default='New')
    unit_id = fields.Many2one(
        'propertio.unit', string='Birim', required=True, ondelete='cascade',
        domain="[('state', 'in', ('available', 'option'))]")
    company_id = fields.Many2one(
        'res.company', string='Şirket', related='unit_id.company_id',
        store=True, readonly=True, index=True,
    )
    partner_id = fields.Many2one('res.partner', string='Müşteri', required=True)
    user_id = fields.Many2one(
        'res.users', string='Danışman', default=lambda self: self.env.user, tracking=True,
    )
    opportunity_id = fields.Many2one(
        'crm.lead', string='CRM Fırsatı', index=True, tracking=True,
        help='Bu rezervasyonun bağlandığı CRM lead / fırsat.',
    )
    offer_price = fields.Monetary(string='Teklif Fiyatı', required=True, currency_field='currency_id')
    list_price = fields.Monetary(
        string='Liste Fiyatı', related='unit_id.list_price',
        readonly=True, currency_field='currency_id',
    )
    discount_pct = fields.Float(string='İndirim %', compute='_compute_discount_pct', store=True)
    currency_id = fields.Many2one('res.currency', related='unit_id.currency_id', readonly=True)
    date_offer = fields.Date(string='Teklif Tarihi', default=fields.Date.context_today)
    date_expiry = fields.Date(string='Son Geçerlilik')
    state = fields.Selection([
        ('draft', 'Beklemede'),
        ('accepted', 'Kabul Edildi'),
        ('refused', 'Reddedildi'),
        ('expired', 'Süresi Doldu'),
        ('cancel', 'İptal Edildi'),
        ('refund', 'İade'),
    ], string='Durum', default='draft', required=True, tracking=True)
    state_reason = fields.Text(string='Durum Açıklaması', tracking=True)
    notes = fields.Text(string='Notlar')
    sale_id = fields.Many2one('propertio.sale', string='Satış Sözleşmesi', copy=False, readonly=True)

    @api.depends('offer_price', 'list_price')
    def _compute_discount_pct(self):
        for r in self:
            if r.list_price and r.list_price > 0:
                r.discount_pct = ((r.list_price - r.offer_price) / r.list_price) * 100
            else:
                r.discount_pct = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('propertio.offer') or 'New'
            if vals.get('unit_id'):
                unit = self.env['propertio.unit'].browse(vals['unit_id'])
                if unit.state == 'available':
                    unit.write({'state': 'option'})
        return super(PropertioOffer, self).create(vals_list)

    def action_accept(self, context=None):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Yalnızca bekleyen rezervasyonlar kabul edilebilir.'))
        self.write({'state': 'accepted'})
        return self.action_convert_to_sale()

    def action_refuse(self, context=None):
        for offer in self:
            if offer.state != 'draft':
                raise UserError(_('Yalnızca bekleyen rezervasyonlar reddedilebilir.'))
            offer.write({'state': 'refused'})
            offer._release_unit()
        return True

    def action_cancel(self, context=None):
        """Cancel reservation (İptal Edildi) — frees unit if still optioned."""
        for offer in self:
            if offer.state in ('expired', 'refund'):
                raise UserError(_(
                    'Süresi dolmuş veya iade edilmiş rezervasyon iptal edilemez.'
                ))
            if offer.state == 'cancel':
                continue
            if offer.sale_id and offer.sale_id.state == 'confirmed':
                raise UserError(_(
                    'Bağlı onaylı satış sözleşmesi var. Önce sözleşmeyi iptal veya iade edin.'
                ))
            offer.write({'state': 'cancel'})
            if offer.sale_id and offer.sale_id.state == 'draft':
                offer.sale_id.action_cancel()
            offer._release_unit()
            offer.message_post(body=_('Rezervasyon / teklif iptal edildi.'))
        return True

    def action_refund(self, context=None):
        """Refund reservation deposit path (İade)."""
        for offer in self:
            if offer.state not in ('accepted', 'cancel'):
                raise UserError(_(
                    'İade yalnızca kabul edilmiş veya iptal edilmiş rezervasyonlar için geçerlidir.'
                ))
            if offer.sale_id and offer.sale_id.state == 'confirmed':
                # Align sale to refund as well
                offer.sale_id.action_refund()
            elif offer.sale_id and offer.sale_id.state == 'draft':
                offer.sale_id.action_cancel()
            offer.write({'state': 'refund'})
            offer._release_unit()
            offer.message_post(body=_(
                'Rezervasyon iade olarak işaretlendi. Kapora iadesi için ödeme sürecini tamamlayın.'
            ))
        return True

    def action_reset_to_draft(self, context=None):
        for offer in self:
            if offer.state not in ('refused', 'expired', 'cancel', 'refund'):
                raise UserError(_('Bu durumdan taslağa dönülemez.'))
            offer.write({'state': 'draft'})
            if offer.unit_id and offer.unit_id.state == 'available':
                offer.unit_id.state = 'option'
            offer.message_post(body=_('Rezervasyon tekrar beklemede.'))
        return True

    def _release_unit(self):
        for offer in self:
            unit = offer.unit_id
            if not unit or unit.state != 'option':
                continue
            other_open = self.search([
                ('unit_id', '=', unit.id),
                ('id', '!=', offer.id),
                ('state', 'in', ('draft', 'accepted')),
            ], limit=1)
            active_sale = self.env['propertio.sale'].search([
                ('unit_id', '=', unit.id),
                ('state', 'in', ('draft', 'confirmed')),
            ], limit=1)
            if not other_open and not active_sale:
                unit.write({'state': 'available'})

    @api.model
    def _cron_expire_offers(self):
        today = fields.Date.context_today(self)
        expired = self.search([
            ('state', '=', 'draft'),
            ('date_expiry', '!=', False),
            ('date_expiry', '<=', today),
        ])
        for offer in expired:
            offer.write({'state': 'expired'})
            offer._release_unit()

    def action_convert_to_sale(self, context=None):
        self.ensure_one()
        if self.state not in ('draft', 'accepted'):
            raise UserError(_('Bu rezervasyondan satış oluşturulamaz.'))
        if self.state != 'accepted':
            self.write({'state': 'accepted'})
        ctx = {
            'default_unit_id': self.unit_id.id,
            'default_partner_id': self.partner_id.id,
            'default_price': self.offer_price,
            'default_currency_id': self.currency_id.id,
            'default_opportunity_id': self.opportunity_id.id if self.opportunity_id else False,
            'propertio_offer_id': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Yeni Satış'),
            'res_model': 'propertio.sale.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
