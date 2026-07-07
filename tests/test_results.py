"""Tests for copilot/results.py — written before the module exists (red)."""

import pytest

from copilot import decompose, results
from copilot.spec import Period


def _period(start, end=None):
    return Period(grain="month", start=start, end=end or start)


# --------------------------------------------------------------------------
# Formatters (P1 conventions)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (1_500_000, "AED 1.5M"),
    (1_000_000, "AED 1.0M"),
    (999_999, "AED 1,000K"),  # just under 1M, rounds within the K tier's own precision
    (350_000, "AED 350K"),
    (100_000, "AED 100K"),
    (99_999, "AED 99,999.00"),
    (1_234.5, "AED 1,234.50"),
    (0, "AED 0.00"),
])
def test_format_aed(value, expected):
    assert results.format_aed(value) == expected


def test_format_aed_none_is_na():
    assert results.format_aed(None) == "N/A"


@pytest.mark.parametrize("value,expected", [
    (33.333, "33.3%"),
    (100.0, "100.0%"),
    (0.0, "0.0%"),
])
def test_format_pct(value, expected):
    assert results.format_pct(value) == expected


def test_format_pct_none_is_na():
    assert results.format_pct(None) == "N/A"


@pytest.mark.parametrize("value,expected", [
    (-20.0, "-20.0pts"),
    (5.0, "+5.0pts"),
    (0.0, "+0.0pts"),
])
def test_format_pts_delta(value, expected):
    assert results.format_pts_delta(value) == expected


def test_format_days():
    assert results.format_days(45.0) == "45.0 days"


def test_format_days_none_is_na():
    assert results.format_days(None) == "N/A"


@pytest.mark.parametrize("value,expected", [
    (1234, "1,234"),
    (0, "0"),
])
def test_format_count(value, expected):
    assert results.format_count(value) == expected


def test_format_count_none_is_na():
    assert results.format_count(None) == "N/A"


def test_format_metric_value_dispatches_by_metric_style():
    assert results.format_metric_value("otif_pct", 84.2).formatted == "84.2%"
    assert results.format_metric_value("revenue", 1_500_000).formatted == "AED 1.5M"
    assert results.format_metric_value("order_count", 1234).formatted == "1,234"
    assert results.format_metric_value("days_of_cover", 45.0).formatted == "45.0 days"
    val = results.format_metric_value("otif_pct", 84.2)
    assert val.raw == 84.2


# --------------------------------------------------------------------------
# Result objects
# --------------------------------------------------------------------------

def test_metric_query_result_shape():
    r = results.build_metric_query_result(metric="otif_pct", value=84.2, period=_period("2026-06"))
    assert r.value.raw == 84.2
    assert r.value.formatted == "84.2%"
    assert r.period_label == "Jun 2026"


def test_metric_query_result_null_value():
    r = results.build_metric_query_result(metric="days_of_cover", value=None, period=_period("2026-06"))
    assert r.value.raw is None
    assert r.value.formatted == "N/A"


def test_series_result_precomputes_min_max_latest_first():
    r = results.build_series_result(
        metric="revenue",
        points=[("2026-01", None), ("2026-02", 150.0), ("2026-03", 290.0)],
    )
    assert len(r.points) == 3
    assert r.points[0].value.raw is None
    assert r.min.raw == 150.0
    assert r.max.raw == 290.0
    assert r.first.raw is None  # first POINT, positional, even though it's null
    assert r.latest.raw == 290.0


def test_series_result_all_null_min_max_are_na():
    r = results.build_series_result(metric="revenue", points=[("2026-01", None), ("2026-02", None)])
    assert r.min.formatted == "N/A"
    assert r.max.formatted == "N/A"


def test_breakdown_result_shape_and_total():
    r = results.build_breakdown_result(
        metric="revenue", dimension="category",
        members=[("home_care", 150.0), ("food_beverage", 100.0), ("All others", 40.0)],
        total=290.0, period=_period("2026-04", "2026-06"),
    )
    assert [m.member for m in r.members] == ["home_care", "food_beverage", "All others"]
    assert r.members[0].value.formatted == "AED 150.00"
    assert r.total.raw == 290.0
    assert r.period_label == "Q2 2026"


def test_decomposition_result_from_ratio_carries_shares_and_rates():
    decomposed = decompose.decompose_ratio([("S1", 9, 12, 4, 8), ("S2", 5, 8, 6, 12)])
    r = results.build_decomposition_result(
        metric="otif_pct", dimension="supplier", decomposed=decomposed,
        period_a=_period("2026-02"), period_b=_period("2026-03"),
    )
    by_member = {m.member: m for m in r.members}
    assert by_member["S1"].share_a.raw == pytest.approx(0.6)
    assert by_member["S1"].rate_a.formatted == "75.0%"
    assert by_member["S1"].contribution.formatted == "-25.0pts"
    assert r.residual_ok is True
    assert r.withheld is False
    assert r.period_a_label == "Feb 2026"
    assert r.period_b_label == "Mar 2026"


def test_decomposition_result_from_additive_has_no_shares_or_rates():
    decomposed = decompose.decompose_additive([("home_care", 15000, 15000), ("food_beverage", 0, 10000)])
    r = results.build_decomposition_result(
        metric="revenue", dimension="category", decomposed=decomposed,
        period_a=_period("2026-02"), period_b=_period("2026-03"),
    )
    by_member = {m.member: m for m in r.members}
    assert by_member["home_care"].share_a is None
    assert by_member["home_care"].rate_a is None
    assert by_member["food_beverage"].contribution.raw == 10000


def test_decomposition_result_withheld_has_no_members():
    decomposed = decompose.decompose_additive(
        [("cat_a", 100, 120), ("cat_b", 50, 40)], total_a=150, total_b=200,
    )
    r = results.build_decomposition_result(
        metric="revenue", dimension="category", decomposed=decomposed,
        period_a=_period("2026-02"), period_b=_period("2026-03"),
    )
    assert r.members == ()
    assert r.withheld is True
    assert r.withheld_reason
