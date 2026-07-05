"""
This suite verifies the generator planted what stories.json claims. It does
NOT verify metric math. Metric math is pinned by hand fixtures in fixtures/,
which the generator never touches. Never assert a metric value here against
generator output as if it were ground truth.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb

from copilot import constants as C
from copilot.gen.build import build_database
from copilot.gen.util import month_range, month_to_first_date, month_to_last_date


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def built_db_path() -> Path:
    """Builds data/mawarid.duckdb if it doesn't exist yet; otherwise opens
    the already-committed file as-is (the build command is `python
    data/generate.py`, this fixture does not re-run it on every test session)."""
    if not C.DB_PATH.exists():
        build_database(C.DB_PATH)
    return C.DB_PATH


@pytest.fixture(scope="session")
def con(built_db_path):
    connection = duckdb.connect(str(built_db_path), read_only=True)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def stories(built_db_path) -> dict:
    if not C.STORIES_JSON_PATH.exists():
        build_database(C.DB_PATH)
    with open(C.STORIES_JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def _scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


# --------------------------------------------------------------------------
# Story effects (stories.json is the claim; this just checks it held)
# --------------------------------------------------------------------------

def test_stories_json_has_all_three_stories(stories):
    story_numbers = {s["story"] for s in stories["stories"]}
    assert story_numbers == {1, 2, 3}


def test_stories_json_has_expected_effect_count(stories):
    # 8 story-1 checks + 5 story-2 checks + 4 story-3 checks. Update this
    # alongside copilot/gen/effects.py if the effect list changes.
    assert len(stories["effects"]) == 17


@pytest.mark.parametrize("effect_index", range(17))
def test_story_effect_within_tolerance(stories, effect_index):
    effects = stories["effects"]
    assert effect_index < len(effects), f"expected 17 effects, stories.json has {len(effects)}"
    e = effects[effect_index]
    assert e["pass"] is True, (
        f"story {e['story']} check '{e['metric']}' ({e['slice']}) failed: "
        f"actual={e['actual']!r} expected={e['expected']!r}"
    )


# --------------------------------------------------------------------------
# Row counts
# --------------------------------------------------------------------------

def test_dimension_row_counts_are_exact(con):
    assert _scalar(con, "SELECT COUNT(*) FROM suppliers") == C.N_SUPPLIERS
    assert _scalar(con, "SELECT COUNT(*) FROM skus") == C.N_SKUS
    assert _scalar(con, "SELECT COUNT(*) FROM customers") == C.N_CUSTOMERS


def test_snapshot_row_count_is_exact(con):
    # Not sampled: every (sku, dc, month) cell gets exactly one row.
    expected = C.N_SKUS * len(C.DC_CODES) * C.WINDOW_MONTHS
    assert _scalar(con, "SELECT COUNT(*) FROM inventory_snapshots") == expected


@pytest.mark.parametrize("table,target", [
    ("orders", C.TARGET_ORDER_COUNT),
    ("order_lines", C.TARGET_ORDER_LINE_COUNT),
    ("shipments", C.TARGET_SHIPMENT_COUNT),
])
def test_sampled_row_counts_within_tolerance(con, table, target):
    actual = _scalar(con, f"SELECT COUNT(*) FROM {table}")
    lo = target * (1 - C.SCALE_TOLERANCE)
    hi = target * (1 + C.SCALE_TOLERANCE)
    assert lo <= actual <= hi, f"{table}: {actual} not within {C.SCALE_TOLERANCE:.0%} of target {target}"


# --------------------------------------------------------------------------
# Referential integrity
# --------------------------------------------------------------------------

@pytest.mark.parametrize("child,fk_col,parent,pk_col", [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_lines", "order_id", "orders", "order_id"),
    ("order_lines", "sku_id", "skus", "sku_id"),
    ("skus", "primary_supplier_id", "suppliers", "supplier_id"),
    ("shipments", "supplier_id", "suppliers", "supplier_id"),
    ("inventory_snapshots", "sku_id", "skus", "sku_id"),
])
def test_no_orphan_foreign_keys(con, child, fk_col, parent, pk_col):
    sql = f"""
        SELECT COUNT(*) FROM {child} c
        WHERE NOT EXISTS (SELECT 1 FROM {parent} p WHERE p.{pk_col} = c.{fk_col})
    """
    assert _scalar(con, sql) == 0


# --------------------------------------------------------------------------
# Value sanity
# --------------------------------------------------------------------------

def test_no_negative_quantities(con):
    assert _scalar(con, "SELECT COUNT(*) FROM order_lines WHERE qty_ordered <= 0") == 0
    assert _scalar(con, "SELECT COUNT(*) FROM order_lines WHERE qty_delivered < 0") == 0
    assert _scalar(con, "SELECT COUNT(*) FROM inventory_snapshots WHERE on_hand_qty < 0") == 0


def test_qty_delivered_never_exceeds_ordered(con):
    assert _scalar(con, "SELECT COUNT(*) FROM order_lines WHERE qty_delivered > qty_ordered") == 0


def test_order_value_equals_line_sum(con):
    sql = """
        SELECT COUNT(*)
        FROM orders o
        JOIN (SELECT order_id, SUM(line_value_aed) AS line_sum FROM order_lines GROUP BY order_id) l
          ON l.order_id = o.order_id
        WHERE ABS(o.order_value_aed - l.line_sum) > 0.01
    """
    assert _scalar(con, sql) == 0


# --------------------------------------------------------------------------
# Window discipline
# --------------------------------------------------------------------------

def test_all_order_dates_inside_window(con):
    window_start = month_to_first_date(C.WINDOW_START_MONTH)
    window_end = month_to_last_date(C.WINDOW_END_MONTH)
    sql = f"""
        SELECT COUNT(*) FROM orders
        WHERE order_date < DATE '{window_start}'
           OR actual_delivery_date > DATE '{window_end}'
           OR requested_delivery_date > DATE '{window_end}'
    """
    assert _scalar(con, sql) == 0


def test_all_shipment_dates_inside_window(con):
    window_start = month_to_first_date(C.WINDOW_START_MONTH)
    window_end = month_to_last_date(C.WINDOW_END_MONTH)
    sql = f"""
        SELECT COUNT(*) FROM shipments
        WHERE po_date < DATE '{window_start}'
           OR actual_arrival_date > DATE '{window_end}'
    """
    assert _scalar(con, sql) == 0


def test_all_snapshot_months_inside_window(con):
    months = set(month_range(C.WINDOW_START_MONTH, C.WINDOW_END_MONTH))
    rows = con.execute("SELECT DISTINCT snapshot_month FROM inventory_snapshots").fetchall()
    actual_months = {r[0] for r in rows}
    assert actual_months <= months, f"snapshot months outside window: {actual_months - months}"


def test_every_month_in_window_has_orders(con):
    months = month_range(C.WINDOW_START_MONTH, C.WINDOW_END_MONTH)
    rows = con.execute("SELECT DISTINCT strftime(order_date, '%Y-%m') FROM orders").fetchall()
    months_with_orders = {r[0] for r in rows}
    missing = [m for m in months if m not in months_with_orders]
    assert not missing, f"months with zero orders: {missing}"


# --------------------------------------------------------------------------
# Determinism: same SEED must reproduce identical query results. DuckDB
# files are not byte-stable, so this compares query results, not checksums.
# --------------------------------------------------------------------------

_DETERMINISM_QUERIES = [
    "SELECT COUNT(*) FROM orders",
    "SELECT COUNT(*) FROM order_lines",
    "SELECT COUNT(*) FROM shipments",
    "SELECT ROUND(SUM(order_value_aed), 2) FROM orders",
    "SELECT ROUND(SUM(line_value_aed), 2) FROM order_lines",
    "SELECT ROUND(SUM(on_hand_value_aed), 2) FROM inventory_snapshots",
    "SELECT COUNT(*) FROM orders WHERE strftime(order_date, '%Y-%m') = '2026-03'",
    "SELECT ROUND(AVG(CASE WHEN actual_delivery_date <= requested_delivery_date THEN 1.0 ELSE 0.0 END), 6) FROM orders",
    "SELECT ROUND(SUM(qty_delivered), 0) FROM order_lines",
    "SELECT MIN(order_date), MAX(order_date) FROM orders",
]


def test_determinism_rebuild_matches(tmp_path, con):
    rebuilt_path = tmp_path / "mawarid_rebuild.duckdb"
    build_database(rebuilt_path, write_stories_json=False)
    con2 = duckdb.connect(str(rebuilt_path), read_only=True)
    try:
        for sql in _DETERMINISM_QUERIES:
            original = con.execute(sql).fetchone()
            rebuilt = con2.execute(sql).fetchone()
            assert original == rebuilt, f"determinism mismatch for query: {sql}\n  original={original}\n  rebuilt={rebuilt}"
    finally:
        con2.close()
