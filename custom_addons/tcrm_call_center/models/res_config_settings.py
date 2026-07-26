# -*- coding: utf-8 -*-
from tcrm import api, fields, models, _
from tcrm.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    santral_config_id = fields.Many2one(
        'tcrm.call.provider.config',
        compute='_compute_santral_config',
        string='Santral Config',
    )
    santral_enabled = fields.Boolean(related='santral_config_id.enabled', readonly=False)
    santral_provider = fields.Selection(related='santral_config_id.provider', readonly=False)
    santral_account_sid = fields.Char(related='santral_config_id.account_sid', readonly=False)
    santral_api_key_sid = fields.Char(related='santral_config_id.api_key_sid', readonly=False)
    santral_api_key_secret = fields.Char(related='santral_config_id.api_key_secret', readonly=False)
    santral_auth_token = fields.Char(related='santral_config_id.auth_token', readonly=False)
    santral_twiml_app_sid = fields.Char(related='santral_config_id.twiml_app_sid', readonly=False)
    santral_verified_caller_id = fields.Char(related='santral_config_id.verified_caller_id', readonly=False)
    santral_public_callback_base_url = fields.Char(related='santral_config_id.public_callback_base_url', readonly=False)
    santral_twilio_edge = fields.Selection(related='santral_config_id.twilio_edge', readonly=False)
    santral_recording_enabled = fields.Boolean(related='santral_config_id.recording_enabled', readonly=False)
    santral_dual_channel_recording = fields.Boolean(related='santral_config_id.dual_channel_recording', readonly=False)
    santral_recording_announcement_enabled = fields.Boolean(
        related='santral_config_id.recording_announcement_enabled', readonly=False,
    )
    santral_recording_announcement_text = fields.Text(
        related='santral_config_id.recording_announcement_text', readonly=False,
    )
    santral_recording_retention_days = fields.Integer(
        related='santral_config_id.recording_retention_days', readonly=False,
    )
    santral_allow_recording_download = fields.Boolean(
        related='santral_config_id.allow_recording_download', readonly=False,
    )
    santral_recording_storage = fields.Selection(
        related='santral_config_id.recording_storage', readonly=False,
    )
    santral_last_connection_test = fields.Datetime(related='santral_config_id.last_connection_test', readonly=True)
    santral_last_connection_status = fields.Selection(
        related='santral_config_id.last_connection_status', readonly=True,
    )
    santral_last_error = fields.Char(related='santral_config_id.last_error', readonly=True)
    santral_legal_warning = fields.Html(related='santral_config_id.legal_warning', readonly=True)

    def _compute_santral_config(self):
        Config = self.env['tcrm.call.provider.config']
        for rec in self:
            config = Config.get_for_company(self.env.company)
            if not config:
                config = Config.create({
                    'company_id': self.env.company.id,
                    'provider': 'twilio',
                    'enabled': False,
                })
            rec.santral_config_id = config

    def action_santral_test_connection(self):
        self.ensure_one()
        if not self.santral_config_id:
            raise UserError(_('Santral yapılandırılmamış'))
        return self.santral_config_id.action_test_connection()
