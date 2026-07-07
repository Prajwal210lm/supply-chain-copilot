"""End-to-end: load all three pinned fixtures into a throwaway in-memory
DuckDB (via fixture_loader.py, which refuses to run if any fixture is not
hand_verified) and run the REAL compiler (validate -> compile -> execute ->
decompose) against them, asserting every value the fixture worksheets pin.

This suite never touches fixtures/ or eval/ — fixture_loader.py only reads
them.
"""

import pytest

from copilot import compile as compiler
from copilot import decompose, validate
from tests.fixture_loader import load_all_fixtures


@pytest.fixture(scope="module")
def fixtures():
    data = load_all_fixtures()
    yield data
    data["con"].close()


def _run_metric_query(con, metric, start, end, filters=None):
    raw = {"spec_type": "metric_query", "metric": metric, "period": {"grain": "month", "start": start, "end": end}}
    if filters:
        raw["filters"] = filters
    outcome = validate.validate(raw)
    assert isinstance(outcome, validate.Accepted), outcome
    compiled = compiler.compile_metric_query(outcome.spec, outcome.resolved_filters)
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    return con.execute(finalized.sql, finalized.params).fetchone()[0]


def _run_breakdown_query(con, metric, start, end, dimension, top_n=20):
    raw = {
        "spec_type": "breakdown_query", "metric": metric,
        "period": {"grain": "month", "start": start, "end": end},
        "dimension": dimension, "top_n": top_n, "sort": "desc",
    }
    outcome = validate.validate(raw)
    assert isinstance(outcome, validate.Accepted), outcome
    compiled = compiler.compile_breakdown_query(outcome.spec, outcome.resolved_filters)
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()
    return {r[0]: r[1] for r in rows}


def _run_decomposition_rows(con, metric, dimension, a_start, a_end, b_start, b_end):
    raw = {
        "spec_type": "change_decomposition", "metric": metric, "dimension": dimension,
        "period_a": {"grain": "month", "start": a_start, "end": a_end},
        "period_b": {"grain": "month", "start": b_start, "end": b_end},
    }
    outcome = validate.validate(raw)
    assert isinstance(outcome, validate.Accepted), outcome
    compiled = compiler.compile_change_decomposition(outcome.spec, outcome.resolved_filters)
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    return con.execute(finalized.sql, finalized.params).fetchall()


# --------------------------------------------------------------------------
# decomposition_fixture.yaml — order-grain metric layer, Feb & Mar 2026
# --------------------------------------------------------------------------

@pytest.mark.parametrize("metric,month,expected", [
    ("otif_pct", "2026-02", 75.0), ("otif_pct", "2026-03", 50.0),
    ("on_time_pct", "2026-02", 75.0), ("on_time_pct", "2026-03", 75.0),
    ("in_full_pct", "2026-02", 100.0), ("in_full_pct", "2026-03", 75.0),
    ("fill_rate_pct", "2026-02", 100.0), ("fill_rate_pct", "2026-03", 85.0),
    ("revenue", "2026-02", 4500.0), ("revenue", "2026-03", 4200.0),
    ("order_count", "2026-02", 12), ("order_count", "2026-03", 12),
    ("avg_order_value", "2026-02", 375.0), ("avg_order_value", "2026-03", 350.0),
    ("stockout_count", "2026-02", 0), ("stockout_count", "2026-03", 1),
])
def test_decomposition_fixture_metric_layer(fixtures, metric, month, expected):
    actual = _run_metric_query(fixtures["con"], metric, month, month)
    assert actual == pytest.approx(expected)


def test_decomposition_fixture_supplier_decomposition_matches_worksheet(fixtures):
    rows = _run_decomposition_rows(fixtures["con"], "otif_pct", "supplier", "2026-02", "2026-02", "2026-03", "2026-03")
    decomposed_rows = [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    result = decompose.decompose_ratio(decomposed_rows)
    by_member = {m.member: m for m in result.members}

    assert by_member["S1"].contribution == pytest.approx(-25.0)
    assert by_member["S2"].contribution == pytest.approx(5.0)
    assert result.sum_of_contributions == pytest.approx(-20.0)
    assert result.delta == pytest.approx(-20.0)
    assert result.residual_ok is True
    assert result.residual == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------
# otif_overlap_fixture.yaml — the union-not-sum bug fixture
# --------------------------------------------------------------------------

@pytest.mark.parametrize("metric,expected", [
    ("on_time_pct", 50.0),
    ("in_full_pct", 50.0),
    ("otif_pct", 25.0),
])
def test_otif_overlap_fixture(fixtures, metric, expected):
    actual = _run_metric_query(fixtures["con"], metric, "2026-01", "2026-01")
    assert actual == pytest.approx(expected)


# --------------------------------------------------------------------------
# days_of_cover_fixture.yaml — re-divided sums, zero-demand null
# --------------------------------------------------------------------------

def test_days_of_cover_dc_aggregates_match_worksheet(fixtures):
    by_dc = _run_breakdown_query(fixtures["con"], "days_of_cover", "2026-06", "2026-06", "dc")
    assert by_dc["JEB"] == pytest.approx(22.0)
    assert by_dc["AUH"] == pytest.approx(13.5)


def test_days_of_cover_dc_aggregate_is_not_mean_of_row_ratios(fixtures):
    # A mean-of-row-DOCs implementation for AUH would average
    # [12.6, 15.0, 7.0, null-excluded, 3.0] -> ~9.4, NOT 13.5. The
    # re-divided-sums result (162 / 12.0 = 13.5) is what must come back.
    by_dc = _run_breakdown_query(fixtures["con"], "days_of_cover", "2026-06", "2026-06", "dc")
    naive_mean_of_rows_auh = (12.6 + 15.0 + 7.0 + 3.0) / 4  # excluding the null SKU-D row
    assert by_dc["AUH"] != pytest.approx(naive_mean_of_rows_auh, rel=0.05)


def test_inventory_value_matches_worksheet(fixtures):
    by_dc = _run_breakdown_query(fixtures["con"], "inventory_value", "2026-06", "2026-06", "dc")
    assert by_dc["JEB"] == pytest.approx(10230.0)
    assert by_dc["AUH"] == pytest.approx(2799.0)
    total = _run_metric_query(fixtures["con"], "inventory_value", "2026-06", "2026-06")
    assert total == pytest.approx(13029.0)


@pytest.mark.parametrize("sku,dc,expected", [
    ("SKU-A", "JEB", 45.0), ("SKU-A", "AUH", 12.6),
    ("SKU-B", "JEB", 24.9), ("SKU-B", "AUH", 15.0),
    ("SKU-C", "JEB", 15.0), ("SKU-C", "AUH", 7.0),
    ("SKU-D", "JEB", 8.0), ("SKU-D", "AUH", None),
    ("SKU-E", "JEB", 7.0), ("SKU-E", "AUH", 3.0),
])
def test_days_of_cover_per_sku_dc_row_matches_worksheet(fixtures, sku, dc, expected):
    actual = _run_metric_query(
        fixtures["con"], "days_of_cover", "2026-06", "2026-06",
        filters=[{"dimension": "dc", "values": [dc]}],
    )
    # The per-sku figure isn't independently queryable (days_of_cover has no
    # sku dimension per the compat matrix) — verify it directly against the
    # snapshot + demand rows instead, the same way the fixture worksheet does.
    row = fixtures["con"].execute(
        "SELECT on_hand_qty FROM inventory_snapshots WHERE sku_id = ? AND dc = ? AND snapshot_month = '2026-06'",
        [sku, dc],
    ).fetchone()
    demand_row = fixtures["con"].execute(
        "SELECT COALESCE(SUM(ol.qty_delivered), 0) FROM order_lines ol JOIN orders o ON o.order_id = ol.order_id "
        "WHERE ol.sku_id = ? AND o.dc = ? AND strftime(o.order_date, '%Y-%m') IN ('2026-04', '2026-05', '2026-06')",
        [sku, dc],
    ).fetchone()
    on_hand_qty = row[0]
    demand_90d = demand_row[0]
    if demand_90d == 0:
        assert expected is None
    else:
        computed = on_hand_qty / (demand_90d / 90.0)
        assert computed == pytest.approx(expected)
