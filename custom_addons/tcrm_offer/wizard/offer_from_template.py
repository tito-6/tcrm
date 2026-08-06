# -*- coding: utf-8 -*-
from datetime import timedelta

from tcrm import api, fields, models, _
from tcrm.exceptions import UserError


class TcrmOfferFromTemplate(models.TransientModel):
    _name = 'tcrm.offer.from.template'
    _description = 'Şablondan Teklif Oluştur'

    template_id = fields.Many2one('tcrm.offer.template', string='Şablon', required=True)
    partner_id = fields.Many2one('res.partner', string='Müşteri', required=True)
    partner_contact_name = fields.Char(string='Yetkili Adı')
    title = fields.Char(string='Başlık')

    @api.onchange('template_id')
    def _onchange_template(self):
        if self.template_id:
            self.title = self.template_id.title or self.template_id.name
            if self.template_id.partner_label and not self.partner_contact_name:
                self.partner_contact_name = self.template_id.partner_label

    def action_create(self):
        self.ensure_one()
        tmpl = self.template_id
        if not tmpl:
            raise UserError(_('Şablon seçin.'))
        valid_until = fields.Date.context_today(self) + timedelta(days=tmpl.validity_days or 15)
        vals = {
            'partner_id': self.partner_id.id,
            'partner_contact_name': self.partner_contact_name or '',
            'title': self.title or tmpl.title or tmpl.name,
            'summary': tmpl.summary,
            'scope_html': tmpl.scope_html,
            'terms_html': tmpl.terms_html,
            'contract_intro_html': tmpl.contract_intro_html,
            'provider_legal_name': tmpl.provider_legal_name,
            'provider_short_name': tmpl.provider_short_name,
            'valid_until': valid_until,
            'ad_budget_default': tmpl.ad_budget_default,
            'ad_budget_min': tmpl.ad_budget_min,
            'ad_budget_max': tmpl.ad_budget_max,
            'catalogue_ids': [(6, 0, tmpl.catalogue_ids.ids)],
            'currency_id': (
                self.env['tcrm.offer']._default_offer_currency().id
            ),
            'item_ids': [
                (0, 0, {
                    'name': it.name,
                    'description': it.description,
                    'category': it.category,
                    'pricing_type': it.pricing_type,
                    'unit_price': it.unit_price,
                    'percentage_rate': it.percentage_rate,
                    'quantity': it.quantity,
                    'custom_fee': it.custom_fee,
                    'billing_period': it.billing_period,
                    'selection_type': it.selection_type,
                    'default_selected': it.default_selected,
                    'taxable': it.taxable,
                    'sort_order': it.sort_order,
                    'includes_html': it.includes_html,
                    'excludes_html': it.excludes_html,
                    'exclusive_group': it.exclusive_group,
                    'code': it.code,
                    'package_group': it.package_group,
                    'client_choice_label': it.client_choice_label,
                    'client_choice_options': it.client_choice_options,
                })
                for it in tmpl.item_ids
            ],
        }
        offer = self.env['tcrm.offer'].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tcrm.offer',
            'res_id': offer.id,
            'view_mode': 'form',
            'target': 'current',
        }
