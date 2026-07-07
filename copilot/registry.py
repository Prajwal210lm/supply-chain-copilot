"""The metric registry: one record per catalog metric, single source of
truth for its meaning, its SQL, and where it can be cut.

Every other module (validate.py for compatibility/decomposability checks,
compile.py for SQL generation, decompose.py for which grain a supplier cut
needs) reads this registry. No metric semantics — no numerator formula, no
compatible-dimension list, no decomposability flag — may be redefined or
hardcoded in any other module. If a rule about what a metric means needs to
change, this is the only file that changes.

## Grain model

Most metrics have exactly one SQL shape ("base relation") that works for
every dimension cut they support. Two families need a second shape:

- The OTIF family (otif_pct, on_time_pct, in_full_pct) defaults to ORDER
  grain (docs/SPEC.md's pinned convention, confirmed by
  fixtures/decomposition_fixture.yaml: Feb/Mar otif_pct as a plain
  metric_query is order-grain 75.0/50.0, not the line-grain 70.0/50.0).
  But an order's lines can carry different suppliers or different
  categories, so a cut by either one is only meaningful at LINE grain
  (docs/SPEC.md's supplier-cut grain note gives the reasoning for
  supplier; the same reasoning applies verbatim to category, since both
  are per-line SKU attributes, so this registry extends the line-grain
  variant to both triggers). fill_rate_pct is already line-grain for
  every cut by definition, so it needs no second relation.
- order_count and avg_order_value default to ORDER grain (dc/emirate/
  customer_segment are order-level, unambiguous) but also support a
  category cut, which is per-line. Cutting an additive COUNT or an AVG by
  a per-line attribute means an order that spans two categories is
  attributed to both — documented here, not a bug: it answers "how many
  orders touched category X", not "how many orders belong only to X".

## Column contract

Every base_relation_sql is a SQL subquery body (no trailing semicolon,
embeddable as `FROM (\n{base_relation_sql}\n)`) that exposes standardized
column aliases so compile.py never needs per-metric column knowledge:

- period_column: the column compile.py filters/buckets on. period_column_type
  is "date" (a DuckDB DATE, compared against parameter-bound date bounds) or
  "month_str" (inventory_snapshots.snapshot_month, a "YYYY-MM" string,
  compared directly against period.start/period.end).
- dimension_columns: {dimension_name: column_alias} for every dimension the
  relation supports directly (a line_grain_variant, if present, declares its
  own dimension_columns for the dimensions it adds/overrides).

## Numerator/denominator shape

Each is an AggExpr: an aggregate function call (`func`, e.g. "COUNT(*)" or
"SUM(qty_delivered)") plus an optional boolean `condition` evaluated as a
SQL FILTER clause (e.g. "on_time AND in_full"), kept SEPARATE rather than
pre-joined into one opaque string. compile.py needs the pieces apart for
change_decomposition: a single statement computing both periods' numbers
together needs `FILTER (WHERE <condition> AND <period tag>)` — ANDing in a
second condition into an already-formed FILTER clause isn't valid SQL, so
AggExpr.filtered_sql() does the combining once, here, instead of every
caller string-splicing a FILTER clause it didn't build. `.sql` (no extra
condition) is what metric_query/breakdown_query use, since they only ever
filter by WHERE on one period and never need the FILTER form at all.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AggExpr:
    func: str
    condition: str | None = None
    scale: float | None = None  # post-aggregation divisor, e.g. 90.0 for days_of_cover's denominator

    def filtered_sql(self, extra_condition: str | None = None) -> str:
        conditions = [c for c in (self.condition, extra_condition) if c]
        base = self.func if not conditions else self.func + " FILTER (WHERE " + " AND ".join(conditions) + ")"
        if self.scale is not None:
            base = "(" + base + ") / " + repr(self.scale)
        return base

    @property
    def sql(self) -> str:
        return self.filtered_sql(None)


@dataclass(frozen=True)
class LineGrainVariant:
    """An alternate relation used when the breakdown/decomposition dimension
    is one of `triggers` — see the grain model in this module's docstring."""
    base_relation_sql: str
    numerator: AggExpr
    denominator: AggExpr | None
    dimension_columns: dict[str, str]
    triggers: frozenset[str]

    @property
    def numerator_sql(self) -> str:
        return self.numerator.sql

    @property
    def denominator_sql(self) -> str | None:
        return self.denominator.sql if self.denominator else None


@dataclass(frozen=True)
class MetricEntry:
    key: str
    display_name: str
    definition: str
    synonyms: tuple[str, ...]
    disambiguation_note: str | None
    base_relation_sql: str
    numerator: AggExpr
    denominator: AggExpr | None
    dimension_columns: dict[str, str]
    period_column: str
    period_column_type: str  # "date" | "month_str"
    join_path: str
    compatible_dimensions: frozenset[str]
    decomposable: bool
    line_grain_variant: LineGrainVariant | None = field(default=None)

    @property
    def numerator_sql(self) -> str:
        return self.numerator.sql

    @property
    def denominator_sql(self) -> str | None:
        return self.denominator.sql if self.denominator else None


# ---------------------------------------------------------------------------
# Shared SQL fragments — each defined exactly once, reused by reference.
# ---------------------------------------------------------------------------

# The OTIF family's default (order-grain) relation. in_full's NOT EXISTS
# fragment against short lines lives here, and only here.
_ORDER_GRAIN_OTIF_RELATION = """
    SELECT
        o.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        (o.actual_delivery_date <= o.requested_delivery_date) AS on_time,
        NOT EXISTS (
            SELECT 1 FROM order_lines ol2
            WHERE ol2.order_id = o.order_id AND ol2.qty_delivered < ol2.qty_ordered
        ) AS in_full
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
"""

_ORDER_GRAIN_OTIF_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment",
}

# The OTIF family's line-grain variant, triggered by category or supplier.
# Joins customers too (not just skus) even though dc/emirate/customer_segment
# are already order-safe — a query can combine a supplier or category filter
# WITH a dc/emirate/segment filter, and once the line-grain relation is
# selected for one dimension it must not lose coverage of the others.
_LINE_GRAIN_OTIF_RELATION = """
    SELECT
        ol.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        s.category AS category,
        s.primary_supplier_id AS supplier,
        (o.actual_delivery_date <= o.requested_delivery_date) AS on_time,
        (ol.qty_delivered = ol.qty_ordered) AS line_in_full
    FROM order_lines ol
    JOIN orders o ON o.order_id = ol.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN skus s ON s.sku_id = ol.sku_id
"""

_LINE_GRAIN_OTIF_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment",
    "category": "category", "supplier": "supplier",
}

# fill_rate_pct and revenue and stockout_count all need the same
# order+customer+sku join at line grain; each still gets its own constant
# (their numerator/denominator differ) but the join shape is written once
# per metric for clarity rather than shared, since DRYing SQL text across
# unrelated metrics would couple them for no reason.
_LINE_GRAIN_FULL_RELATION = """
    SELECT
        ol.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        s.category AS category,
        s.primary_supplier_id AS supplier,
        ol.qty_ordered AS qty_ordered,
        ol.qty_delivered AS qty_delivered,
        (ol.qty_delivered * ol.unit_price_aed) AS line_revenue,
        (ol.qty_delivered = 0) AS is_stockout
    FROM order_lines ol
    JOIN orders o ON o.order_id = ol.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN skus s ON s.sku_id = ol.sku_id
"""

_LINE_GRAIN_FULL_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment",
    "category": "category", "supplier": "supplier",
}

_ORDER_GRAIN_COUNT_RELATION = """
    SELECT
        o.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        o.order_value_aed AS order_value_aed
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
"""

_ORDER_GRAIN_COUNT_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment",
}

# avg_order_value's default (order-grain) relation. Pinned by
# fixtures/decomposition_fixture.yaml's own worksheet — avg_order_value_aed
# is computed as revenue_aed / order_count (DELIVERED value, the same basis
# as the revenue metric), not orders.order_value_aed (booked/ordered
# value). A correlated subquery per order keeps this a simple order-grain
# relation rather than needing a GROUP BY layer underneath it.
_ORDER_GRAIN_DELIVERED_VALUE_RELATION = """
    SELECT
        o.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        (
            SELECT SUM(ol.qty_delivered * ol.unit_price_aed)
            FROM order_lines ol WHERE ol.order_id = o.order_id
        ) AS delivered_value
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
"""

_ORDER_GRAIN_DELIVERED_VALUE_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment",
}

# avg_order_value's category cut: one row per (order, category) pair the
# order touches, carrying the order's full DELIVERED value (same
# multi-attribution reasoning as order_count's category cut below).
_LINE_GRAIN_DELIVERED_VALUE_RELATION = """
    SELECT DISTINCT
        ol.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        s.category AS category,
        (
            SELECT SUM(ol2.qty_delivered * ol2.unit_price_aed)
            FROM order_lines ol2 WHERE ol2.order_id = ol.order_id
        ) AS delivered_value
    FROM order_lines ol
    JOIN orders o ON o.order_id = ol.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN skus s ON s.sku_id = ol.sku_id
"""

_LINE_GRAIN_DELIVERED_VALUE_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment", "category": "category",
}

# order_count / avg_order_value's category cut: one row per (order, category)
# pair the order touches, carrying the order's full order_value_aed. Joins
# customers too, for the same reason as _LINE_GRAIN_OTIF_RELATION above: a
# category filter can combine with a dc/emirate/segment filter and must not
# lose coverage of them once this relation is selected.
_LINE_GRAIN_COUNT_RELATION = """
    SELECT DISTINCT
        ol.order_id,
        o.order_date AS event_date,
        o.dc AS dc,
        c.emirate AS emirate,
        c.segment AS customer_segment,
        s.category AS category,
        o.order_value_aed AS order_value_aed
    FROM order_lines ol
    JOIN orders o ON o.order_id = ol.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN skus s ON s.sku_id = ol.sku_id
"""

_LINE_GRAIN_COUNT_DIMENSION_COLUMNS = {
    "dc": "dc", "emirate": "emirate", "customer_segment": "customer_segment", "category": "category",
}

# days_of_cover / inventory_value: snapshot grain. The trailing-90-day
# demand window is expressed relative to i.snapshot_month, self-contained
# per row — never relative to a query's period bounds — so this fragment is
# reusable unmodified regardless of what period a request asks about.
_SNAPSHOT_RELATION = """
    SELECT
        i.snapshot_month AS month_str,
        i.dc AS dc,
        s.category AS category,
        i.on_hand_value_aed AS on_hand_value_aed,
        i.on_hand_qty AS on_hand_qty,
        (
            SELECT COALESCE(SUM(ol.qty_delivered), 0)
            FROM order_lines ol
            JOIN orders o ON o.order_id = ol.order_id
            WHERE ol.sku_id = i.sku_id
              AND o.dc = i.dc
              AND strftime(o.order_date, '%Y-%m') <= i.snapshot_month
              AND strftime(o.order_date, '%Y-%m') >= strftime(
                    CAST((i.snapshot_month || '-01') AS DATE) - INTERVAL 2 MONTH, '%Y-%m'
              )
        ) AS demand_90d
    FROM inventory_snapshots i
    JOIN skus s ON s.sku_id = i.sku_id
"""

_SNAPSHOT_DIMENSION_COLUMNS = {"dc": "dc", "category": "category"}

_SHIPMENT_RELATION = """
    SELECT
        sh.shipment_id,
        sh.promised_arrival_date AS event_date,
        sh.dc AS dc,
        sh.supplier_id AS supplier,
        DATE_DIFF('day', sh.po_date, sh.actual_arrival_date) AS lead_days
    FROM shipments sh
"""

_SHIPMENT_DIMENSION_COLUMNS = {"dc": "dc", "supplier": "supplier"}

_OTIF_FAMILY_DIMS = frozenset({"month", "week", "dc", "emirate", "category", "customer_segment", "supplier"})
_REVENUE_FAMILY_DIMS = frozenset({"month", "week", "dc", "emirate", "category", "customer_segment"})
_INVENTORY_DIMS = frozenset({"month", "dc", "category"})
_STOCKOUT_DIMS = frozenset({"month", "week", "dc", "category", "supplier"})
_LEAD_TIME_DIMS = frozenset({"month", "dc", "supplier"})

_COUNT_STAR = AggExpr(func="COUNT(*)")


METRICS: dict[str, MetricEntry] = {
    "otif_pct": MetricEntry(
        key="otif_pct",
        display_name="OTIF %",
        definition="Share of orders delivered both on time and in full.",
        synonyms=("otif", "on time in full", "perfect order", "perfect order rate"),
        disambiguation_note=(
            "Requires BOTH on-time delivery AND full quantity — 'on time' alone is on_time_pct, "
            "'complete' alone is in_full_pct, and demand fulfilled by quantity is fill_rate_pct. "
            "Questions about tracking against a target, target attainment, or gap-to-target imply "
            "stored target data, which is not in the catalog. These are out_of_catalog, not plain OTIF queries."
        ),
        base_relation_sql=_ORDER_GRAIN_OTIF_RELATION,
        numerator=AggExpr(func="COUNT(*)", condition="on_time AND in_full"),
        denominator=_COUNT_STAR,
        dimension_columns=_ORDER_GRAIN_OTIF_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="orders JOIN customers (order grain); line-grain variant adds order_lines JOIN skus for category/supplier",
        compatible_dimensions=_OTIF_FAMILY_DIMS,
        decomposable=True,
        line_grain_variant=LineGrainVariant(
            base_relation_sql=_LINE_GRAIN_OTIF_RELATION,
            numerator=AggExpr(func="COUNT(*)", condition="on_time AND line_in_full"),
            denominator=_COUNT_STAR,
            dimension_columns=_LINE_GRAIN_OTIF_DIMENSION_COLUMNS,
            triggers=frozenset({"category", "supplier"}),
        ),
    ),
    "on_time_pct": MetricEntry(
        key="on_time_pct",
        display_name="On-Time %",
        definition="Share of orders delivered by their requested delivery date, regardless of completeness.",
        synonyms=("on time", "on time delivery", "delivery punctuality", "timeliness"),
        disambiguation_note="Timeliness only — ignores whether the order was short-shipped. otif_pct additionally requires in-full.",
        base_relation_sql=_ORDER_GRAIN_OTIF_RELATION,
        numerator=AggExpr(func="COUNT(*)", condition="on_time"),
        denominator=_COUNT_STAR,
        dimension_columns=_ORDER_GRAIN_OTIF_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="orders JOIN customers (order grain); line-grain variant adds order_lines JOIN skus for category/supplier",
        compatible_dimensions=_OTIF_FAMILY_DIMS,
        decomposable=True,
        line_grain_variant=LineGrainVariant(
            base_relation_sql=_LINE_GRAIN_OTIF_RELATION,
            numerator=AggExpr(func="COUNT(*)", condition="on_time"),
            denominator=_COUNT_STAR,
            dimension_columns=_LINE_GRAIN_OTIF_DIMENSION_COLUMNS,
            triggers=frozenset({"category", "supplier"}),
        ),
    ),
    "in_full_pct": MetricEntry(
        key="in_full_pct",
        display_name="In-Full %",
        definition="Share of orders delivered with every line at its full ordered quantity, regardless of timing.",
        synonyms=("in full", "order completeness", "complete orders", "completeness"),
        disambiguation_note="Completeness only — ignores lateness. fill_rate_pct measures the same idea by quantity instead of by whole orders.",
        base_relation_sql=_ORDER_GRAIN_OTIF_RELATION,
        numerator=AggExpr(func="COUNT(*)", condition="in_full"),
        denominator=_COUNT_STAR,
        dimension_columns=_ORDER_GRAIN_OTIF_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="orders JOIN customers (order grain); line-grain variant adds order_lines JOIN skus for category/supplier",
        compatible_dimensions=_OTIF_FAMILY_DIMS,
        decomposable=True,
        line_grain_variant=LineGrainVariant(
            base_relation_sql=_LINE_GRAIN_OTIF_RELATION,
            numerator=AggExpr(func="COUNT(*)", condition="line_in_full"),
            denominator=_COUNT_STAR,
            dimension_columns=_LINE_GRAIN_OTIF_DIMENSION_COLUMNS,
            triggers=frozenset({"category", "supplier"}),
        ),
    ),
    "fill_rate_pct": MetricEntry(
        key="fill_rate_pct",
        display_name="Fill Rate %",
        definition="Share of ordered quantity that was actually delivered, at line grain.",
        synonyms=("fill rate", "quantity fill rate", "case fill rate"),
        disambiguation_note="A quantity ratio, not an order-level binary — a single short-shipped line lowers fill_rate_pct without necessarily changing in_full_pct's order count in the same proportion. Always line grain, for every cut.",
        base_relation_sql=_LINE_GRAIN_FULL_RELATION,
        numerator=AggExpr(func="SUM(qty_delivered)"),
        denominator=AggExpr(func="SUM(qty_ordered)"),
        dimension_columns=_LINE_GRAIN_FULL_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="order_lines JOIN orders JOIN customers JOIN skus (line grain, always)",
        compatible_dimensions=_OTIF_FAMILY_DIMS,
        decomposable=True,
        line_grain_variant=None,
    ),
    "revenue": MetricEntry(
        key="revenue",
        display_name="Revenue",
        definition="Delivered value: sum of qty_delivered times unit_price_aed, at line grain.",
        synonyms=("sales", "revenue", "total sales", "takings", "sales value"),
        disambiguation_note="Delivered value, not the order's booked/ordered value — a short-shipped order contributes less revenue than it was ordered for.",
        base_relation_sql=_LINE_GRAIN_FULL_RELATION,
        numerator=AggExpr(func="SUM(line_revenue)"),
        denominator=None,
        dimension_columns=_LINE_GRAIN_FULL_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="order_lines JOIN orders JOIN customers JOIN skus (line grain)",
        compatible_dimensions=_REVENUE_FAMILY_DIMS,
        decomposable=True,
        line_grain_variant=None,
    ),
    "order_count": MetricEntry(
        key="order_count",
        display_name="Order Count",
        definition="Count of orders placed.",
        synonyms=("orders", "number of orders", "order volume", "how many orders"),
        disambiguation_note=None,
        base_relation_sql=_ORDER_GRAIN_COUNT_RELATION,
        numerator=_COUNT_STAR,
        denominator=None,
        dimension_columns=_ORDER_GRAIN_COUNT_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="orders JOIN customers (order grain); line-grain variant adds order_lines JOIN skus for category (multi-attributed)",
        compatible_dimensions=_REVENUE_FAMILY_DIMS,
        decomposable=True,
        line_grain_variant=LineGrainVariant(
            base_relation_sql=_LINE_GRAIN_COUNT_RELATION,
            numerator=_COUNT_STAR,
            denominator=None,
            dimension_columns=_LINE_GRAIN_COUNT_DIMENSION_COLUMNS,
            triggers=frozenset({"category"}),
        ),
    ),
    "avg_order_value": MetricEntry(
        key="avg_order_value",
        display_name="Average Order Value",
        definition="Revenue divided by order count, based on delivered value, in AED.",
        synonyms=("aov", "average order value", "order size", "typical order value"),
        disambiguation_note="Per-order average, not the total — revenue is the sum across all orders, this is the mean of one order.",
        base_relation_sql=_ORDER_GRAIN_DELIVERED_VALUE_RELATION,
        numerator=AggExpr(func="SUM(delivered_value)"),
        denominator=_COUNT_STAR,
        dimension_columns=_ORDER_GRAIN_DELIVERED_VALUE_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="orders JOIN customers (order grain); line-grain variant adds order_lines JOIN skus for category (multi-attributed)",
        compatible_dimensions=_REVENUE_FAMILY_DIMS,
        decomposable=False,
        line_grain_variant=LineGrainVariant(
            base_relation_sql=_LINE_GRAIN_DELIVERED_VALUE_RELATION,
            numerator=AggExpr(func="SUM(delivered_value)"),
            denominator=_COUNT_STAR,
            dimension_columns=_LINE_GRAIN_DELIVERED_VALUE_DIMENSION_COLUMNS,
            triggers=frozenset({"category"}),
        ),
    ),
    "inventory_value": MetricEntry(
        key="inventory_value",
        display_name="Inventory Value",
        definition="Total on-hand inventory value (AED) at month-end snapshot.",
        synonyms=("inventory value", "stock value", "on hand value", "how much stock", "stock on hand", "sitting on"),
        disambiguation_note="A holdings measure (AED), not a demand-relative duration — days_of_cover measures how long that stock lasts.",
        base_relation_sql=_SNAPSHOT_RELATION,
        numerator=AggExpr(func="SUM(on_hand_value_aed)"),
        denominator=None,
        dimension_columns=_SNAPSHOT_DIMENSION_COLUMNS,
        period_column="month_str",
        period_column_type="month_str",
        join_path="inventory_snapshots JOIN skus (snapshot grain)",
        compatible_dimensions=_INVENTORY_DIMS,
        decomposable=True,
        line_grain_variant=None,
    ),
    "days_of_cover": MetricEntry(
        key="days_of_cover",
        display_name="Days of Cover",
        definition="on_hand_qty divided by trailing-90-day daily demand (sum(qty_delivered)/90); re-divide summed totals, never average per-row ratios; null when trailing demand is zero.",
        synonyms=("days of cover", "days of supply", "stock cover", "how long will stock last"),
        disambiguation_note="Forward-looking coverage duration, not a stockout count and not a raw stock value — a zero-demand SKU has null days_of_cover, not zero or infinite.",
        base_relation_sql=_SNAPSHOT_RELATION,
        numerator=AggExpr(func="SUM(on_hand_qty)"),
        denominator=AggExpr(func="SUM(demand_90d)", scale=90.0),
        dimension_columns=_SNAPSHOT_DIMENSION_COLUMNS,
        period_column="month_str",
        period_column_type="month_str",
        join_path="inventory_snapshots JOIN skus, with a correlated trailing-90-day order_lines/orders subquery",
        compatible_dimensions=_INVENTORY_DIMS,
        decomposable=False,
        line_grain_variant=None,
    ),
    "stockout_count": MetricEntry(
        key="stockout_count",
        display_name="Stockout Count",
        definition="Count of order lines delivered with qty_delivered = 0.",
        synonyms=("stockouts", "out of stock count", "shortage count", "how many times out of stock"),
        disambiguation_note="An event count (frequency), not a coverage duration — days_of_cover measures remaining runway, not how often it ran out.",
        base_relation_sql=_LINE_GRAIN_FULL_RELATION,
        numerator=AggExpr(func="COUNT(*)", condition="is_stockout"),
        denominator=None,
        dimension_columns=_LINE_GRAIN_FULL_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="order_lines JOIN orders JOIN customers JOIN skus (line grain)",
        compatible_dimensions=_STOCKOUT_DIMS,
        decomposable=True,
        line_grain_variant=None,
    ),
    "avg_supplier_lead_time": MetricEntry(
        key="avg_supplier_lead_time",
        display_name="Average Supplier Lead Time",
        definition="Mean actual lead time in days (actual_arrival_date minus po_date) across shipments promised in the period.",
        synonyms=("lead time", "supplier lead time", "delivery lead time"),
        disambiguation_note=None,
        base_relation_sql=_SHIPMENT_RELATION,
        numerator=AggExpr(func="SUM(lead_days)"),
        denominator=_COUNT_STAR,
        dimension_columns=_SHIPMENT_DIMENSION_COLUMNS,
        period_column="event_date",
        period_column_type="date",
        join_path="shipments (shipment grain), filtered on promised_arrival_date",
        compatible_dimensions=_LEAD_TIME_DIMS,
        decomposable=False,
        line_grain_variant=None,
    ),
}


def get_metric(key: str) -> MetricEntry:
    try:
        return METRICS[key]
    except KeyError:
        raise KeyError(f"Unknown metric key: {key!r}. Valid keys: {sorted(METRICS)}") from None


# --------------------------------------------------------------------------
# Dimension metadata for the catalog renderer.
#
# Only dimensions whose member CODES could be mistaken for another
# dimension's values get an explicit (code, display) list here — e.g. dc's
# "AUH" is also the common short name for the Abu Dhabi emirate, so without
# seeing the DC roster spelled out the model has no way to tell "at AUH"
# is a dc filter rather than an emirate filter. Dimensions whose members are
# already unambiguous full names or snake_case keys (emirate, category,
# customer_segment, supplier) don't need this — stage1.py's catalog
# renderer falls back to a plain member count for those.
# --------------------------------------------------------------------------

DIMENSION_MEMBERS: dict[str, tuple[tuple[str, str], ...]] = {
    "dc": (("JEB", "Jebel Ali"), ("AUH", "Abu Dhabi")),
}


def resolve_for_spec_type(spec_type: str, metric_key: str) -> MetricEntry:
    """Every spec type carries a `metric` field over the same enum space —
    this function exists so callers never write their own metric lookup, and
    the single-source-of-truth test can assert identity across all three."""
    return get_metric(metric_key)
