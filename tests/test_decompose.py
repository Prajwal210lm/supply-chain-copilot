"""Tests for copilot/decompose.py — written before the module exists (red).

Pure math, no database. The ratio-decomposition numbers below are taken
directly from fixtures/decomposition_fixture.yaml's worksheet (hand_verified:
true) — S1: Feb 9-of-12 line-grain OTIF, Mar 4-of-8; S2: Feb 5-of-8, Mar
6-of-12. Contributions -25.0 / +5.0 summing to -20.0, matching the pinned
line_grain_delta of -20.0 exactly.
"""

import pytest

from copilot import decompose


# --------------------------------------------------------------------------
# Ratio decomposition — matches the fixture worksheet exactly
# --------------------------------------------------------------------------

def test_ratio_decomposition_matches_fixture_worksheet():
    rows = [
        ("S1", 9, 12, 4, 8),   # (member, num_a, den_a, num_b, den_b)
        ("S2", 5, 8, 6, 12),
    ]
    result = decompose.decompose_ratio(rows)
    by_member = {m.member: m for m in result.members}

    assert by_member["S1"].contribution == pytest.approx(-25.0)
    assert by_member["S2"].contribution == pytest.approx(5.0)
    assert result.sum_of_contributions == pytest.approx(-20.0)
    assert result.delta == pytest.approx(-20.0)
    assert result.rate_a == pytest.approx(70.0)
    assert result.rate_b == pytest.approx(50.0)
    assert result.residual == pytest.approx(0.0, abs=1e-9)
    assert result.residual_ok is True
    assert result.withheld is False


def test_ratio_decomposition_shares_and_rates_match_worksheet():
    rows = [("S1", 9, 12, 4, 8), ("S2", 5, 8, 6, 12)]
    result = decompose.decompose_ratio(rows)
    by_member = {m.member: m for m in result.members}

    assert by_member["S1"].share_a == pytest.approx(0.600)
    assert by_member["S1"].rate_a == pytest.approx(75.0)
    assert by_member["S1"].share_b == pytest.approx(0.400)
    assert by_member["S1"].rate_b == pytest.approx(50.0)

    assert by_member["S2"].share_a == pytest.approx(0.400)
    assert by_member["S2"].rate_a == pytest.approx(62.5)
    assert by_member["S2"].share_b == pytest.approx(0.600)
    assert by_member["S2"].rate_b == pytest.approx(50.0)


def test_order_grain_counts_fail_to_reconcile_against_pinned_line_grain_delta():
    # Deliberately broken variant: order-grain OTIF counts per supplier
    # (derived from the same fixture's raw orders, by hand) instead of the
    # line-grain counts docs/SPEC.md requires for a supplier cut. This must
    # NOT reproduce the fixture's pinned line_grain_delta of -20.0 — that
    # mismatch is exactly what the "supplier cut needs line grain" rule
    # exists to prevent silently passing.
    order_grain_rows = [
        ("S1", 5, 7, 2, 5),    # S1: Feb 5-of-7 orders OTIF, Mar 2-of-5
        ("S2", 4, 5, 4, 7),    # S2: Feb 4-of-5 orders OTIF, Mar 4-of-7
    ]
    result = decompose.decompose_ratio(order_grain_rows)
    LINE_GRAIN_DELTA = -20.0  # pinned by fixtures/decomposition_fixture.yaml
    assert result.delta == pytest.approx(-25.0)  # matches the fixture's separately-noted order_grain_delta
    assert result.delta != pytest.approx(LINE_GRAIN_DELTA)


def test_ratio_decomposition_withholds_on_externally_supplied_total_mismatch():
    rows = [("S1", 9, 12, 4, 8), ("S2", 5, 8, 6, 12)]
    ok = decompose.decompose_ratio(rows)
    assert ok.residual_ok is True

    # Cross-checking against an independently-fetched (and here, wrong on
    # purpose) grand total simulates a real integrity bug — e.g. the
    # decomposition query's WHERE clause silently dropping rows the
    # standalone total query included.
    bad = decompose.decompose_ratio(rows, total_num_b=999, total_den_b=12)
    assert bad.residual_ok is False
    assert bad.withheld is True
    assert bad.members == ()
    assert bad.withheld_reason


# --------------------------------------------------------------------------
# Additive decomposition — exact integer (fils) arithmetic
# --------------------------------------------------------------------------

def test_additive_decomposition_exact_integer_arithmetic():
    # AED 150 / 100 / 40 in fils (x100), Feb has only home_care.
    rows = [
        ("home_care", 15000, 15000),
        ("food_beverage", 0, 10000),
        ("personal_care", 0, 4000),
    ]
    result = decompose.decompose_additive(rows)

    assert result.total_a == 15000
    assert result.total_b == 29000
    assert result.delta == 14000
    assert result.sum_of_contributions == 14000
    assert result.residual == 0
    assert isinstance(result.residual, int)
    assert result.residual_ok is True
    assert result.withheld is False

    by_member = {m.member: m for m in result.members}
    assert by_member["home_care"].contribution == 0
    assert by_member["food_beverage"].contribution == 10000
    assert by_member["personal_care"].contribution == 4000


def test_additive_decomposition_withholds_on_externally_supplied_total_mismatch():
    rows = [("cat_a", 100, 120), ("cat_b", 50, 40)]
    ok = decompose.decompose_additive(rows)
    assert ok.residual_ok is True
    assert ok.residual == 0

    bad = decompose.decompose_additive(rows, total_a=150, total_b=200)
    assert bad.residual_ok is False
    assert bad.withheld is True
    assert bad.members == ()
    assert bad.withheld_reason


def test_additive_decomposition_preserves_member_present_in_only_one_period():
    rows = [("only_in_a", 500, 0), ("only_in_b", 0, 300), ("in_both", 100, 150)]
    result = decompose.decompose_additive(rows)
    members = {m.member for m in result.members}
    assert members == {"only_in_a", "only_in_b", "in_both"}


def test_ratio_residual_tolerance_constant_is_locked():
    assert decompose.RATIO_RESIDUAL_REL_TOL == 1e-9
