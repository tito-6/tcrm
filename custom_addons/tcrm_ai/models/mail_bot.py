# Part of TCRM AI. See LICENSE for details.

import logging

from markupsafe import Markup

from tcrm import models, _

_logger = logging.getLogger(__name__)


class MailBot(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_answer(self, channel, body, values, command=False):
        """Replace tcrmBot with TCRM AI: answer any question using the AI engine."""
        tcrmbot = self.env.ref('base.partner_root')
        # Same condition as original mail_bot: only in 1:1 chat with the bot
        if channel.channel_type != 'chat' or tcrmbot not in channel.channel_member_ids.partner_id:
            return False

        # Set user to idle so parent never runs onboarding / "I don't understand"
        try:
            self.env.user.sudo().tcrmbot_state = 'idle'
        except Exception:
            pass

        body_clean = (body or '').strip()
        if not body_clean:
            return False

        # Always run TCRM AI for this chat (never return False so parent never runs)
        try:
            result = self.env['tcrm.ai.engine']._ask(body_clean)
            if result.get('error'):
                return result.get('answer', _('TCRM AI is not configured. Go to Settings and set your Gemini API key in the TCRM AI section.'))
            return self.env['tcrm.ai.engine']._format_answer_as_html(result)
        except Exception as e:
            _logger.exception("TCRM AI error in Discuss chat")
            return _('TCRM AI encountered an error. Check Settings → TCRM AI (API key and model) or try again. (%s)') % str(e)
