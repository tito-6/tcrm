# Part of TCRM AI. See LICENSE for details.

"""
Manages per-session conversation history.
History is passed to Gemini on every turn so the model has full context.
"""

import json
import logging

_logger = logging.getLogger(__name__)

# Cap at last 10 exchanges (20 messages) to save tokens / quota
MAX_HISTORY_MESSAGES = 20


def get_history(env, session_id):
    """
    Return list of {"role": "user"|"assistant", "content": str}.
    Uses tcrm.ai.session if session_id given; else returns [].
    """
    if not session_id:
        return []
    try:
        Session = env.get('tcrm.ai.session')
        if not Session:
            return []
        return Session.get_history(session_id)
    except Exception as e:
        _logger.warning("conversation_memory get_history: %s", e)
        return []


def append(env, session_id, role, content):
    """Append one message. role in ('user', 'assistant'). content is string."""
    if not session_id:
        return
    try:
        Session = env.get('tcrm.ai.session')
        if Session:
            Session.append(session_id, role, content or '')
    except Exception as e:
        _logger.warning("conversation_memory append: %s", e)


def clear(env, session_id):
    """Clear conversation history for this session."""
    if not session_id:
        return
    try:
        Session = env.get('tcrm.ai.session')
        if Session:
            Session.clear(session_id)
    except Exception as e:
        _logger.warning("conversation_memory clear: %s", e)


def serialize_for_prompt(history):
    """Turn history list into a string block for the prompt."""
    if not history:
        return ""
    lines = []
    for msg in history:
        role = msg.get('role', 'user')
        content = (msg.get('content') or '').strip()
        if content:
            lines.append("[%s]: %s" % (role, content))
    return "\n".join(lines)
