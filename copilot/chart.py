"""Chart-type selection: spec shape -> ChartSpec, deterministically. No LLM
involved anywhere in this module — the model never picks a chart type, and
never sees this module's output. ChartSpec is pure derived data; the
frontend is the thing that actually draws a chart from it.

Selection rule (fixed by spec_type / time_grain, nothing else):
  metric_query, no time_grain -> stat_card   (a single number, no chart)
  metric_query, time_grain    -> line        (a series over time)
  breakdown_query             -> bar_horizontal
  change_decomposition        -> waterfall   (ranked bars + a total bar)
"""

from dataclasses import dataclass

from copilot import registry

CHART_TYPES = ("stat_card", "line", "bar_horizontal", "waterfall")


@dataclass(frozen=True)
class ChartPoint:
    label: str
    value: float | int | None
    formatted: str
    color: str | None = None


@dataclass(frozen=True)
class ChartSpec:
    type: str
    title: str
    points: tuple
    x_label: str | None
    y_label: str | None


def _metric_display(metric: str) -> str:
    return registry.get_metric(metric).display_name


def build_chart_spec(parsed, result) -> ChartSpec:
    if parsed.spec_type == "metric_query":
        if parsed.time_grain is None:
            return _stat_card(parsed, result)
        return _line_chart(parsed, result)
    if parsed.spec_type == "breakdown_query":
        return _bar_horizontal(parsed, result)
    if parsed.spec_type == "change_decomposition":
        return _waterfall(parsed, result)
    raise ValueError(f"chart.build_chart_spec: no chart defined for spec_type={parsed.spec_type!r}")


def _stat_card(parsed, result) -> ChartSpec:
    point = ChartPoint(label=_metric_display(parsed.metric), value=result.value.raw, formatted=result.value.formatted)
    return ChartSpec(type="stat_card", title=_metric_display(parsed.metric), points=(point,), x_label=None, y_label=None)


def _line_chart(parsed, result) -> ChartSpec:
    points = tuple(
        ChartPoint(label=p.bucket, value=p.value.raw, formatted=p.value.formatted)
        for p in result.points
    )
    return ChartSpec(
        type="line", title=_metric_display(parsed.metric), points=points,
        x_label="period", y_label=_metric_display(parsed.metric),
    )


def _bar_horizontal(parsed, result) -> ChartSpec:
    points = tuple(
        ChartPoint(label=m.member, value=m.value.raw, formatted=m.value.formatted)
        for m in result.members
    )
    return ChartSpec(
        type="bar_horizontal", title=_metric_display(parsed.metric) + " by " + parsed.dimension, points=points,
        x_label=_metric_display(parsed.metric), y_label=parsed.dimension,
    )


def _waterfall(parsed, result) -> ChartSpec:
    ranked = sorted(result.members, key=lambda m: abs(m.contribution.raw or 0), reverse=True)
    points = [
        ChartPoint(
            label=m.member, value=m.contribution.raw, formatted=m.contribution.formatted,
            color="green" if (m.contribution.raw or 0) >= 0 else "red",
        )
        for m in ranked
    ]
    points.append(ChartPoint(label="Total", value=result.delta.raw, formatted=result.delta.formatted, color="total"))
    return ChartSpec(
        type="waterfall", title=_metric_display(parsed.metric) + " change by " + parsed.dimension, points=tuple(points),
        x_label=parsed.dimension, y_label=_metric_display(parsed.metric),
    )
