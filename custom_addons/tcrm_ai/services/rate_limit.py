# Part of TCRM AI. See LICENSE for details.
"""Per-user and per-tenant throttling using tenant-local usage rows."""
from __future__ import annotations

from datetime import datetime, timedelta

from tcrm import fields

from .constants import SAFE_ERROR_CODES, rate_limit_user_message


class RateLimitError(Exception):
    def __init__(self, code: str = 'rate_limited', retry_after: int = 15):
        self.code = code
        self.retry_after = max(5, int(retry_after or 15))
        if code in ('rate_limited', 'quota_exceeded'):
            self.safe_message = rate_limit_user_message(self.retry_after)
        else:
            self.safe_message = SAFE_ERROR_CODES.get(code, SAFE_ERROR_CODES['rate_limited'])
        super().__init__(self.safe_message)


def _today_domain(user_id=None, company_id=None):
    today = fields.Date.context_today
    # caller passes env via usage model methods
    return today


def check_and_consume(env, config) -> None:
    """Raise RateLimitError when tenant/user limits are exceeded."""
    Usage = env['tcrm.ai.usage']
    now = fields.Datetime.now()
    today = fields.Date.context_today(env['tcrm.ai.usage'])
    month_start = today.replace(day=1)

    user = env.user
    company = env.company

    # Per-user RPM (soft, in-process window via recent usage rows)
    rpm_limit = max(1, int(getattr(config, 'rpm_limit', 10) or 10))
    window_start = now - timedelta(seconds=60)
    user_rpm = Usage.search_count([
        ('user_id', '=', user.id),
        ('create_date', '>=', fields.Datetime.to_string(window_start) if isinstance(window_start, datetime) else window_start),
        ('success', '=', True),
    ])
    if user_rpm >= rpm_limit:
        raise RateLimitError('rate_limited')

    daily_req = int(config.daily_request_limit or 0)
    daily_tok = int(config.daily_token_limit or 0)
    monthly_tok = int(config.monthly_usage_limit or 0)

    if daily_req:
        tenant_today = Usage.search_count([
            ('create_date', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
        ])
        if tenant_today >= daily_req:
            # Soft block only — do not permanently sticky-lock entitlement.
            raise RateLimitError('quota_exceeded')

    if daily_tok:
        rows = Usage.search([
            ('create_date', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
        ])
        tokens_today = sum(rows.mapped('total_tokens'))
        if tokens_today >= daily_tok:
            raise RateLimitError('quota_exceeded')

    if monthly_tok:
        rows = Usage.search([
            ('create_date', '>=', fields.Datetime.to_string(datetime.combine(month_start, datetime.min.time()))),
        ])
        tokens_month = sum(rows.mapped('total_tokens'))
        if tokens_month >= monthly_tok:
            raise RateLimitError('quota_exceeded')

    # Duplicate in-flight guard (same user, last 2s pending)
    recent_pending = Usage.search_count([
        ('user_id', '=', user.id),
        ('company_id', '=', company.id),
        ('create_date', '>=', fields.Datetime.to_string(now - timedelta(seconds=2))),
        ('in_flight', '=', True),
    ])
    if recent_pending:
        raise RateLimitError('rate_limited')


def usage_dashboard(env) -> dict:
    Usage = env['tcrm.ai.usage']
    today = fields.Date.context_today(Usage)
    month_start = today.replace(day=1)
    day_start = datetime.combine(today, datetime.min.time())
    month_dt = datetime.combine(month_start, datetime.min.time())

    today_rows = Usage.search([('create_date', '>=', fields.Datetime.to_string(day_start))])
    month_rows = Usage.search([('create_date', '>=', fields.Datetime.to_string(month_dt))])

    def _avg_ms(rows):
        vals = [r.duration_ms for r in rows if r.duration_ms]
        return int(sum(vals) / len(vals)) if vals else 0

    fail = len(month_rows.filtered(lambda r: not r.success))
    tool_counter = {}
    user_counter = {}
    for r in month_rows:
        for t in (r.tools_used or '').split(','):
            t = t.strip()
            if t:
                tool_counter[t] = tool_counter.get(t, 0) + 1
        if r.user_id:
            user_counter[r.user_id.name] = user_counter.get(r.user_id.name, 0) + 1

    top_tools = sorted(tool_counter.items(), key=lambda x: -x[1])[:10]
    top_users = sorted(user_counter.items(), key=lambda x: -x[1])[:10]

    return {
        'requests_today': len(today_rows),
        'tokens_today': sum(today_rows.mapped('total_tokens')),
        'monthly_requests': len(month_rows),
        'monthly_tokens': sum(month_rows.mapped('total_tokens')),
        'average_response_ms': _avg_ms(month_rows),
        'failure_rate': (fail / len(month_rows)) if month_rows else 0.0,
        'most_used_tools': [{'name': n, 'count': c} for n, c in top_tools],
        'most_active_users': [{'name': n, 'count': c} for n, c in top_users],
    }
