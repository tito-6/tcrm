# Part of TCRM AI. See LICENSE for details.

"""
Post-process every Gemini answer before sending to user:
strip JSON/code, truncate if needed, ensure links are present.
"""

import re
import logging

from . import fallback_handler

_logger = logging.getLogger(__name__)

MAX_ANSWER_CHARS = 2000


def format_answer(raw_answer, tables=None, links=None, base_url=None):
    """
    Return cleaned answer text. Optionally append "See full details in TCRM" if truncated.
    Does NOT inject HTML here (chat UI does that); just the text.
    """
    if not raw_answer:
        return ""
    text = fallback_handler.strip_tool_call_blocks(raw_answer)
    if not text:
        return ""
    if len(text) > MAX_ANSWER_CHARS:
        text = text[:MAX_ANSWER_CHARS].rsplit(" ", 1)[0] if " " in text[:MAX_ANSWER_CHARS] else text[:MAX_ANSWER_CHARS]
        text += "… See full details in TCRM."
    return text.strip()
