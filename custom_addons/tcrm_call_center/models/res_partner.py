# -*- coding: utf-8 -*-
from tcrm import fields, models, _
from tcrm.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    santral_call_count = fields.Integer(compute='_compute_santral_call_count')

    def _compute_santral_call_count(self):
        Call = self.env['tcrm.call.record']
        for partner in self:
            partner.santral_call_count = Call.search_count([('partner_id', '=', partner.id)])

    def action_santral_call(self):
        self.ensure_one()
        self.check_access('read')
        config = self.env['tcrm.call.provider.config'].get_for_company(require_enabled=True)
        if not config:
            raise UserError(_('Santral yapılandırılmamış'))
        call, dial_token, _config = self.env['tcrm.call.record'].action_prepare_outbound(
            res_model='res.partner', res_id=self.id,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'tcrm_call_center.dialer',
            'name': _('Ara'),
            'target': 'new',
            'context': {
                'call_id': call.id,
                'dial_token': dial_token,
                'partner_id': self.id,
                'record_name': self.display_name,
                'phone_masked': call.destination_masked,
                'project_name': '',
                'caller_id_masked': ('*' * max(0, len(call.caller_id or '') - 4)) + (call.caller_id or '')[-4:],
            },
        }
