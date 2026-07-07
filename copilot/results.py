"""The result contract: every numeric value carries its raw form plus a
formatted (P1 convention) sibling, and each spec_type gets a stable result
shape so a future display/templating layer can address values by a fixed
dot-path rather than re-deriving formatting rules itself.

## Placeholder namespace (dot-paths a template layer can reference)

MetricQueryResult:
    value.raw, value.formatted
    period_label   (e.g. "Jun 2026", "Q1 2026", "Jan 2025 to Dec 2025" —
                     see copilot.dateutil.period_label; a plain string,
                     not a FormattedNumber, since it has no raw/formatted
                     numeric split)

MetricSeriesResult:
    points[i].bucket, points[i].value.raw, points[i].value.formatted
    min.raw, min.formatted
    max.raw, max.formatted
    first.raw, first.formatted   (the first POINT positionally, even if null)
    latest.raw, latest.formatted (the last POINT positionally, even if null)

BreakdownResult:
    members[i].member, members[i].value.raw, members[i].value.formatted
    total.raw, total.formatted
    period_label

DecompositionResult:
    members[i].member
    members[i].share_a.raw / .formatted   (None for additive metrics)
    members[i].share_b.raw / .formatted   (None for additive metrics)
    members[i].rate_a.raw / .formatted    (None for additive metrics)
    members[i].rate_b.raw / .formatted    (None for additive metrics)
    members[i].contribution.raw / .formatted
    delta.raw, delta.formatted
    residual_ok, withheld, withheld_reason
    period_a_label, period_b_label

## Formatter rules (P1 conventions)

  currency : AED X.XM at 1,000,000+; AED XXXK (no decimals) at 100,000-999,999;
             AED X,XXX.XX (2 decimals, comma grouped) below that.
  percentage: one decimal place, e.g. "84.2%".
  pts delta : one decimal place, always signed, e.g. "+5.2pts" / "-3.1pts".
  days      : one decimal place, e.g. "45.0 days".
  count     : comma-grouped integer, no decimals.

None always formats as "N/A" (never "0" or "-").
"""

from dataclasses import dataclass

from copilot import dateutil as D
from copilot import decompose

_CURRENCY_METRICS = frozenset({"revenue", "avg_order_value", "inventory_value"})
_PERCENTAGE_METRICS = frozenset({"otif_pct", "on_time_pct", "in_full_pct", "fill_rate_pct"})
_COUNT_METRICS = frozenset({"order_count", "stockout_count"})
_DAYS_METRICS = frozenset({"days_of_cover", "avg_supplier_lead_time"})


@dataclass(frozen=True)
class FormattedNumber:
    raw: float | int | None
    formatted: str


def format_aed(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return "AED " + format(value / 1_000_000, ".1f") + "M"
    if abs_value >= 100_000:
        return "AED " + format(round(value / 1000), ",") + "K"
    return "AED " + format(value, ",.2f")


def format_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return format(value, ".1f") + "%"


def format_pts_delta(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return sign + format(value, ".1f") + "pts"


def format_days(value: float | None) -> str:
    if value is None:
        return "N/A"
    return format(value, ".1f") + " days"


def format_count(value: int | None) -> str:
    if value is None:
        return "N/A"
    return format(value, ",")


def _style_for_metric(metric: str) -> str:
    if metric in _CURRENCY_METRICS:
        return "currency"
    if metric in _PERCENTAGE_METRICS:
        return "percentage"
    if metric in _COUNT_METRICS:
        return "count"
    if metric in _DAYS_METRICS:
        return "days"
    return "plain"


_FORMATTERS = {
    "currency": format_aed,
    "percentage": format_pct,
    "count": format_count,
    "days": format_days,
    "plain": lambda v: "N/A" if v is None else str(v),
}


def format_metric_value(metric: str, value) -> FormattedNumber:
    style = _style_for_metric(metric)
    return FormattedNumber(raw=value, formatted=_FORMATTERS[style](value))


def _pts_number(value: float | None) -> FormattedNumber:
    return FormattedNumber(raw=value, formatted=format_pts_delta(value))


def _share_number(value: float | None) -> FormattedNumber:
    return FormattedNumber(raw=value, formatted=("N/A" if value is None else format(value, ".1%")))


# --------------------------------------------------------------------------
# Result objects
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class MetricQueryResult:
    metric: str
    value: FormattedNumber
    period_label: str


def build_metric_query_result(metric: str, value, period) -> MetricQueryResult:
    return MetricQueryResult(metric=metric, value=format_metric_value(metric, value), period_label=D.period_label(period))


@dataclass(frozen=True)
class SeriesPoint:
    bucket: str
    value: FormattedNumber


@dataclass(frozen=True)
class MetricSeriesResult:
    metric: str
    points: tuple
    min: FormattedNumber
    max: FormattedNumber
    first: FormattedNumber
    latest: FormattedNumber


def build_series_result(metric: str, points) -> MetricSeriesResult:
    points = list(points)
    series_points = tuple(SeriesPoint(bucket=b, value=format_metric_value(metric, v)) for b, v in points)
    non_null = [v for _, v in points if v is not None]
    min_value = min(non_null) if non_null else None
    max_value = max(non_null) if non_null else None
    first_value = points[0][1] if points else None
    latest_value = points[-1][1] if points else None
    return MetricSeriesResult(
        metric=metric,
        points=series_points,
        min=format_metric_value(metric, min_value),
        max=format_metric_value(metric, max_value),
        first=format_metric_value(metric, first_value),
        latest=format_metric_value(metric, latest_value),
    )


@dataclass(frozen=True)
class BreakdownMember:
    member: str
    value: FormattedNumber


@dataclass(frozen=True)
class BreakdownResult:
    metric: str
    dimension: str
    members: tuple
    total: FormattedNumber
    period_label: str


def build_breakdown_result(metric: str, dimension: str, members, total, period) -> BreakdownResult:
    member_objs = tuple(BreakdownMember(member=m, value=format_metric_value(metric, v)) for m, v in members)
    return BreakdownResult(
        metric=metric, dimension=dimension, members=member_objs,
        total=format_metric_value(metric, total), period_label=D.period_label(period),
    )


@dataclass(frozen=True)
class DecompositionMember:
    member: str
    share_a: FormattedNumber | None
    share_b: FormattedNumber | None
    rate_a: FormattedNumber | None
    rate_b: FormattedNumber | None
    contribution: FormattedNumber


@dataclass(frozen=True)
class DecompositionResult:
    metric: str
    dimension: str
    members: tuple
    delta: FormattedNumber
    residual_ok: bool
    withheld: bool
    withheld_reason: str | None
    period_a_label: str
    period_b_label: str


def build_decomposition_result(metric: str, dimension: str, decomposed, period_a, period_b) -> DecompositionResult:
    if isinstance(decomposed, decompose.RatioDecompositionResult):
        members = tuple(
            DecompositionMember(
                member=m.member,
                share_a=_share_number(m.share_a),
                share_b=_share_number(m.share_b),
                rate_a=FormattedNumber(raw=m.rate_a, formatted=format_pct(m.rate_a)),
                rate_b=FormattedNumber(raw=m.rate_b, formatted=format_pct(m.rate_b)),
                contribution=_pts_number(m.contribution),
            )
            for m in decomposed.members
        )
        delta = _pts_number(decomposed.delta)
    else:
        members = tuple(
            DecompositionMember(
                member=m.member, share_a=None, share_b=None, rate_a=None, rate_b=None,
                contribution=format_metric_value(metric, m.contribution),
            )
            for m in decomposed.members
        )
        delta = format_metric_value(metric, decomposed.delta)

    return DecompositionResult(
        metric=metric, dimension=dimension, members=members, delta=delta,
        residual_ok=decomposed.residual_ok, withheld=decomposed.withheld,
        withheld_reason=decomposed.withheld_reason,
        period_a_label=D.period_label(period_a), period_b_label=D.period_label(period_b),
    )
