# -*- coding: utf-8 -*-
import os

from tcrm import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tcrm_marketing_zernio_api_key = fields.Char(
        string='Zernio API Anahtarı',
        config_parameter='tcrm_marketing_hub.zernio_api_key',
        help='Zernio dashboard üzerinden oluşturulan API anahtarı. '
             'Tarayıcıya gönderilmez. Ortam değişkeni: ZERNIO_API_KEY.',
    )
    tcrm_marketing_zernio_base_url = fields.Char(
        string='Zernio API URL',
        config_parameter='tcrm_marketing_hub.zernio_base_url',
        default='https://zernio.com/api/v1',
    )
    tcrm_marketing_default_profile_id = fields.Char(
        string='Varsayılan Zernio Profil ID',
        config_parameter='tcrm_marketing_hub.default_profile_id',
        help='Boş bırakılırsa senkron sırasında ilk profil kullanılır.',
    )
    tcrm_marketing_env_override_hint = fields.Char(
        string='Ortam Override',
        compute='_compute_marketing_env_hint',
    )

    @api.depends_context('uid')
    def _compute_marketing_env_hint(self):
        hint = 'ZERNIO_API_KEY' if os.environ.get('ZERNIO_API_KEY') else self.env._('Yok')
        for rec in self:
            rec.tcrm_marketing_env_override_hint = hint
