"""Computes the actual, measured effect of each planted story against the
built DuckDB database, and assembles data/stories.json.

Grain rule used throughout (see docs/SPEC.md's supplier-cut grain note from
step 1): a dimension that is single-valued per order (dc, customer_segment)
is measured at ORDER grain; a dimension that can vary line-to-line within one
order (supplier, category) is measured at ORDER-LINE grain. The headline
monthly OTIF figure is order grain, matching fixtures/decomposition_fixture.yaml.

Every query here runs against the tables actually written to
data/mawarid.duckdb — this file proves what got planted, using plain SQL, the
same way tests/test_generator_sanity.py will.
"""

import json

from copilot import constants as C
from copilot.gen.util import months_between


def _order_grain_otif(con, month: str, group_by_sql: str | None = None) -> dict:
    base = f"""
        WITH order_flags AS (
            SELECT o.order_id,
                   {group_by_sql + ' AS grp,' if group_by_sql else ''}
                   (o.actual_delivery_date <= o.requested_delivery_date) AS on_time,
                   NOT EXISTS (
                       SELECT 1 FROM order_lines ol
                       WHERE ol.order_id = o.order_id AND ol.qty_delivered < ol.qty_ordered
                   ) AS in_full
            FROM orders o
            {"JOIN customers c ON c.customer_id = o.customer_id" if group_by_sql and "c." in group_by_sql else ""}
            WHERE strftime(o.order_date, '%Y-%m') = '{month}'
        )
        SELECT {"grp," if group_by_sql else ""} AVG(CASE WHEN on_time AND in_full THEN 100.0 ELSE 0.0 END) AS otif_pct,
               COUNT(*) AS n
        FROM order_flags
        {"GROUP BY grp" if group_by_sql else ""}
    """
    rows = con.execute(base).fetchall()
    if group_by_sql:
        return {r[0]: {"otif_pct": r[1], "n": r[2]} for r in rows}
    return {"otif_pct": rows[0][0], "n": rows[0][1]}


def _line_grain_otif_by(con, month: str, group_col: str) -> dict:
    sql = f"""
        SELECT {group_col} AS grp,
               COUNT(*) AS line_count,
               AVG(CASE WHEN o.actual_delivery_date <= o.requested_delivery_date
                         AND ol.qty_delivered = ol.qty_ordered
                    THEN 100.0 ELSE 0.0 END) AS otif_pct
        FROM order_lines ol
        JOIN orders o ON o.order_id = ol.order_id
        JOIN skus s ON s.sku_id = ol.sku_id
        WHERE strftime(o.order_date, '%Y-%m') = '{month}'
        GROUP BY grp
    """
    rows = con.execute(sql).fetchall()
    return {r[0]: {"line_count": r[1], "otif_pct": r[2]} for r in rows}


def _category_days_of_cover_and_value(con, category: str, month: str) -> dict:
    sql = f"""
        WITH cat_month_demand AS (
            SELECT s.category, strftime(o.order_date, '%Y-%m') AS month, SUM(ol.qty_delivered) AS demand
            FROM order_lines ol
            JOIN orders o ON o.order_id = ol.order_id
            JOIN skus s ON s.sku_id = ol.sku_id
            WHERE s.category = '{category}'
            GROUP BY 1, 2
        ),
        trailing_demand AS (
            SELECT category, month,
                   SUM(demand) OVER (PARTITION BY category ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS demand_90d
            FROM cat_month_demand
        ),
        inv AS (
            SELECT s.category, i.snapshot_month AS month, SUM(i.on_hand_qty) AS qty, SUM(i.on_hand_value_aed) AS value
            FROM inventory_snapshots i
            JOIN skus s ON s.sku_id = i.sku_id
            WHERE s.category = '{category}'
            GROUP BY 1, 2
        )
        SELECT inv.qty, inv.value, trailing_demand.demand_90d,
               inv.qty / (trailing_demand.demand_90d / 90.0) AS days_of_cover
        FROM inv JOIN trailing_demand ON inv.category = trailing_demand.category AND inv.month = trailing_demand.month
        WHERE inv.month = '{month}'
    """
    row = con.execute(sql).fetchone()
    return {"on_hand_qty": row[0], "on_hand_value_aed": row[1], "demand_90d": row[2], "days_of_cover": row[3]}


def _total_inventory_value(con, month: str) -> float:
    sql = f"SELECT SUM(on_hand_value_aed) FROM inventory_snapshots WHERE snapshot_month = '{month}'"
    return con.execute(sql).fetchone()[0]


def _monthly_order_stats(con, segment: str, month: str) -> dict:
    sql = f"""
        SELECT COUNT(*), COALESCE(SUM(o.order_value_aed), 0)
        FROM orders o JOIN customers c ON c.customer_id = o.customer_id
        WHERE c.segment = '{segment}' AND strftime(o.order_date, '%Y-%m') = '{month}'
    """
    row = con.execute(sql).fetchone()
    return {"order_count": row[0], "revenue_aed": row[1]}


def _total_revenue(con, months: list[str]) -> float:
    placeholders = ", ".join(f"'{m}'" for m in months)
    sql = f"SELECT COALESCE(SUM(order_value_aed), 0) FROM orders WHERE strftime(order_date, '%Y-%m') IN ({placeholders})"
    return con.execute(sql).fetchone()[0]


def _dormant_customer_check(con) -> dict:
    sql = f"""
        SELECT c.customer_id, COUNT(o.order_id) AS n
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.customer_id
            AND strftime(o.order_date, '%Y-%m') BETWEEN '2026-04' AND '2026-06'
        WHERE c.segment = '{C.CHURN_SEGMENT}'
        GROUP BY c.customer_id
    """
    rows = con.execute(sql).fetchall()
    zero_order_customers = sum(1 for _, n in rows if n == 0)
    return {"traditional_trade_customers": len(rows), "zero_order_in_q2_2026": zero_order_customers}


def _band_ok(value, band) -> bool:
    return band[0] <= value <= band[1]


def compute_and_write_stories(con) -> dict:
    effects = []

    # ---------------------------------------------------------------- Story 1
    feb = _order_grain_otif(con, "2026-02")
    mar = _order_grain_otif(con, "2026-03")
    apr = _order_grain_otif(con, "2026-04")
    may = _order_grain_otif(con, "2026-05")

    sup_feb = _line_grain_otif_by(con, "2026-02", "s.primary_supplier_id")
    sup_mar = _line_grain_otif_by(con, "2026-03", "s.primary_supplier_id")
    all_suppliers = set(sup_feb) | set(sup_mar)
    total_feb_lines = sum(v["line_count"] for v in sup_feb.values())
    total_mar_lines = sum(v["line_count"] for v in sup_mar.values())
    line_grain_otif_feb = sum(v["otif_pct"] * v["line_count"] for v in sup_feb.values()) / total_feb_lines
    line_grain_otif_mar = sum(v["otif_pct"] * v["line_count"] for v in sup_mar.values()) / total_mar_lines
    line_grain_delta = line_grain_otif_mar - line_grain_otif_feb

    contributions = {}
    for sup in all_suppliers:
        share_feb = sup_feb.get(sup, {"line_count": 0, "otif_pct": 0})["line_count"] / total_feb_lines
        rate_feb = sup_feb.get(sup, {"otif_pct": 0})["otif_pct"]
        share_mar = sup_mar.get(sup, {"line_count": 0, "otif_pct": 0})["line_count"] / total_mar_lines
        rate_mar = sup_mar.get(sup, {"otif_pct": 0})["otif_pct"]
        contributions[sup] = (share_mar * rate_mar) - (share_feb * rate_feb)
    sup07_contribution = contributions.get(C.ANADOLU_SUPPLIER_ID, 0.0)
    sup07_share_of_delta = sup07_contribution / line_grain_delta if line_grain_delta != 0 else 0.0

    dc_feb = _order_grain_otif(con, "2026-02", "o.dc")
    dc_mar = _order_grain_otif(con, "2026-03", "o.dc")
    dc_drop = {dc: dc_feb[dc]["otif_pct"] - dc_mar[dc]["otif_pct"] for dc in dc_feb if dc in dc_mar}
    auh_share_of_dc_drop = dc_drop.get(C.STORY1_AFFECTED_DC, 0) / sum(dc_drop.values()) if sum(dc_drop.values()) else 0

    cat_feb = _line_grain_otif_by(con, "2026-02", "s.category")
    cat_mar = _line_grain_otif_by(con, "2026-03", "s.category")
    cat_drop = {cat: cat_feb[cat]["otif_pct"] - cat_mar[cat]["otif_pct"] for cat in cat_feb if cat in cat_mar}
    cat_drop_sorted = sorted(cat_drop.items(), key=lambda kv: kv[1], reverse=True)
    top2_categories = [c for c, _ in cat_drop_sorted[:2]]

    seg_feb = _order_grain_otif(con, "2026-02", "c.segment")
    seg_mar = _order_grain_otif(con, "2026-03", "c.segment")
    seg_drop = {seg: seg_feb[seg]["otif_pct"] - seg_mar[seg]["otif_pct"] for seg in seg_feb if seg in seg_mar}
    seg_spread = max(seg_drop.values()) - min(seg_drop.values())

    effects.append({
        "story": 1, "metric": "otif_pct", "slice": "month=2026-02 (baseline)",
        "expected": list(C.STORY1_FEBRUARY_BASELINE_OTIF_BAND), "actual": feb["otif_pct"],
        "pass": _band_ok(feb["otif_pct"], C.STORY1_FEBRUARY_BASELINE_OTIF_BAND),
    })
    effects.append({
        "story": 1, "metric": "otif_pct", "slice": "month=2026-03",
        "expected": list(C.STORY1_MARCH_OTIF_BAND), "actual": mar["otif_pct"],
        "pass": _band_ok(mar["otif_pct"], C.STORY1_MARCH_OTIF_BAND),
    })
    effects.append({
        "story": 1, "metric": "otif_pct", "slice": "month=2026-04 (recovery)",
        "expected": list(C.STORY1_APRIL_OTIF_BAND), "actual": apr["otif_pct"],
        "pass": _band_ok(apr["otif_pct"], C.STORY1_APRIL_OTIF_BAND),
    })
    effects.append({
        "story": 1, "metric": "otif_pct", "slice": "month=2026-05 (recovered)",
        "expected": list(C.STORY1_MAY_OTIF_BAND), "actual": may["otif_pct"],
        "pass": _band_ok(may["otif_pct"], C.STORY1_MAY_OTIF_BAND),
    })
    effects.append({
        "story": 1, "metric": "otif_pct_line_grain_delta_share_by_supplier", "slice": "SUP-07, 2026-02 -> 2026-03",
        "expected": list(C.STORY1_SUP07_LINE_DELTA_SHARE_BAND), "actual": sup07_share_of_delta,
        "pass": _band_ok(sup07_share_of_delta, C.STORY1_SUP07_LINE_DELTA_SHARE_BAND),
    })
    effects.append({
        "story": 1, "metric": "otif_pct_dc_drop_share", "slice": f"dc={C.STORY1_AFFECTED_DC}, 2026-02 -> 2026-03",
        "expected": ">0.5 (AUH explains most of the dc-level drop)", "actual": auh_share_of_dc_drop,
        "pass": auh_share_of_dc_drop > 0.5,
    })
    effects.append({
        "story": 1, "metric": "otif_pct_category_cut_top2", "slice": "2026-02 -> 2026-03",
        "expected": sorted(C.STORY1_AFFECTED_CATEGORIES), "actual": sorted(top2_categories),
        "pass": set(top2_categories) == set(C.STORY1_AFFECTED_CATEGORIES),
    })
    effects.append({
        "story": 1, "metric": "otif_pct_segment_cut_spread_pp", "slice": "2026-02 -> 2026-03",
        "expected": f"<= {C.STORY1_SEGMENT_CUT_MAX_SPREAD_PP} pp spread across segments", "actual": seg_spread,
        "pass": seg_spread <= C.STORY1_SEGMENT_CUT_MAX_SPREAD_PP,
    })

    # ---------------------------------------------------------------- Story 2
    hc_start = _category_days_of_cover_and_value(con, C.SLOWMOVE_CATEGORY, C.SLOWMOVE_DEMAND_DECLINE_START)
    hc_end = _category_days_of_cover_and_value(con, C.SLOWMOVE_CATEGORY, C.WINDOW_END_MONTH)
    total_val_start = _total_inventory_value(con, C.SLOWMOVE_DEMAND_DECLINE_START)
    total_val_end = _total_inventory_value(con, C.WINDOW_END_MONTH)
    total_val_drift = abs(total_val_end - total_val_start) / total_val_start

    effects.append({
        "story": 2, "metric": "days_of_cover", "slice": f"category={C.SLOWMOVE_CATEGORY}, month={C.SLOWMOVE_DEMAND_DECLINE_START}",
        "expected": list(C.SLOWMOVE_DOC_START_BAND_DAYS), "actual": hc_start["days_of_cover"],
        "pass": _band_ok(hc_start["days_of_cover"], C.SLOWMOVE_DOC_START_BAND_DAYS),
    })
    effects.append({
        "story": 2, "metric": "days_of_cover", "slice": f"category={C.SLOWMOVE_CATEGORY}, month={C.WINDOW_END_MONTH}",
        "expected": list(C.SLOWMOVE_DOC_END_BAND_DAYS), "actual": hc_end["days_of_cover"],
        "pass": _band_ok(hc_end["days_of_cover"], C.SLOWMOVE_DOC_END_BAND_DAYS),
    })
    effects.append({
        "story": 2, "metric": "inventory_value_aed", "slice": f"category={C.SLOWMOVE_CATEGORY}, month={C.SLOWMOVE_DEMAND_DECLINE_START}",
        "expected": list(C.SLOWMOVE_INVENTORY_VALUE_START_BAND_AED), "actual": hc_start["on_hand_value_aed"],
        "pass": _band_ok(hc_start["on_hand_value_aed"], C.SLOWMOVE_INVENTORY_VALUE_START_BAND_AED),
    })
    effects.append({
        "story": 2, "metric": "inventory_value_aed", "slice": f"category={C.SLOWMOVE_CATEGORY}, month={C.WINDOW_END_MONTH}",
        "expected": list(C.SLOWMOVE_INVENTORY_VALUE_END_BAND_AED), "actual": hc_end["on_hand_value_aed"],
        "pass": _band_ok(hc_end["on_hand_value_aed"], C.SLOWMOVE_INVENTORY_VALUE_END_BAND_AED),
    })
    effects.append({
        "story": 2, "metric": "total_inventory_value_drift", "slice": f"{C.SLOWMOVE_DEMAND_DECLINE_START} -> {C.WINDOW_END_MONTH}, all categories",
        "expected": f"<= {C.SLOWMOVE_TOTAL_INVENTORY_FLAT_TOLERANCE}", "actual": total_val_drift,
        "pass": total_val_drift <= C.SLOWMOVE_TOTAL_INVENTORY_FLAT_TOLERANCE,
    })

    # ---------------------------------------------------------------- Story 3
    trad_start = _monthly_order_stats(con, C.CHURN_SEGMENT, C.CHURN_DECAY_START)
    trad_end = _monthly_order_stats(con, C.CHURN_SEGMENT, C.WINDOW_END_MONTH)
    modern_start = _monthly_order_stats(con, C.CHURN_COUNTER_SEGMENT, C.CHURN_DECAY_START)
    modern_end = _monthly_order_stats(con, C.CHURN_COUNTER_SEGMENT, C.WINDOW_END_MONTH)
    dormant = _dormant_customer_check(con)

    early_months = [C.WINDOW_START_MONTH, "2024-08", "2024-09"]
    late_months = ["2026-04", "2026-05", "2026-06"]
    revenue_early = _total_revenue(con, early_months)
    revenue_late = _total_revenue(con, late_months)
    revenue_drift = abs(revenue_late - revenue_early) / revenue_early

    trad_decline_ratio = trad_end["order_count"] / trad_start["order_count"] if trad_start["order_count"] else None
    modern_growth_ratio = modern_end["order_count"] / modern_start["order_count"] if modern_start["order_count"] else None

    effects.append({
        "story": 3, "metric": "order_count_decline_ratio", "slice": f"segment={C.CHURN_SEGMENT}, {C.CHURN_DECAY_START} -> {C.WINDOW_END_MONTH}",
        "expected": "< 1.0 (declining)", "actual": trad_decline_ratio,
        "pass": trad_decline_ratio is not None and trad_decline_ratio < 1.0,
    })
    effects.append({
        "story": 3, "metric": "order_count_growth_ratio", "slice": f"segment={C.CHURN_COUNTER_SEGMENT}, {C.CHURN_DECAY_START} -> {C.WINDOW_END_MONTH}",
        "expected": "> 1.0 (growing)", "actual": modern_growth_ratio,
        "pass": modern_growth_ratio is not None and modern_growth_ratio > 1.0,
    })
    effects.append({
        "story": 3, "metric": "dormant_customer_count", "slice": f"segment={C.CHURN_SEGMENT}, Q2 2026",
        "expected": C.CHURN_DORMANT_CUSTOMER_COUNT, "actual": dormant["zero_order_in_q2_2026"],
        "pass": dormant["zero_order_in_q2_2026"] == C.CHURN_DORMANT_CUSTOMER_COUNT,
    })
    effects.append({
        "story": 3, "metric": "total_revenue_drift", "slice": f"{'/'.join(early_months)} vs {'/'.join(late_months)}, all segments",
        "expected": "<= 0.15", "actual": revenue_drift,
        "pass": revenue_drift <= 0.15,
    })

    stories_doc = {
        "generated_by": "data/generate.py",
        "seed": C.SEED,
        "stories": [
            {
                "story": 1,
                "name": "March 2026 OTIF drop (Anadolu / SUP-07 shipment delay)",
                "planted": (
                    "SUP-07 (Anadolu Consumer Goods) shipments promised Feb-Mar 2026 arrive "
                    "70-85 days late instead of the standard 42, disproportionately hitting AUH "
                    "(most Anadolu volume routed there). AUH orders containing home_care/"
                    "personal_care SKUs sourced from SUP-07 fail in-full and, less often, on-time "
                    "through the month, with severity peaking in March and fading by May."
                ),
                "constants_used": [
                    "ANADOLU_DELAY_ACTUAL_LEAD_MIN_DAYS", "ANADOLU_DELAY_ACTUAL_LEAD_MAX_DAYS",
                    "ANADOLU_DELAY_SHIPMENTS_DUE_MONTHS", "STORY1_AFFECTED_DC",
                    "STORY1_ANADOLU_AUH_SHIPMENT_SHARE", "STORY1_AFFECTED_CATEGORIES",
                    "STORY1_MONTH_SEVERITY", "STORY1_EXTRA_SHORT_PROB_PEAK", "STORY1_EXTRA_LATE_PROB_PEAK",
                ],
            },
            {
                "story": 2,
                "name": "home_care slow-moving build",
                "planted": (
                    "home_care sell-through declines ~1.5%/month from 2025-09 while purchasing "
                    "holds flat, so days_of_cover climbs from ~55 to ~105 and inventory value from "
                    "~AED 9M to ~AED 14M by 2026-06. food_beverage inventory tightens over the same "
                    "period so TOTAL inventory value stays near flat, hiding the problem in the "
                    "headline number."
                ),
                "constants_used": [
                    "SLOWMOVE_DEMAND_DECLINE_START", "SLOWMOVE_DEMAND_DECLINE_RATE",
                    "SLOWMOVE_DOC_TARGET_START_DAYS", "SLOWMOVE_DOC_TARGET_END_DAYS",
                    "SLOWMOVE_COUNTER_STOCK_SHRINK_RATE",
                ],
            },
            {
                "story": 3,
                "name": "traditional_trade quiet churn",
                "planted": (
                    "traditional_trade order count declines ~2.5%/month per customer from 2025-10 "
                    "across all 30 traditional_trade customers, with 8 of them fully dormant by "
                    "2026-04. modern_trade order count grows ~1.5%/month over the same period, "
                    "offsetting revenue. Demand-side only: delivery-outcome logic never sees this "
                    "overlay, so it cannot leak into Story 1's Feb-Mar 2026 decomposition."
                ),
                "constants_used": [
                    "CHURN_DECAY_START", "TRAD_TRADE_DECAY_RATE", "MODERN_TRADE_GROWTH_RATE",
                    "CHURN_DORMANT_CUSTOMER_COUNT", "CHURN_DORMANT_BY_MONTH", "CHURN_ACTIVE_CUSTOMER_FLOOR_RATE",
                ],
            },
        ],
        "effects": effects,
    }

    with open(C.STORIES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(stories_doc, f, indent=2, default=float)

    return stories_doc
