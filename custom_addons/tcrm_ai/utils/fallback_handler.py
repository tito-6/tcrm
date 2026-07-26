# Part of TCRM AI. See LICENSE for details.

"""
Handle empty responses, tool errors, and strip any raw JSON/code from answers.
NEVER show: raw JSON, Python tracebacks, Odoo error codes, tool names to the user.
"""

import json
import re
import logging

_logger = logging.getLogger(__name__)


def strip_tool_call_blocks(text):
    """Remove any ```json ... ``` or raw {"tool": ...} blocks from text."""
    if not text or not isinstance(text, str):
        return (text or "").strip()
    # Code block with {"tool": ...}
    text = re.sub(r"```(?:json)?\s*\{[^`]*\"tool\"\s*:[^`]*\}\s*```", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Raw JSON line
    text = re.sub(r"^\s*\{\s*\"tool\"\s*:\s*[^}]+\}\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def build_fallback_from_data(user_message, tables, links):
    """When Gemini returns empty but we have tool results, build a human answer."""
    parts = []
    if user_message:
        parts.append("Here are the details for your request (« %s »):" % (user_message[:80] + ("…" if len(user_message) > 80 else "")))
    else:
        parts.append("Here are the results:")
    if tables:
        for t in tables:
            rows = t.get("rows") or []
            if rows:
                parts.append("Found %d record(s). See the table below." % len(rows))
                break
    if links:
        labels = [l.get("label") or l.get("url") or "" for l in links[:5]]
        parts.append("Open in TCRM: " + ", ".join(labels))
    return " ".join(parts) if parts else "Results are in the table and links below."


def handle_tool_error(e, user_facing=True):
    """Log the error; return user-friendly message if user_facing."""
    _logger.warning("TCRM AI tool error: %s", e)
    if not user_facing:
        raise
    return "I couldn't retrieve that data right now. Please try again or check TCRM directly."


def sanitize_error_message(err_msg):
    """Remove tracebacks, file paths, and internal codes from error messages."""
    if not err_msg:
        return "Something went wrong. Please try again."
    # Truncate long errors
    err_msg = str(err_msg).split("\n")[0][:200]
    # Replace common internal phrases
    for bad in ("Traceback", "File \"", "line ", "Error code", "odoo.exceptions"):
        if bad in err_msg:
            return "I couldn't complete that request. Please try again or rephrase."
    return err_msg.encode("ascii", "replace").decode("ascii")
