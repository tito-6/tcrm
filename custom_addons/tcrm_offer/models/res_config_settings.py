# -*- coding: utf-8 -*-
from tcrm import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tcrm_offer_default_tax_rate = fields.Float(
        string='Varsayılan Teklif KDV Oranı (%)',
        config_parameter='tcrm_offer.default_tax_rate',
        default=20.0,
    )
    tcrm_offer_public_base_url = fields.Char(
        string='Teklif Public Base URL',
        config_parameter='tcrm_offer.public_base_url',
        help='Örn. https://akod.tcrm.online — boşsa web.base.url kullanılır.',
    )
