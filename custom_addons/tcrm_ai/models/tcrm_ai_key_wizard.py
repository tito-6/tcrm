# Part of TCRM AI. See LICENSE for details.

from tcrm import models, fields, _
from tcrm.exceptions import UserError

from ..services.crypto import encrypt_secret


class TcrmAiKeyWizard(models.TransientModel):
    _name = 'tcrm.ai.key.wizard'
    _description = 'Change TCRM AI API Key'

    config_id = fields.Many2one('tcrm.ai.config', required=True)
    api_key_input = fields.Char(string='New API Key', required=True)

    def action_confirm(self):
        self.ensure_one()
        raw = (self.api_key_input or '').strip()
        if len(raw) < 20:
            raise UserError(_('API anahtarı geçersiz görünüyor.'))
        self.config_id._require_ai_admin()
        self.config_id.write({'api_key_encrypted': encrypt_secret(self.env, raw)})
        return {'type': 'ir.actions.act_window_close'}


class TcrmAiKeyDeleteWizard(models.TransientModel):
    _name = 'tcrm.ai.key.delete.wizard'
    _description = 'Delete TCRM AI API Key'

    config_id = fields.Many2one('tcrm.ai.config', required=True)
    confirm = fields.Boolean(string='Anahtarı silmeyi onaylıyorum')

    def action_confirm(self):
        self.ensure_one()
        if not self.confirm:
            raise UserError(_('Lütfen silme işlemini onaylayın.'))
        self.config_id.clear_api_key()
        return {'type': 'ir.actions.act_window_close'}
