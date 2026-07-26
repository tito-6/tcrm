# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Deterministic market analytics helpers (asking prices only)."""
from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence


def _clean(values: Iterable[float]) -> List[float]:
    out = []
    for v in values:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def mean(values: Sequence[float]) -> Optional[float]:
    data = _clean(values)
    if not data:
        return None
    return round(sum(data) / len(data), 4)


def median(values: Sequence[float]) -> Optional[float]:
    data = sorted(_clean(values))
    n = len(data)
    if not n:
        return None
    mid = n // 2
    if n % 2:
        return round(data[mid], 4)
    return round((data[mid - 1] + data[mid]) / 2.0, 4)


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    data = sorted(_clean(values))
    n = len(data)
    if not n:
        return None
    if n == 1:
        return round(data[0], 4)
    p = max(0.0, min(100.0, float(p)))
    k = (n - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(data[int(k)], 4)
    d0 = data[f] * (c - k)
    d1 = data[c] * (k - f)
    return round(d0 + d1, 4)


def min_max(values: Sequence[float]):
    data = _clean(values)
    if not data:
        return None, None
    return min(data), max(data)


def iqr_outlier_mask(values: Sequence[float], factor: float = 1.5) -> List[bool]:
    data = _clean(values)
    if len(data) < 4:
        return [False] * len(values)
    q1 = percentile(data, 25)
    q3 = percentile(data, 75)
    if q1 is None or q3 is None:
        return [False] * len(values)
    iqr = q3 - q1
    low, high = q1 - factor * iqr, q3 + factor * iqr
    mask = []
    for v in values:
        try:
            f = float(v)
            mask.append(bool(math.isfinite(f) and (f < low or f > high)))
        except (TypeError, ValueError):
            mask.append(False)
    return mask


def indicative_gross_yield(annual_rent_asking: Optional[float], sale_asking: Optional[float]) -> Optional[float]:
    """Indicative gross rental yield from asking prices (not transaction prices)."""
    if not annual_rent_asking or not sale_asking or sale_asking <= 0:
        return None
    return round((annual_rent_asking / sale_asking) * 100.0, 4)


def sale_rent_ratio(median_sale: Optional[float], median_monthly_rent: Optional[float]) -> Optional[float]:
    if not median_sale or not median_monthly_rent or median_monthly_rent <= 0:
        return None
    return round(median_sale / median_monthly_rent, 4)


def summarize_prices(values: Sequence[float]) -> dict:
    data = _clean(values)
    if not data:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
        }
    lo, hi = min_max(data)
    return {
        "count": len(data),
        "mean": mean(data),
        "median": median(data),
        "min": lo,
        "max": hi,
        "p10": percentile(data, 10),
        "p25": percentile(data, 25),
        "p75": percentile(data, 75),
        "p90": percentile(data, 90),
    }


def comparable_score(subject: dict, candidate: dict) -> tuple:
    """Explainable score (higher is better). Returns (score, factors)."""
    score = 0.0
    factors = []

    if subject.get("transaction_type") and subject.get("transaction_type") == candidate.get("transaction_type"):
        score += 25
        factors.append("transaction_match")
    if subject.get("category_code") and subject.get("category_code") == candidate.get("category_code"):
        score += 20
        factors.append("category_match")
    if subject.get("neighborhood") and subject.get("neighborhood") == candidate.get("neighborhood"):
        score += 15
        factors.append("neighborhood_match")
    elif subject.get("district") and subject.get("district") == candidate.get("district"):
        score += 10
        factors.append("district_match")
    elif subject.get("province") and subject.get("province") == candidate.get("province"):
        score += 5
        factors.append("province_match")

    s_area = subject.get("gross_area") or 0
    c_area = candidate.get("gross_area") or 0
    if s_area and c_area:
        rel = abs(s_area - c_area) / max(s_area, c_area)
        area_pts = max(0.0, 15.0 * (1.0 - rel))
        score += area_pts
        factors.append("area_proximity:%.1f" % area_pts)

    if subject.get("rooms") and subject.get("rooms") == candidate.get("rooms"):
        score += 8
        factors.append("rooms_match")

    if candidate.get("state") == "active":
        score += 5
        factors.append("active")

    quality = candidate.get("quality_score") or 0
    score += min(7.0, float(quality) / 15.0)
    if quality:
        factors.append("quality")

    return round(score, 4), factors
