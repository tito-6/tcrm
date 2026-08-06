# -*- coding: utf-8 -*-
"""Shared pricing helpers for tcrm_offer (kuruş / minor units)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# Meta ad management fee tiers (budget and fee in major TRY units for readability;
# all public functions accept and return kuruş integers).
_TIER_FIXED_MAX = 50_000
_TIER_PCT_35_MAX = 70_000
_TIER_PCT_32_MAX = 100_000
_TIER_PCT_31_MAX = 500_000
# Zorunlu temel paket: bütçe ≤ 50.000 TL → 30.000 TL/ay reklam yönetimi
_FIXED_FEE = 30_000


def to_kurus(amount: float | Decimal | int | str) -> int:
    """Convert major currency units to integer kuruş."""
    d = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return int(d * 100)


def from_kurus(kurus: int) -> Decimal:
    return (Decimal(kurus) / Decimal(100)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def format_try(kurus: int) -> str:
    major = from_kurus(kurus)
    # Turkish grouping: 20.000,00 TL
    s = f'{major:,.2f}'
    # swap , and .
    int_part, frac = s.split('.')
    int_part = int_part.replace(',', '.')
    return f'{int_part},{frac} TL'


def meta_ad_management_fee_kurus(budget_kurus: int, custom_fee_kurus: int | None = None) -> int:
    """
    Compute Meta reklam yönetimi monthly fee from ad budget.

    Rules (major TRY):
      budget <= 50_000           -> 30_000 fixed (zorunlu temel paket)
      50_000 < budget < 70_000   -> budget * 0.35
      70_000 <= budget < 100_000 -> budget * 0.32
      100_000 <= budget <= 500_000 -> budget * 0.31
      budget > 500_000           -> custom_fee required (else raises)
    """
    budget = from_kurus(budget_kurus)
    if budget <= Decimal(_TIER_FIXED_MAX):
        return to_kurus(_FIXED_FEE)
    if budget < Decimal(_TIER_PCT_35_MAX):
        return to_kurus(budget * Decimal('0.35'))
    if budget < Decimal(_TIER_PCT_32_MAX):
        return to_kurus(budget * Decimal('0.32'))
    if budget <= Decimal(_TIER_PCT_31_MAX):
        return to_kurus(budget * Decimal('0.31'))
    if custom_fee_kurus is None:
        raise ValueError('custom_fee_required')
    return int(custom_fee_kurus)


def meta_requires_custom_fee(budget_kurus: int) -> bool:
    return from_kurus(budget_kurus) > Decimal(_TIER_PCT_31_MAX)


def apply_tax(net_kurus: int, tax_rate_percent: float | Decimal) -> dict[str, int]:
    """Return net, tax, gross for a single net amount (kuruş)."""
    rate = Decimal(str(tax_rate_percent)) / Decimal(100)
    net = int(net_kurus)
    tax = int((Decimal(net) * rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return {'net': net, 'tax': tax, 'gross': net + tax}


def validate_exclusive_groups(selected_items: list[dict[str, Any]]) -> None:
    """
    selected_items: list of dicts with keys id, exclusive_group (optional str).
    Raises ValueError if more than one item shares the same non-empty exclusive_group.
    """
    seen: dict[str, Any] = {}
    for item in selected_items:
        group = (item.get('exclusive_group') or '').strip()
        if not group:
            continue
        if group in seen:
            raise ValueError(f'exclusive_group_conflict:{group}')
        seen[group] = item.get('id')


def quote_offer(
    items: list[dict[str, Any]],
    selected_ids: set[Any],
    *,
    tax_rate_percent: float | Decimal,
    ad_budget_kurus: int | None = None,
) -> dict[str, Any]:
    """
    Server-authoritative quote.

    Each item dict:
      id, pricing_type (fixed|percentage|quantity|custom|meta_budget),
      unit_price_kurus, percentage_rate, quantity,
      billing_period (one_time|monthly|per_session),
      required (bool), taxable (bool), exclusive_group,
      custom_fee_kurus (optional, for meta >500k),
      meta_budget_field (bool) — if True, uses ad_budget_kurus for fee calc
    """
    selected = []
    for item in items:
        iid = item['id']
        required = bool(item.get('required'))
        if required or iid in selected_ids:
            selected.append(item)

    validate_exclusive_groups(selected)

    monthly = 0
    one_time = 0
    per_session = 0
    lines = []

    for item in selected:
        ptype = item.get('pricing_type') or 'fixed'
        taxable = bool(item.get('taxable', True))
        period = item.get('billing_period') or 'one_time'
        qty = int(item.get('quantity') or 1)
        if qty < 1:
            qty = 1

        if ptype == 'meta_budget':
            budget = ad_budget_kurus if ad_budget_kurus is not None else int(item.get('unit_price_kurus') or 0)
            custom = item.get('custom_fee_kurus')
            line_net = meta_ad_management_fee_kurus(budget, custom)
            # budget itself is paid to Meta, not included in our fee
        elif ptype == 'percentage':
            base = int(item.get('unit_price_kurus') or 0)
            rate = Decimal(str(item.get('percentage_rate') or 0)) / Decimal(100)
            line_net = int((Decimal(base) * rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        elif ptype == 'quantity':
            line_net = int(item.get('unit_price_kurus') or 0) * qty
        elif ptype == 'custom':
            line_net = int(item.get('unit_price_kurus') or 0)
        else:  # fixed
            line_net = int(item.get('unit_price_kurus') or 0) * qty

        if period == 'monthly':
            monthly += line_net if taxable or True else line_net
            # track taxable separately below
        elif period == 'per_session':
            per_session += line_net
        else:
            one_time += line_net

        lines.append({
            'id': item['id'],
            'name': item.get('name'),
            'billing_period': period,
            'net_kurus': line_net,
            'taxable': taxable,
            'quantity': qty,
        })

    taxable_net = sum(l['net_kurus'] for l in lines if l['taxable'])
    nontaxable_net = sum(l['net_kurus'] for l in lines if not l['taxable'])
    tax_part = apply_tax(taxable_net, tax_rate_percent)
    total_net = taxable_net + nontaxable_net
    total_tax = tax_part['tax']
    total_gross = total_net + total_tax

    monthly_taxable = sum(
        l['net_kurus'] for l in lines
        if l['billing_period'] == 'monthly' and l['taxable']
    )
    monthly_nontax = sum(
        l['net_kurus'] for l in lines
        if l['billing_period'] == 'monthly' and not l['taxable']
    )
    one_time_taxable = sum(
        l['net_kurus'] for l in lines
        if l['billing_period'] == 'one_time' and l['taxable']
    )
    one_time_nontax = sum(
        l['net_kurus'] for l in lines
        if l['billing_period'] == 'one_time' and not l['taxable']
    )
    session_taxable = sum(
        l['net_kurus'] for l in lines
        if l['billing_period'] == 'per_session' and l['taxable']
    )
    session_nontax = sum(
        l['net_kurus'] for l in lines
        if l['billing_period'] == 'per_session' and not l['taxable']
    )

    def pack(taxable_k, nontax_k):
        t = apply_tax(taxable_k, tax_rate_percent)
        net = taxable_k + nontax_k
        return {'net': net, 'tax': t['tax'], 'gross': net + t['tax']}

    return {
        'lines': lines,
        'monthly': pack(monthly_taxable, monthly_nontax),
        'one_time': pack(one_time_taxable, one_time_nontax),
        'per_session': pack(session_taxable, session_nontax),
        'net_kurus': total_net,
        'tax_kurus': total_tax,
        'gross_kurus': total_gross,
        'tax_rate_percent': float(tax_rate_percent),
        'ad_budget_kurus': ad_budget_kurus,
    }
