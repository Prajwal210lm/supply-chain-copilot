"""Small shared helpers used across the generation modules.

Kept separate from copilot/constants.py (data) and the per-table generators
(logic specific to one table) so date/month arithmetic and weighted sampling
have exactly one implementation each.
"""

from datetime import date, timedelta

import numpy as np


def month_to_first_date(month: str) -> date:
    y, m = (int(x) for x in month.split("-"))
    return date(y, m, 1)


def month_to_last_date(month: str) -> date:
    y, m = (int(x) for x in month.split("-"))
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)


def add_months(month: str, n: int) -> str:
    y, m = (int(x) for x in month.split("-"))
    total = (y * 12 + (m - 1)) + n
    y2, m2 = divmod(total, 12)
    return f"{y2:04d}-{m2 + 1:02d}"


def months_between(start_month: str, end_month: str) -> int:
    """end_month minus start_month, in whole months (can be negative)."""
    ys, ms = (int(x) for x in start_month.split("-"))
    ye, me = (int(x) for x in end_month.split("-"))
    return (ye * 12 + (me - 1)) - (ys * 12 + (ms - 1))


def month_range(start_month: str, end_month: str) -> list[str]:
    n = months_between(start_month, end_month)
    return [add_months(start_month, i) for i in range(n + 1)]


def random_date_in_month(rng: np.random.Generator, month: str, max_day: int | None = None) -> date:
    """A uniformly random calendar date within `month`. If max_day is given,
    the draw is restricted to the first `max_day` days of the month (used to
    keep the last window month's deliveries from spilling past the window
    edge)."""
    first = month_to_first_date(month)
    last = month_to_last_date(month)
    days_in_month = (last - first).days + 1
    upper = min(days_in_month, max_day) if max_day is not None else days_in_month
    offset = int(rng.integers(0, upper))
    return first + timedelta(days=offset)


def allocate_counts(total: int, shares: dict) -> dict:
    """Largest-remainder rounding: split `total` across `shares` (a dict of
    label -> proportion, need not be pre-normalized) so the resulting integer
    counts sum to exactly `total`, rather than drifting by a unit from
    independent rounding of each share."""
    labels = list(shares.keys())
    weight_sum = sum(shares.values())
    raw = {label: total * shares[label] / weight_sum for label in labels}
    base = {label: int(raw[label]) for label in labels}
    remainder = total - sum(base.values())
    # Give the leftover units to the labels with the largest fractional part.
    fractions = sorted(labels, key=lambda label: raw[label] - base[label], reverse=True)
    for label in fractions[:remainder]:
        base[label] += 1
    return base


def weighted_choice_index(rng: np.random.Generator, weights: list[float]) -> int:
    p = np.asarray(weights, dtype=float)
    p = p / p.sum()
    return int(rng.choice(len(weights), p=p))


def weighted_sample_without_replacement(rng: np.random.Generator, n_items: int, weights: list[float], k: int) -> list[int]:
    """k distinct indices into range(n_items), drawn without replacement with
    probability proportional to `weights`. Used to pick distinct SKUs for an
    order's lines. Implemented as sequential weighted draws with removal —
    fine at this scale (at most 5 draws per call)."""
    k = min(k, n_items)
    pool = list(range(n_items))
    pool_weights = list(weights)
    chosen = []
    for _ in range(k):
        idx = weighted_choice_index(rng, pool_weights)
        chosen.append(pool[idx])
        del pool[idx]
        del pool_weights[idx]
    return chosen
