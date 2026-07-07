"""Tests for copilot/compile.py — written before the module exists (red).

Uses a small synthetic in-memory DuckDB (not the fixtures — those are for
test_integration_fixture.py) so every expected number here is hand-computed
in this file's own comments, independent of the project's pinned fixtures.
"""

import ast
import re
from pathlib import Path

import duckdb
import pytest

from copilot import compile as compiler
from copilot import constants as C
from copilot import spec, validate

SCHEMA_SQL = C.SCHEMA_SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture()
def con():
    connection = duckdb.connect(":memory:")
    connection.execute(SCHEMA_SQL)

    connection.execute("INSERT INTO suppliers VALUES ('SUP-01','Test Supplier A','Testland',10)")
    connection.execute("INSERT INTO suppliers VALUES ('SUP-02','Test Supplier B','Testland',10)")

    connection.execute("INSERT INTO skus VALUES ('SKU-T1','Widget','home_care','A',5.00,'SUP-01')")
    connection.execute("INSERT INTO skus VALUES ('SKU-T2','Gadget','food_beverage','A',2.00,'SUP-02')")
    connection.execute("INSERT INTO skus VALUES ('SKU-T3','Gizmo','personal_care','A',8.00,'SUP-01')")

    connection.execute("INSERT INTO customers VALUES ('CUST-1','Alpha Trading','modern_trade','Dubai')")
    connection.execute("INSERT INTO customers VALUES ('CUST-2','Beta Trading','traditional_trade','Abu Dhabi')")

    # --- Feb 2026: only home_care present (revenue 150, on-time, in-full) ---
    connection.execute("""
        INSERT INTO orders VALUES
        ('ORD-0','CUST-1','JEB', DATE '2026-02-15', DATE '2026-02-18', DATE '2026-02-18', 150.00)
    """)
    connection.execute("INSERT INTO order_lines VALUES ('ORD-0','SKU-T1',10,10,15.00,150.00)")

    # --- Mar 2026: three orders, three categories ---
    # ORD-1: on_time, in_full -> OTIF. home_care revenue 150.
    connection.execute("""
        INSERT INTO orders VALUES
        ('ORD-1','CUST-1','JEB', DATE '2026-03-15', DATE '2026-03-18', DATE '2026-03-18', 150.00)
    """)
    connection.execute("INSERT INTO order_lines VALUES ('ORD-1','SKU-T1',10,10,15.00,150.00)")

    # ORD-2: LATE but in_full -> not OTIF, not on_time. food_beverage revenue 100.
    connection.execute("""
        INSERT INTO orders VALUES
        ('ORD-2','CUST-2','AUH', DATE '2026-03-15', DATE '2026-03-18', DATE '2026-03-23', 100.00)
    """)
    connection.execute("INSERT INTO order_lines VALUES ('ORD-2','SKU-T2',20,20,5.00,100.00)")

    # ORD-3: on_time but SHORT (2 of 5) -> not OTIF, not in_full. personal_care revenue 40 (delivered).
    connection.execute("""
        INSERT INTO orders VALUES
        ('ORD-3','CUST-1','JEB', DATE '2026-03-15', DATE '2026-03-18', DATE '2026-03-18', 100.00)
    """)
    connection.execute("INSERT INTO order_lines VALUES ('ORD-3','SKU-T3',5,2,20.00,40.00)")

    # One shipment: SUP-01 at JEB in March, lead_days = 5. No shipments at all
    # for SUP-01/AUH — deliberately, for the zero-denominator lead-time test.
    connection.execute("""
        INSERT INTO shipments VALUES
        ('SHIP-1','SUP-01','JEB', DATE '2026-03-01', DATE '2026-03-10', DATE '2026-03-15')
    """)

    yield connection
    connection.close()


def _validate_and_compile(compile_fn, raw_spec: dict):
    outcome = validate.validate(raw_spec)
    assert isinstance(outcome, validate.Accepted), f"expected Accepted, got {outcome!r}"
    return compile_fn(outcome.spec, outcome.resolved_filters)


# --------------------------------------------------------------------------
# Structural guardrails
# --------------------------------------------------------------------------

def test_no_fstring_or_format_call_in_compile_module():
    source = Path(compiler.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            violations.append(f"f-string at line {node.lineno}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            violations.append(f".format() call at line {node.lineno}")
    assert not violations, f"compile.py must never build SQL via f-string/.format(): {violations}"


def test_belt_check_rejects_non_select():
    with pytest.raises(compiler.BeltCheckError):
        compiler.belt_check("DELETE FROM orders")


def test_belt_check_rejects_semicolon():
    with pytest.raises(compiler.BeltCheckError):
        compiler.belt_check("SELECT 1; SELECT 2")


def test_belt_check_rejects_multi_statement_without_semicolon_keyword_sniff():
    with pytest.raises(compiler.BeltCheckError):
        compiler.belt_check("SELECT 1 UNION ALL DROP TABLE orders")


def test_belt_check_accepts_plain_select():
    compiler.belt_check("SELECT 1 AS value")


def test_belt_check_accepts_with_cte():
    compiler.belt_check("WITH a AS (SELECT 1) SELECT * FROM a")


def test_finalize_appends_outer_limit():
    finalized = compiler.finalize_for_execution("SELECT 1 AS value", [])
    assert re.search(r"LIMIT\s+500", finalized.sql)
    assert finalized.sql.count(";") == 0


# --------------------------------------------------------------------------
# metric_query — aggregate
# --------------------------------------------------------------------------

def test_metric_query_otif_aggregate(con):
    compiled = _validate_and_compile(compiler.compile_metric_query, {
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    row = con.execute(finalized.sql, finalized.params).fetchone()
    assert row[0] == pytest.approx(100.0 / 3, abs=0.01)  # 1 of 3 orders is OTIF


def test_metric_query_zero_denominator_returns_null_not_zero(con):
    # Bypasses validate.py's resolve step on purpose: resolve.py's catalog is
    # the REAL supplier roster (Anadolu et al.), not this file's synthetic
    # "SUP-01"/"SUP-02" test suppliers, so it has nothing to fuzzy-match
    # against here — compile.py is meant to receive already-resolved
    # canonical ids directly, which is exactly what this test hands it.
    parsed = spec.parse_spec({
        "spec_type": "metric_query", "metric": "avg_supplier_lead_time",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    compiled = compiler.compile_metric_query(parsed, {"supplier": ["SUP-01"], "dc": ["AUH"]})
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    row = con.execute(finalized.sql, finalized.params).fetchone()
    assert row[0] is None


def test_metric_query_uses_bound_parameters_not_literals(con):
    compiled = _validate_and_compile(compiler.compile_metric_query, {
        "spec_type": "metric_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "filters": [{"dimension": "category", "values": ["home_care"]}],
    })
    assert "home_care" not in compiled.sql
    assert "?" in compiled.sql
    assert "home_care" in compiled.params


# --------------------------------------------------------------------------
# metric_query — series with an explicit-null empty bucket
# --------------------------------------------------------------------------

def test_metric_query_series_includes_explicit_null_for_empty_bucket(con):
    compiled = _validate_and_compile(compiler.compile_metric_query, {
        "spec_type": "metric_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-01", "end": "2026-03"},
        "time_grain": "month",
    })
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()
    by_bucket = {str(r[0])[:7]: r[1] for r in rows}
    assert by_bucket["2026-01"] is None
    assert by_bucket["2026-02"] == pytest.approx(150.0)
    assert by_bucket["2026-03"] == pytest.approx(290.0)


# --------------------------------------------------------------------------
# breakdown_query — members + others == total
# --------------------------------------------------------------------------

def test_breakdown_query_members_plus_others_equals_total(con):
    compiled = _validate_and_compile(compiler.compile_breakdown_query, {
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "dimension": "category", "top_n": 2, "sort": "desc",
    })
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()
    by_member = {r[0]: r[1] for r in rows}
    assert by_member["home_care"] == pytest.approx(150.0)
    assert by_member["food_beverage"] == pytest.approx(100.0)
    assert by_member["All others"] == pytest.approx(40.0)
    members_sum = by_member["home_care"] + by_member["food_beverage"] + by_member["All others"]
    assert members_sum == pytest.approx(by_member["Total"])
    assert by_member["Total"] == pytest.approx(290.0)


def test_breakdown_query_ratio_metric_others_bucket_is_re_divided_not_averaged(con):
    # otif_pct by category, top_n=1: the folded "All others" rate must come
    # from SUM(num)/SUM(den) across the folded members, not an average of
    # their individual rates (the exact bug fixtures/otif_overlap_fixture
    # exists to catch, here applied to the breakdown fold instead).
    compiled = _validate_and_compile(compiler.compile_breakdown_query, {
        "spec_type": "breakdown_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "dimension": "category", "top_n": 1, "sort": "desc",
    })
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()
    by_member = {r[0]: r[1] for r in rows}
    # home_care (ORD-1) is the only OTIF order -> its own rate is 100.0 and
    # it's the single top_n=1 member; food_beverage + personal_care fold
    # into "All others", both non-OTIF -> re-divided rate must be 0.0.
    assert by_member["home_care"] == pytest.approx(100.0)
    assert by_member["All others"] == pytest.approx(0.0)


# --------------------------------------------------------------------------
# change_decomposition — full member set, raw numerators/denominators only
# --------------------------------------------------------------------------

def test_change_decomposition_preserves_full_member_set(con):
    compiled = _validate_and_compile(compiler.compile_change_decomposition, {
        "spec_type": "change_decomposition", "metric": "revenue", "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()
    columns = [d[0] for d in con.description]
    by_member = {r[0]: dict(zip(columns[1:], r[1:])) for r in rows}

    assert set(by_member.keys()) == {"home_care", "food_beverage", "personal_care"}
    # home_care present in BOTH periods.
    assert by_member["home_care"]["num_a"] == pytest.approx(150.0)
    assert by_member["home_care"]["num_b"] == pytest.approx(150.0)
    # food_beverage and personal_care absent from period_a but present in b —
    # full member set preserved means they still appear, with num_a as 0 (or
    # null, coalesced).
    assert (by_member["food_beverage"]["num_a"] or 0) == pytest.approx(0.0)
    assert by_member["food_beverage"]["num_b"] == pytest.approx(100.0)
    assert (by_member["personal_care"]["num_a"] or 0) == pytest.approx(0.0)
    assert by_member["personal_care"]["num_b"] == pytest.approx(40.0)


def test_change_decomposition_returns_raw_numbers_only_no_precomputed_ratio(con):
    compiled = _validate_and_compile(compiler.compile_change_decomposition, {
        "spec_type": "change_decomposition", "metric": "otif_pct", "dimension": "supplier",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    columns_lower = compiled.sql.lower()
    assert "num_a" in columns_lower and "den_a" in columns_lower
    assert "num_b" in columns_lower and "den_b" in columns_lower
