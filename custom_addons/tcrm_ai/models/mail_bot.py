# Part of TCRM AI. See LICENSE for details.

import logging

from markupsafe import Markup

from tcrm import models, _

_logger = logging.getLogger(__name__)


class MailBot(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_answer(self, channel, body, values, command=False):
        """Replace tcrmBot with TCRM AI: answer any question using the Groq AI engine."""
        tcrmbot = self.env.ref('base.partner_root')
        if channel.channel_type != 'chat' or tcrmbot not in channel.channel_member_ids.partner_id:
            return False

        try:
            self.env.user.sudo().tcrmbot_state = 'idle'
        except Exception:
            pass

        body_clean = (body or '').strip()
        if not body_clean:
            return False

        # Same unified orchestration as full/floating assistant.
        if not (
            self.env.user.has_group('tcrm_ai.group_tcrm_ai_user')
            or self.env.user.has_group('tcrm_ai.group_tcrm_ai_admin')
            or self.env.user.has_group('base.group_system')
        ):
            return _('TCRM AI erişiminiz yok.')

        try:
            result = self.env['tcrm.ai.engine']._ask({
                'text': body_clean,
                'source': 'discuss',
            })
            if result.get('error'):
                return result.get('answer') or _(
                    'TCRM AI kullanılamıyor. Ayarlar > TCRM AI bölümünden yapılandırmayı kontrol edin.'
                )
            return self.env['tcrm.ai.engine']._format_answer_as_html(result)
        except Exception:
            _logger.exception('TCRM AI error in Discuss chat')
            return _(
                'TCRM AI bir hata ile karşılaştı. Ayarlar → TCRM AI bölümünü kontrol edin '
                'veya kısa süre sonra tekrar deneyin.'
            )
