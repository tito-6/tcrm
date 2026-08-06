# Part of TCRM AI. See LICENSE for details.

from tcrm import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider_summary = fields.Char(
        string='AI providers',
        compute='_compute_ai_provider_summary',
    )
    ai_health_status = fields.Selection(
        [
            ('all_ok', 'All OK'),
            ('degraded', 'Degraded'),
            ('all_down', 'All Down'),
            ('none', 'No providers'),
        ],
        string='AI health',
        compute='_compute_ai_provider_summary',
    )

    @api.depends()
    def _compute_ai_provider_summary(self):
        for rec in self:
            try:
                status = rec.env['tcrm.ai.config'].sudo().get_public_status()
                if status.get('configured') and status.get('ai_enabled'):
                    rec.ai_provider_summary = '%s / %s' % (status.get('provider'), status.get('model'))
                    rec.ai_health_status = 'all_ok' if status.get('last_connection_status') == 'ok' else 'degraded'
                elif status.get('configured'):
                    rec.ai_provider_summary = 'Key saved — AI disabled or untested'
                    rec.ai_health_status = 'degraded'
                else:
                    rec.ai_provider_summary = 'Yapılandırma gerekli'
                    rec.ai_health_status = 'none'
            except Exception:
                rec.ai_provider_summary = 'Configure TCRM AI'
                rec.ai_health_status = 'none'
