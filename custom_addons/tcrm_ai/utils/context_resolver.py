# Part of TCRM AI. See LICENSE for details.

"""
Resolve pronouns and references in the user message against conversation history.
e.g. "the paid amount of it" -> resolve "it" to last mentioned sale/partner.
"""

import re
import logging

_logger = logging.getLogger(__name__)


def resolve_message(message, history, last_entities=None):
    """
    Return (resolved_message, resolved_entities).
    - resolved_message: user message with references clarified if possible.
    - resolved_entities: dict to inject into tool args (e.g. sale_id, partner_name, name_or_id).
    last_entities: optional dict from previous turn { "sale_id": 9, "partner_name": "Michael Brown", "model": "propertio.sale" }.
    """
    if not message or not isinstance(message, str):
        return message, last_entities or {}

    resolved = message
    entities = dict(last_entities or {})

    # Ordinal: "the third one" -> need to resolve from last list in history
    ord_m = re.search(r"\b(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+one\b", message, re.I)
    if ord_m:
        ordinals = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5}
        idx = ordinals.get(ord_m.group(1).lower(), 1)
        # Look in last assistant message for a list (e.g. table of sales) and pick the Nth
        for h in reversed(history):
            if h.get("role") == "assistant":
                content = h.get("content") or ""
                # Heuristic: look for "id" or "name" in table/list; we don't parse tables here
                # So we set ordinal_index for the executor to use with last tool result
                entities["ordinal_index"] = idx
                break
        resolved = re.sub(r"\b(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+one\b", f"the #{idx} from the previous list", resolved, flags=re.I)

    # "it", "him", "her", "that contract", "the same client"
    if re.search(r"\b(it|him|her|that contract|the same client|his|her)\b", message, re.I):
        if last_entities:
            if last_entities.get("sale_id"):
                resolved = re.sub(r"\b(it|that contract)\b", f"sale id {last_entities['sale_id']}", resolved, flags=re.I)
                entities["sale_id"] = last_entities["sale_id"]
            if last_entities.get("partner_name"):
                resolved = re.sub(r"\b(him|her|the same client)\b", last_entities["partner_name"], resolved, flags=re.I)
                entities["partner_name"] = last_entities["partner_name"]
        # If we couldn't resolve, intent can be marked clarification_needed later

    return resolved, entities


def extract_last_entities_from_assistant_content(content, tool_results=None):
    """
    From the last assistant reply (or tool result), extract sale_id, partner_name, etc.
    so we can pass them as last_entities on the next turn.
    tool_results: optional list of last tool call results (dicts with rows, link, etc.)
    """
    entities = {}
    if not content and not tool_results:
        return entities
    if tool_results:
        for tr in (tool_results or [])[-2:]:  # last 2 results
            if isinstance(tr, dict):
                if tr.get("link") and isinstance(tr["link"], dict):
                    url = tr["link"].get("url", "")
                    # /web#id=9&model=propertio.sale
                    id_m = re.search(r"id=(\d+)", url)
                    model_m = re.search(r"model=([^&]+)", url)
                    if id_m:
                        entities["sale_id"] = int(id_m.group(1))
                    if model_m:
                        entities["model"] = model_m.group(1)
                rows = tr.get("rows") or []
                if rows and isinstance(rows[0], dict):
                    first = rows[0]
                    if "partner" in first:
                        entities["partner_name"] = str(first.get("partner", "")).strip()
                    elif "partner_id" in first:
                        entities["partner_name"] = str(first.get("partner_id", "")).strip()
                    elif "name" in first:
                        entities["last_name"] = str(first.get("name", "")).strip()
    return entities
