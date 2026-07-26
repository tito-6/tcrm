# -*- coding: utf-8 -*-
from tcrm import fields, models, _
from tcrm.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    santral_call_count = fields.Integer(compute='_compute_santral_call_count')

    def _compute_santral_call_count(self):
        Call = self.env['tcrm.call.record']
        for lead in self:
            lead.santral_call_count = Call.search_count([('lead_id', '=', lead.id)])

    def action_santral_call(self):
        self.ensure_one()
        self.check_access('read')
        config = self.env['tcrm.call.provider.config'].get_for_company(require_enabled=True)
        if not config:
            raise UserError(_('Santral yapılandırılmamış'))
        call, dial_token, _config = self.env['tcrm.call.record'].action_prepare_outbound(
            res_model='crm.lead', res_id=self.id,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'tcrm_call_center.dialer',
            'name': _('Ara'),
            'target': 'new',
            'context': {
                'call_id': call.id,
                'dial_token': dial_token,
                'lead_id': self.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'record_name': self.display_name,
                'phone_masked': call.destination_masked,
                'project_name': self.propertio_project_id.display_name if self.propertio_project_id else '',
                'caller_id_masked': call.caller_id[-4:].rjust(len(call.caller_id or ''), '*') if call.caller_id else '',
            },
        }
