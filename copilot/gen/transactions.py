"""Orders and order_lines: the demand/fulfillment layer.

This is where Story 1 (Anadolu/AUH delivery failures) and Story 3
(traditional_trade churn) are planted. They are kept in clearly separate
code paths on purpose:

  - Story 3 (`_churn_factor`) only ever influences how many orders a
    customer places in a given month — it is evaluated and fully resolved
    before a single order is constructed, and it has no visibility into
    delivery-outcome logic at all.
  - Story 1 (`_is_story1_affected_line` / the on_time and short-ship draws)
    only ever influences whether an already-decided order/line is delivered
    on time and in full — it has no visibility into how the order count was
    decided.

  Story 3's hard constraint (demand-side only, must not touch Feb-Mar 2026
  delivery outcomes) is therefore enforced by this module structure, not by
  a comment someone could drift away from.
"""

import math

import numpy as np
import pandas as pd

from copilot import constants as C
from copilot.gen.util import (
    month_range,
    month_to_last_date,
    months_between,
    random_date_in_month,
    weighted_sample_without_replacement,
)


def _churn_factor(customer_id: str, segment: str, month: str, dormant_ids: set) -> float:
    """Story 3: order-count multiplier for a customer in a given month.
    Demand-side only — see module docstring."""
    if segment == C.CHURN_SEGMENT:
        msd = months_between(C.CHURN_DECAY_START, month)
        if msd < 0:
            return 1.0
        if customer_id in dormant_ids:
            span = months_between(C.CHURN_DECAY_START, C.CHURN_DORMANT_BY_MONTH)
            if msd >= span:
                return 0.0
            return max(0.0, 1 - msd / span)
        return max(C.CHURN_ACTIVE_CUSTOMER_FLOOR_RATE, (1 - C.TRAD_TRADE_DECAY_RATE) ** msd)
    if segment == C.CHURN_COUNTER_SEGMENT:
        msd = months_between(C.CHURN_DECAY_START, month)
        if msd < 0:
            return 1.0
        return (1 + C.MODERN_TRADE_GROWTH_RATE) ** msd
    return 1.0


def _category_time_factor(category: str, month: str) -> float:
    """Story 2's demand-side half: home_care sell-through declines, its
    food_beverage counter grows mildly. Feeds order-line SKU-selection
    weight, which is what ultimately drives realized qty_delivered per
    category per month (and therefore the trailing-90-day demand series
    days_of_cover is computed against downstream)."""
    if category == C.SLOWMOVE_CATEGORY:
        msd = months_between(C.SLOWMOVE_DEMAND_DECLINE_START, month)
        if msd < 0:
            return 1.0
        return (1 - C.SLOWMOVE_DEMAND_DECLINE_RATE) ** msd
    if category == C.SLOWMOVE_COUNTER_CATEGORY:
        msd = months_between(C.SLOWMOVE_DEMAND_DECLINE_START, month)
        if msd < 0:
            return 1.0
        return (1 + C.SLOWMOVE_COUNTER_DEMAND_GROWTH_RATE) ** msd
    return 1.0


def _seasonal_delta(month: str) -> float:
    cal_month = int(month.split("-")[1])
    phase = 2 * math.pi * (cal_month - C.SEASONALITY_PEAK_MONTH) / 12
    return -C.SEASONALITY_AMPLITUDE * math.cos(phase)


def _is_story1_affected_line(sku_row: dict, dc: str, month: str) -> bool:
    return (
        sku_row["primary_supplier_id"] == C.ANADOLU_SUPPLIER_ID
        and sku_row["category"] in C.STORY1_AFFECTED_CATEGORIES
        and dc == C.STORY1_AFFECTED_DC
        and month in C.STORY1_MONTH_SEVERITY
    )


def build_orders_and_lines(rng: np.random.Generator, customers_df: pd.DataFrame, skus_df: pd.DataFrame):
    months = month_range(C.WINDOW_START_MONTH, C.WINDOW_END_MONTH)

    customers = customers_df.to_dict("records")
    for c in customers:
        c["home_dc"] = C.EMIRATE_TO_DC[c["emirate"]]

    skus = skus_df.to_dict("records")
    n_skus = len(skus)
    sku_abc = [s["abc_class"] for s in skus]
    sku_category = [s["category"] for s in skus]

    trad_ids = [c["customer_id"] for c in customers if c["segment"] == C.CHURN_SEGMENT]
    dormant_ids = set(
        trad_ids[i] for i in rng.choice(len(trad_ids), size=C.CHURN_DORMANT_CUSTOMER_COUNT, replace=False)
    )

    # Precompute sku sampling weights per (segment, month): ABC popularity *
    # segment/category affinity * category time factor (Story 2's demand
    # curve). 4 segments * 24 months = 96 combos, computed once.
    weight_cache: dict[tuple[str, str], list[float]] = {}
    for segment in C.SEGMENTS:
        for month in months:
            weights = []
            for s in skus:
                affinity = C.SEGMENT_CATEGORY_AFFINITY.get((segment, s["category"]), C.DEFAULT_CATEGORY_AFFINITY)
                w = C.ABC_LINE_POPULARITY_WEIGHT[s["abc_class"]] * affinity * _category_time_factor(s["category"], month)
                weights.append(w)
            weight_cache[(segment, month)] = weights

    order_rows = []
    line_rows = []
    order_seq = 0

    for c in customers:
        base_lambda = C.SEGMENT_BASE_MONTHLY_ORDERS_PER_CUSTOMER[c["segment"]] * C.GLOBAL_ORDER_VOLUME_SCALE
        for month in months:
            factor = _churn_factor(c["customer_id"], c["segment"], month, dormant_ids)
            noise = float(rng.normal(1.0, 0.08))
            noise = max(0.5, noise)
            lam = max(0.0, base_lambda * factor * noise)
            n_orders_this_cell = int(rng.poisson(lam)) if lam > 0 else 0

            is_last_window_month = month == C.WINDOW_END_MONTH
            max_day = 20 if is_last_window_month else None

            weights = weight_cache[(c["segment"], month)]

            for _ in range(n_orders_this_cell):
                order_seq += 1
                order_id = f"ORD-{order_seq:0{C.ORDER_ID_WIDTH}d}"

                dc = c["home_dc"]
                if rng.random() < C.CROSS_DC_SHIP_RATE:
                    dc = [x for x in C.DC_CODES if x != dc][0]

                order_date = pd.Timestamp(random_date_in_month(rng, month, max_day=max_day))
                lead_days = int(rng.integers(C.REQUESTED_LEAD_DAYS_MIN, C.REQUESTED_LEAD_DAYS_MAX + 1))
                requested_delivery_date = order_date + pd.Timedelta(days=lead_days)

                k = int(rng.choice(C.ORDER_LINE_COUNT_CHOICES, p=np.asarray(C.ORDER_LINE_COUNT_WEIGHTS) / sum(C.ORDER_LINE_COUNT_WEIGHTS)))
                chosen_idx = weighted_sample_without_replacement(rng, n_skus, weights, k)

                chosen_lines = []
                order_touched_by_story1 = False
                for idx in chosen_idx:
                    s = skus[idx]
                    affected = _is_story1_affected_line(s, dc, month)
                    order_touched_by_story1 = order_touched_by_story1 or affected
                    qty_ordered = max(1, round(float(rng.uniform(C.ORDER_QTY_MIN, C.ORDER_QTY_MAX)) * C.ABC_QTY_MULTIPLIER[s["abc_class"]]))
                    unit_price_aed = round(s["base_unit_price_aed"] * float(rng.uniform(0.98, 1.02)), 2)
                    chosen_lines.append({"sku": s, "affected": affected, "qty_ordered": qty_ordered, "unit_price_aed": unit_price_aed})

                severity = C.STORY1_MONTH_SEVERITY.get(month, 0.0) if order_touched_by_story1 else 0.0

                delta = _seasonal_delta(month)
                p_on_time = min(1.0, max(0.0, C.BASE_ON_TIME_RATE + delta))
                if severity > 0:
                    p_on_time = min(1.0, max(0.0, p_on_time - C.STORY1_EXTRA_LATE_PROB_PEAK * severity))
                on_time = rng.random() < p_on_time

                p_in_full_month = min(1.0, max(0.0, C.BASE_IN_FULL_RATE + delta))

                for line in chosen_lines:
                    k_lines = len(chosen_lines)
                    p_line_short_base = 1 - p_in_full_month ** (1 / k_lines)
                    if line["affected"]:
                        p_line_short = min(0.95, p_line_short_base + C.STORY1_EXTRA_SHORT_PROB_PEAK * severity)
                    else:
                        p_line_short = p_line_short_base

                    is_short = rng.random() < p_line_short
                    qty_ordered = line["qty_ordered"]
                    if is_short:
                        if line["affected"]:
                            withhold_frac = float(rng.uniform(C.STORY1_AFFECTED_SHORT_FRACTION_MIN, C.STORY1_AFFECTED_SHORT_FRACTION_MAX))
                        elif rng.random() < C.ZERO_DELIVERY_SHARE_OF_SHORT:
                            withhold_frac = 1.0
                        else:
                            withhold_frac = float(rng.uniform(C.SHORT_SHIP_FRACTION_MIN, C.SHORT_SHIP_FRACTION_MAX))
                        shortfall = max(1, round(qty_ordered * withhold_frac))
                        qty_delivered = max(0, qty_ordered - shortfall)
                    else:
                        qty_delivered = qty_ordered

                    line["qty_delivered"] = qty_delivered

                if on_time:
                    early_days = int(rng.integers(0, 2))
                    actual_delivery_date = requested_delivery_date - pd.Timedelta(days=early_days)
                    if actual_delivery_date < order_date:
                        actual_delivery_date = order_date
                else:
                    late_days = int(rng.integers(C.LATE_DELAY_DAYS_MIN, C.LATE_DELAY_DAYS_MAX + 1))
                    actual_delivery_date = requested_delivery_date + pd.Timedelta(days=late_days)

                window_end_ts = pd.Timestamp(month_to_last_date(C.WINDOW_END_MONTH))
                if actual_delivery_date > window_end_ts:
                    actual_delivery_date = window_end_ts

                order_value_aed = 0.0
                for line in chosen_lines:
                    line_value_aed = round(line["qty_ordered"] * line["unit_price_aed"], 2)
                    order_value_aed += line_value_aed
                    line_rows.append({
                        "order_id": order_id,
                        "sku_id": line["sku"]["sku_id"],
                        "qty_ordered": line["qty_ordered"],
                        "qty_delivered": line["qty_delivered"],
                        "unit_price_aed": line["unit_price_aed"],
                        "line_value_aed": line_value_aed,
                    })
                order_value_aed = round(order_value_aed, 2)

                order_rows.append({
                    "order_id": order_id,
                    "customer_id": c["customer_id"],
                    "dc": dc,
                    "order_date": order_date,
                    "requested_delivery_date": requested_delivery_date,
                    "actual_delivery_date": actual_delivery_date,
                    "order_value_aed": order_value_aed,
                })

    orders_df = pd.DataFrame(order_rows)
    lines_df = pd.DataFrame(line_rows)
    return orders_df, lines_df
