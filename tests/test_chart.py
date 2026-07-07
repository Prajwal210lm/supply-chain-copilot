"""Tests for copilot/chart.py — deterministic chart-type selection, no LLM
involved. Specs and results are built via the real spec.py/results.py/
decompose.py code paths, not hand-rolled fakes, so these tests exercise the
actual shapes chart.py will see in production.
"""

import pytest

from copilot import chart, decompose, results, spec


def _metric_query_spec(time_grain=None):
    d = {
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    }
    if time_grain:
        d["time_grain"] = time_grain
    return spec.parse_spec(d)


def _breakdown_spec():
    return spec.parse_spec({
        "spec_type": "breakdown_query", "metric": "revenue", "dimension": "category",
        "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
    })


def _decomposition_spec():
    return spec.parse_spec({
        "spec_type": "change_decomposition", "metric": "revenue", "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })


def test_stat_card_for_metric_query_without_time_grain():
    parsed = _metric_query_spec()
    result = results.build_metric_query_result("otif_pct", 84.2, parsed.period)
    chart_spec = chart.build_chart_spec(parsed, result)
    assert chart_spec.type == "stat_card"
    assert len(chart_spec.points) == 1
    assert chart_spec.points[0].value == 84.2
    assert chart_spec.points[0].formatted == "84.2%"


def test_stat_card_has_no_axis_labels():
    parsed = _metric_query_spec()
    result = results.build_metric_query_result("otif_pct", 84.2, parsed.period)
    chart_spec = chart.build_chart_spec(parsed, result)
    assert chart_spec.x_label is None
    assert chart_spec.y_label is None


def test_line_chart_for_metric_query_with_time_grain():
    parsed = _metric_query_spec(time_grain="month")
    result = results.build_series_result("otif_pct", [("2026-05", 84.2), ("2026-06", 90.0)])
    chart_spec = chart.build_chart_spec(parsed, result)
    assert chart_spec.type == "line"
    assert [p.label for p in chart_spec.points] == ["2026-05", "2026-06"]
    assert [p.value for p in chart_spec.points] == [84.2, 90.0]


def test_bar_horizontal_for_breakdown_query():
    parsed = _breakdown_spec()
    result = results.build_breakdown_result(
        "revenue", "category", [("food_beverage", 1000), ("personal_care", 500)], 1500, parsed.period,
    )
    chart_spec = chart.build_chart_spec(parsed, result)
    assert chart_spec.type == "bar_horizontal"
    assert len(chart_spec.points) == 2
    assert chart_spec.y_label == "category"


def test_waterfall_for_change_decomposition_has_ranked_bars_plus_total():
    parsed = _decomposition_spec()
    decomposed = decompose.decompose_additive([("food_beverage", 1000, 1200), ("personal_care", 500, 400)])
    result = results.build_decomposition_result("revenue", "category", decomposed, parsed.period_a, parsed.period_b)
    chart_spec = chart.build_chart_spec(parsed, result)
    assert chart_spec.type == "waterfall"
    assert len(chart_spec.points) == 3
    assert chart_spec.points[-1].label == "Total"
    assert chart_spec.points[-1].color == "total"


def test_waterfall_colors_positive_green_negative_red():
    parsed = _decomposition_spec()
    decomposed = decompose.decompose_additive([("food_beverage", 1000, 1200), ("personal_care", 500, 400)])
    result = results.build_decomposition_result("revenue", "category", decomposed, parsed.period_a, parsed.period_b)
    chart_spec = chart.build_chart_spec(parsed, result)
    by_label = {p.label: p for p in chart_spec.points}
    assert by_label["food_beverage"].color == "green"
    assert by_label["personal_care"].color == "red"


def test_waterfall_ranked_by_absolute_contribution_descending():
    parsed = _decomposition_spec()
    decomposed = decompose.decompose_additive([("small", 100, 110), ("big", 1000, 1300)])
    result = results.build_decomposition_result("revenue", "category", decomposed, parsed.period_a, parsed.period_b)
    chart_spec = chart.build_chart_spec(parsed, result)
    assert [p.label for p in chart_spec.points[:-1]] == ["big", "small"]


def test_waterfall_handles_withheld_decomposition_with_no_members():
    parsed = _decomposition_spec()
    # A residual mismatch forces decompose.py to withhold members entirely.
    decomposed = decompose.decompose_additive([("a", 100, 200)], total_a=0, total_b=0)
    assert decomposed.withheld is True
    result = results.build_decomposition_result("revenue", "category", decomposed, parsed.period_a, parsed.period_b)
    chart_spec = chart.build_chart_spec(parsed, result)
    assert chart_spec.type == "waterfall"
    assert len(chart_spec.points) == 1
    assert chart_spec.points[0].label == "Total"


def test_unknown_spec_type_raises():
    class FakeSpec:
        spec_type = "clarification"

    with pytest.raises(ValueError):
        chart.build_chart_spec(FakeSpec(), object())
