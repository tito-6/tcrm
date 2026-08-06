# Part of TCRM AI. See LICENSE for details.
"""Route native Odoo HTML editor / ChatGPT generate_text through Groq (TCRM AI)."""

import logging

from tcrm import http, _
from tcrm.exceptions import AccessError, UserError
from tcrm.http import request

_logger = logging.getLogger(__name__)


class TcrmAiHtmlEditorController(http.Controller):
    """Replace IAP OpenAI generate_text with the local TCRM AI (Groq) engine."""

    @http.route(
        ["/web_editor/generate_text", "/html_editor/generate_text"],
        type="jsonrpc",
        auth="user",
    )
    def generate_text(self, prompt, conversation_history):
        user = request.env.user
        if not (
            user.has_group('tcrm_ai.group_tcrm_ai_user')
            or user.has_group('tcrm_ai.group_tcrm_ai_admin')
            or user.has_group('base.group_system')
        ):
            raise AccessError(_('TCRM AI erişiminiz yok.'))

        if 'tcrm.ai.engine' not in request.env:
            raise UserError(_('TCRM AI is not installed on this database.'))

        history_bits = []
        for turn in (conversation_history or [])[-12:]:
            if not isinstance(turn, dict):
                continue
            role = turn.get('role') or turn.get('author') or 'user'
            content = turn.get('content') or turn.get('message') or turn.get('text') or ''
            content = (content or '').strip()
            if content:
                history_bits.append('%s: %s' % (role, content))
        prompt_text = (prompt or '').strip()
        if not prompt_text and not history_bits:
            raise UserError(_('Sorry, your prompt is too long. Try to say it in fewer words.'))

        text = '\n'.join(history_bits + (['user: %s' % prompt_text] if prompt_text else []))
        # Content drafting — keep tools off so the editor gets plain text.
        result = request.env['tcrm.ai.engine']._ask({
            'text': text,
            'source': 'html_editor',
            'disable_tools': True,
        })
        if result.get('error'):
            code = result.get('error_code') or ''
            if code == 'rate_limited':
                raise UserError(_(
                    'You have reached the maximum number of requests for this service. Try again later.'
                ))
            raise UserError(
                result.get('answer')
                or _('Sorry, we could not generate a response. Please try again later.')
            )
        answer = (result.get('answer') or '').strip()
        if not answer:
            raise UserError(_('Sorry, we could not generate a response. Please try again later.'))
        return answer
