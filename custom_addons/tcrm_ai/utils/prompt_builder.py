# Part of TCRM AI. See LICENSE for details.

"""
Build the full system and user prompt for Gemini, including identity, account context,
conversation history, and tool descriptions.
"""

import logging

from . import conversation_memory

_logger = logging.getLogger(__name__)


def build_account_context(env):
    """Section 2: dynamic account context (counts, user, company, date)."""
    lines = []
    try:
        if env.get("res.partner"):
            n = env["res.partner"].search_count([])
            lines.append("Total contacts/partners: %d" % n)
        for model_label, model_name in (
            ("property sales", "propertio.sale"),
            ("sale orders", "sale.order"),
            ("leads", "crm.lead"),
            ("invoices", "account.move"),
        ):
            if env.get(model_name):
                n = env[model_name].search_count([])
                lines.append("Total %s: %d" % (model_label, n))
        user = env.user
        lines.append("Current user: %s" % (user.name or user.login))
        if env.company:
            lines.append("Company: %s" % env.company.name)
        from datetime import date
        lines.append("Today's date: %s" % date.today().isoformat())
    except Exception as e:
        _logger.warning("prompt_builder account_context: %s", e)
    return "\n".join(lines) if lines else "No account summary available."


def build_history_section(history):
    """Section 3: conversation history (last 20 messages)."""
    if not history:
        return ""
    return conversation_memory.serialize_for_prompt(history)


def build_system_prompt(account_context, history_str=""):
    """Full system prompt (identity, rules, account, history, tools, format)."""
    return """SECTION 1 — IDENTITY & RULES
You are TCRM AI, an expert assistant for a real-estate CRM.
You answer in clear, professional, friendly English (or the user's language).
You NEVER show JSON, code blocks, tool call syntax, or error messages to the user.
If you need data, call the appropriate tool. Wait for the result, then answer.
If a question is ambiguous, ask ONE short clarifying question.
Always address the user's actual intent, not just the literal words.

SECTION 2 — ACCOUNT CONTEXT
%s

SECTION 3 — CONVERSATION HISTORY (use for follow-up and references)
%s

SECTION 4 — AVAILABLE TOOLS (actual calls are handled by the system)
- get_record_details(name_or_id, model?) → full details of a sale, contract, lead, or partner by name/code (e.g. OVER-001)
- search_sales(partner_name?, limit?) → list property sales
- get_payment_plan(sale_id?, partner_name?) → full installment schedule
- get_paid_amount(sale_id_or_partner_name) → total paid and remaining balance
- search_partners(name?, limit?) → find contacts / companies
- run_search_read(model, fields, domain, limit) → flexible data query
- get_overdue_payments(days_overdue?) → list overdue installments
- summarize_sales_pipeline() → aggregate stats (total sales, revenue, collected, outstanding)
- web_search(query, num_results?) → search the internet

SECTION 5 — TOOL CALL FORMAT (never shown to user)
To call a tool, respond ONLY with this JSON, no other text:
{"tool": "<tool_name>", "args": {<args>}}

SECTION 6 — ANSWER FORMAT
- Use bullet points or a table when listing multiple records
- Include "Open in TCRM" links when returning record details
- For payment plans: show installment name, due date, amount, paid/unpaid status
- For summaries (e.g. total paid): state the number clearly upfront
- Keep answers concise but complete
""" % (
        account_context,
        history_str or "(No prior messages in this conversation.)",
    )


def build_user_block(resolved_message, resolved_entities_hint=""):
    """Current user message block, optionally with resolved context hint."""
    if resolved_entities_hint:
        return "User: %s\n[Resolved context: %s]" % (resolved_message, resolved_entities_hint)
    return "User: %s" % resolved_message
