"""Shipments (supplier -> dc replenishment) and inventory_snapshots.

Story 1's supply-side half lives in build_shipments: SUP-07 shipments
promised in Feb/Mar 2026 arrive 70-85 days late instead of the standard 42,
and are disproportionately AUH-bound.

Story 2 lives in build_inventory_snapshots: home_care's days_of_cover is set
from an explicit target-days-of-cover curve (55 -> 105 days, linear over the
Sep-2025..Jun-2026 span) multiplied by that sku/dc/month's REALIZED trailing
90-day demand — see the long comment on SLOWMOVE_DOC_TARGET_START_DAYS in
copilot/constants.py for why a target curve is used instead of back-solving
from independently-locked demand/purchasing rates. food_beverage gets a
symmetric (milder) shrink on its own baseline days-of-cover target, sized
during calibration so total inventory value stays near flat.
"""

import pandas as pd

from copilot import constants as C
from copilot.gen.util import month_range, month_to_first_date, month_to_last_date, months_between, random_date_in_month


def build_shipments(rng, suppliers_df: pd.DataFrame) -> pd.DataFrame:
    suppliers = suppliers_df.to_dict("records")
    months = month_range(C.WINDOW_START_MONTH, C.WINDOW_END_MONTH)
    window_start_ts = pd.Timestamp(month_to_first_date(C.WINDOW_START_MONTH))
    window_end_ts = pd.Timestamp(month_to_last_date(C.WINDOW_END_MONTH))

    rows = []
    seq = 0
    for supplier in suppliers:
        sid = supplier["supplier_id"]
        lead = supplier["standard_lead_time_days"]
        is_anadolu = sid == C.ANADOLU_SUPPLIER_ID
        p_auh = C.STORY1_ANADOLU_AUH_SHIPMENT_SHARE if is_anadolu else C.DEFAULT_SUPPLIER_DC_SHARE

        for month in months:
            mean_total = C.SHIPMENTS_PER_SUPPLIER_DC_MONTH_MEAN * 2 * C.SHIPMENT_VOLUME_SCALE
            total = int(rng.poisson(mean_total))
            n_auh = int(rng.binomial(total, p_auh)) if total > 0 else 0
            n_jeb = total - n_auh

            for dc, n in (("AUH", n_auh), ("JEB", n_jeb)):
                delayed = is_anadolu and month in C.ANADOLU_DELAY_SHIPMENTS_DUE_MONTHS
                for _ in range(n):
                    seq += 1
                    shipment_id = f"SHIP-{seq:0{C.SHIPMENT_ID_WIDTH}d}"

                    promised_arrival_date = pd.Timestamp(random_date_in_month(rng, month))
                    jitter_days = int(rng.integers(-C.SHIPMENT_LEAD_JITTER_DAYS, C.SHIPMENT_LEAD_JITTER_DAYS + 1))
                    po_date = promised_arrival_date - pd.Timedelta(days=lead + jitter_days)
                    if po_date < window_start_ts:
                        po_date = window_start_ts
                    if promised_arrival_date < po_date:
                        promised_arrival_date = po_date

                    if delayed:
                        actual_lead = int(rng.integers(C.ANADOLU_DELAY_ACTUAL_LEAD_MIN_DAYS, C.ANADOLU_DELAY_ACTUAL_LEAD_MAX_DAYS + 1))
                        actual_arrival_date = po_date + pd.Timedelta(days=actual_lead)
                    elif rng.random() < C.SHIPMENT_LATE_RATE_BASE:
                        late_days = int(rng.integers(C.SHIPMENT_LATE_DAYS_MIN, C.SHIPMENT_LATE_DAYS_MAX + 1))
                        actual_arrival_date = promised_arrival_date + pd.Timedelta(days=late_days)
                    else:
                        early_days = int(rng.integers(0, 2))
                        actual_arrival_date = promised_arrival_date - pd.Timedelta(days=early_days)

                    if actual_arrival_date > window_end_ts:
                        actual_arrival_date = window_end_ts
                    if actual_arrival_date < po_date:
                        actual_arrival_date = po_date

                    rows.append({
                        "shipment_id": shipment_id,
                        "supplier_id": sid,
                        "dc": dc,
                        "po_date": po_date,
                        "promised_arrival_date": promised_arrival_date,
                        "actual_arrival_date": actual_arrival_date,
                    })
    return pd.DataFrame(rows)


def _home_care_target_doc(month: str) -> float:
    msd = months_between(C.SLOWMOVE_DEMAND_DECLINE_START, month)
    if msd <= 0:
        return C.SLOWMOVE_DOC_TARGET_START_DAYS
    total_ramp = months_between(C.SLOWMOVE_DEMAND_DECLINE_START, C.WINDOW_END_MONTH)
    frac = min(1.0, msd / total_ramp)
    return C.SLOWMOVE_DOC_TARGET_START_DAYS + (C.SLOWMOVE_DOC_TARGET_END_DAYS - C.SLOWMOVE_DOC_TARGET_START_DAYS) * frac


def _counter_target_doc(month: str, base_doc: float) -> float:
    msd = months_between(C.SLOWMOVE_DEMAND_DECLINE_START, month)
    if msd <= 0:
        return base_doc
    return base_doc * (1 - C.SLOWMOVE_COUNTER_STOCK_SHRINK_RATE) ** msd


def build_inventory_snapshots(rng, skus_df: pd.DataFrame, orders_df: pd.DataFrame, lines_df: pd.DataFrame) -> pd.DataFrame:
    months = month_range(C.WINDOW_START_MONTH, C.WINDOW_END_MONTH)

    merged = lines_df.merge(orders_df[["order_id", "dc", "order_date"]], on="order_id")
    merged["month"] = merged["order_date"].dt.strftime("%Y-%m")
    monthly_demand = merged.groupby(["sku_id", "dc", "month"])["qty_delivered"].sum()
    demand_lookup = monthly_demand.to_dict()

    month_index = {m: i for i, m in enumerate(months)}

    def trailing_90d_demand(sku_id: str, dc: str, month: str) -> int:
        idx = month_index[month]
        lo = max(0, idx - 2)
        return sum(demand_lookup.get((sku_id, dc, m), 0) for m in months[lo: idx + 1])

    skus = skus_df.to_dict("records")

    rows = []
    for s in skus:
        sku_id = s["sku_id"]
        category = s["category"]
        abc_class = s["abc_class"]
        unit_cost_aed = s["unit_cost_aed"]
        base_doc = C.SNAPSHOT_BASE_DOC_DAYS_BY_CATEGORY[category]

        for dc in C.DC_CODES:
            for month in months:
                demand_90d = trailing_90d_demand(sku_id, dc, month)

                if category == C.SLOWMOVE_CATEGORY:
                    target_doc = _home_care_target_doc(month)
                elif category == C.SLOWMOVE_COUNTER_CATEGORY:
                    target_doc = _counter_target_doc(month, base_doc)
                else:
                    target_doc = base_doc

                if demand_90d > 0:
                    noise = float(rng.uniform(1 - C.SNAPSHOT_ONHAND_NOISE, 1 + C.SNAPSHOT_ONHAND_NOISE))
                    on_hand_qty = max(0, round(target_doc * (demand_90d / 90) * noise))
                else:
                    on_hand_qty = C.SNAPSHOT_ZERO_DEMAND_FALLBACK_QTY_BY_ABC[abc_class]

                on_hand_value_aed = round(on_hand_qty * unit_cost_aed, 2)
                rows.append({
                    "snapshot_month": month,
                    "sku_id": sku_id,
                    "dc": dc,
                    "on_hand_qty": int(on_hand_qty),
                    "on_hand_value_aed": on_hand_value_aed,
                })
    return pd.DataFrame(rows)
