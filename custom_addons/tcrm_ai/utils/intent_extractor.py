# Part of TCRM AI. See LICENSE for details.

"""
Lightweight intent and entity extraction before calling tools.
Helps route to the right tool and resolve contract/sale/partner references.
"""

import re
import logging

_logger = logging.getLogger(__name__)

INTENT_TYPES = [
    "count_records",
    "list_records",
    "get_record_details",
    "get_payment_plan",
    "get_paid_amount",
    "get_overdue",
    "search_partner",
    "general_question",
    "web_search",
    "follow_up",
    "clarification_needed",
]


# Patterns for intent (order matters: more specific first)
INTENT_PATTERNS = [
    (r"\b(how much has .+ paid|paid amount|amount paid|total paid|remaining balance)\b", "get_paid_amount"),
    (r"\b(overdue|late payment|who has overdue|past due)\b", "get_overdue"),
    (r"\b(payment plan|installments?|schedule)\s+(?:for|of)\b", "get_payment_plan"),
    (r"\b(details?|information|info|about)\s+(?:of\s+)?([A-Za-z0-9_-]+)\b", "get_record_details"),
    (r"\b([A-Za-z0-9_-]+)\s+contract\b", "get_record_details"),
    (r"\bcontract\s+([A-Za-z0-9_-]+)\b", "get_record_details"),
    (r"\b(how many|count|number of)\b", "count_records"),
    (r"\b(list|show|give me)\s+(?:all\s+)?(?:sales?|contracts?|leads?)\b", "list_records"),
    (r"\b(find|search|contact details?)\s+(?:for|of)?\s*(.+?)(?:\?|$)", "search_partner"),
    (r"\b(total\s+collected|total\s+amount|sum of|aggregate)\b", "get_paid_amount"),
    (r"\b(what is|who is|explain|define)\b", "general_question"),
    (r"\b(rate|dollar|today\'?s|current)\b.*\b(price|rate|exchange)\b", "web_search"),
    (r"\b(it|him|her|that contract|the same client|the first one|the third one|his|her)\b", "follow_up"),
]


def detect_intent(message, history=None):
    """
    Return (intent_type, entities dict).
    entities may include: name_or_id, partner_name, sale_id, ordinal (e.g. 3 for "third one").
    """
    if not message or not isinstance(message, str):
        return "general_question", {}
    text = message.strip().lower()
    entities = {}

    for pattern, intent in INTENT_PATTERNS:
        m = re.search(pattern, message, re.I | re.DOTALL)
        if m:
            if intent == "get_record_details" and m.lastindex and m.lastindex >= 1:
                entities["name_or_id"] = m.group(m.lastindex).strip()
            if intent == "get_payment_plan":
                # Extract name/code after "for X" or "of X"
                sub = re.search(r"(?:for|of)\s+([^.?!]+?)(?:\s+please|\s*$|\?|\.)", message, re.I)
                if sub:
                    entities["partner_name"] = sub.group(1).strip()
            if intent == "get_paid_amount":
                sub = re.search(r"(?:for|of)\s+(.+?)(?:\s+please|\s*$|\?|\.)", message, re.I)
                if sub:
                    entities["sale_or_partner"] = sub.group(1).strip()
            if intent == "search_partner" and m.lastindex and m.lastindex >= 2:
                entities["name"] = m.group(2).strip()
            if intent == "follow_up":
                # Ordinal: "the first one" -> 1, "the third one" -> 3
                ord_m = re.search(r"\b(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+one\b", message, re.I)
                if ord_m:
                    ordinals = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5}
                    entities["ordinal"] = ordinals.get(ord_m.group(1).lower(), 1)
            return intent, entities

    return "general_question", entities


def extract_contract_code(message):
    """Extract likely contract/sale code (e.g. OVER-001, DRAFT-001) from message."""
    # Codes like XXX-NNN
    m = re.search(r"\b([A-Za-z]{2,}-[0-9]{2,})\b", message)
    if m:
        return m.group(1).strip()
    m = re.search(r"\b([A-Za-z0-9_-]{3,})\s+contract\b", message, re.I)
    if m:
        return m.group(1).strip()
    return None
