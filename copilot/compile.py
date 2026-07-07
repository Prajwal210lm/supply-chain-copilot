"""Spec -> SQL. The four shapes:

  metric_query (no time_grain)  -> one row, numerator/denominator or a sum.
  metric_query (time_grain set) -> a series, LEFT JOINed onto a VALUES
                                    bucket spine so empty buckets appear as
                                    explicit NULLs rather than missing rows.
  breakdown_query                -> ranked members, a case-folded "All
                                    others" rollup, and a grand total — all
                                    from one re-divided sum, so
                                    members + others == total by construction.
  change_decomposition           -> one row per member of the UNION of both
                                    periods' members, with raw num_a/den_a/
                                    num_b/den_b columns. No ratio, no share,
                                    no contribution — decompose.py computes
                                    all of that in Python from these raw
                                    numbers.

TWO-CHANNEL RULE: every value that came from the spec or from resolve.py
(canonical ids, date bounds, top_n, sort direction, month/week unit labels)
is bound as a DuckDB query parameter (`?`), collected into `params` as this
module runs, never written into the SQL text. The only strings written
directly into SQL text are:
  (a) fragments from copilot.registry (base relations, column names,
      numerator/denominator expressions) — these are Python string literals
      this project's own source code wrote, never spec-derived text, and
      (b) small compiler-authored constants (the "All others" / "Total"
      labels, CTE names, the outer LIMIT number) that never vary with input.
This module never uses an f-string or `.format()` call to build SQL — every
piece of SQL text below is built with `+` concatenation of the two kinds of
string described above, which keeps that invariant mechanically checkable
(tests/test_compile.py's structural test greps the AST for both and fails
if it finds either, anywhere in this file).
"""

import threading
from dataclasses import dataclass, field

import duckdb

from copilot import dateutil as D
from copilot import registry

DEFAULT_ROW_LIMIT = 500
DEFAULT_TIMEOUT_SECONDS = 5.0

_PERCENTAGE_METRICS = frozenset({"otif_pct", "on_time_pct", "in_full_pct", "fill_rate_pct"})
_SORT_DIRECTION_SQL = {"asc": "ASC", "desc": "DESC"}
_TRUNC_UNIT = {"month": "month", "week": "week"}

OTHERS_LABEL = "All others"
TOTAL_LABEL = "Total"


class BeltCheckError(Exception):
    pass


@dataclass
class CompiledQuery:
    sql: str
    params: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Belt check + execution wrapper
# --------------------------------------------------------------------------

_FORBIDDEN_KEYWORDS = (
    "insert ", "update ", "delete ", "drop ", "alter ", "attach ", "detach ",
    "copy ", "create ", "pragma ", "call ", "export ", "import ", "vacuum ",
    "checkpoint ", "load ",
)


def belt_check(sql: str) -> None:
    stripped = sql.strip()
    if not stripped:
        raise BeltCheckError("empty statement")
    if ";" in stripped:
        raise BeltCheckError("semicolons are not allowed")
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise BeltCheckError("statement must start with SELECT or WITH")
    padded = " " + lowered + " "
    for keyword in _FORBIDDEN_KEYWORDS:
        if keyword in padded:
            raise BeltCheckError("forbidden keyword in statement: " + keyword.strip())


def finalize_for_execution(sql: str, params: list, limit: int = DEFAULT_ROW_LIMIT) -> CompiledQuery:
    belt_check(sql)
    wrapped = "SELECT * FROM (\n" + sql + "\n) AS _compiled_outer LIMIT " + str(int(limit))
    return CompiledQuery(sql=wrapped, params=list(params))


def execute(con: duckdb.DuckDBPyConnection, compiled: CompiledQuery, timeout_s: float = DEFAULT_TIMEOUT_SECONDS):
    timer = threading.Timer(timeout_s, con.interrupt)
    timer.start()
    try:
        result = con.execute(compiled.sql, compiled.params)
        rows = result.fetchall()
        columns = [d[0] for d in result.description]
    finally:
        timer.cancel()
    return rows, columns


# --------------------------------------------------------------------------
# Relation selection + shared fragment builders
# --------------------------------------------------------------------------

def _select_relation(entry: registry.MetricEntry, dims_in_play: set):
    variant = entry.line_grain_variant
    if variant is not None and (dims_in_play & variant.triggers):
        return variant.base_relation_sql, variant.dimension_columns, variant.numerator, variant.denominator
    return entry.base_relation_sql, entry.dimension_columns, entry.numerator, entry.denominator


def _period_where(period_column: str, period_column_type: str, period, params: list) -> str:
    if period_column_type == "date":
        start_date, end_date = D.period_to_date_range(period)
        params.append(start_date)
        params.append(end_date)
    else:
        params.append(period.start)
        params.append(period.end)
    return period_column + " BETWEEN ? AND ?"


def _filter_where(dimension_columns: dict, resolved_filters: dict, params: list) -> list:
    clauses = []
    for dimension, ids in resolved_filters.items():
        column = dimension_columns[dimension]
        placeholders = ", ".join(["?"] * len(ids))
        clauses.append(column + " IN (" + placeholders + ")")
        params.extend(ids)
    return clauses


def _wrap_where(clauses: list) -> str:
    return " AND ".join(clauses) if clauses else "TRUE"


def _ratio_value_sql(metric_key: str, num_col: str, den_col: str, has_denominator: bool) -> str:
    if not has_denominator:
        return num_col
    expr = "((" + num_col + ") * 1.0 / NULLIF(" + den_col + ", 0))"
    if metric_key in _PERCENTAGE_METRICS:
        expr = expr + " * 100.0"
    return expr


def _dims_in_play(parsed, resolved_filters: dict) -> set:
    dims = set(resolved_filters.keys())
    dimension = getattr(parsed, "dimension", None)
    if dimension is not None:
        dims.add(dimension)
    return dims


# --------------------------------------------------------------------------
# metric_query
# --------------------------------------------------------------------------

def compile_metric_query(parsed, resolved_filters: dict) -> CompiledQuery:
    entry = registry.get_metric(parsed.metric)
    dims_in_play = _dims_in_play(parsed, resolved_filters)
    relation_sql, dim_cols, numerator, denominator = _select_relation(entry, dims_in_play)

    params: list = []
    where_clauses = [_period_where(entry.period_column, entry.period_column_type, parsed.period, params)]
    where_clauses.extend(_filter_where(dim_cols, resolved_filters, params))
    where_sql = _wrap_where(where_clauses)

    if parsed.time_grain is None:
        return _compile_metric_aggregate(entry, relation_sql, numerator, denominator, where_sql, params)
    return _compile_metric_series(entry, parsed, relation_sql, numerator, denominator, where_sql, params)


def _compile_metric_aggregate(entry, relation_sql, numerator, denominator, where_sql, params) -> CompiledQuery:
    num_sql = numerator.sql
    den_sql = denominator.sql if denominator else None
    value_sql = _ratio_value_sql(entry.key, num_sql, den_sql, den_sql is not None)

    sql = (
        "SELECT " + value_sql + " AS value\n"
        + "FROM (\n" + relation_sql + "\n) AS base\n"
        + "WHERE " + where_sql
    )
    return CompiledQuery(sql=sql, params=params)


def _compile_metric_series(entry, parsed, relation_sql, numerator, denominator, where_sql, params) -> CompiledQuery:
    has_den = denominator is not None
    value_sql = _ratio_value_sql(entry.key, "agg.num_val", "agg.den_val", has_den)

    agg_params: list = []
    if entry.period_column_type == "month_str":
        buckets = D.month_range(parsed.period.start, parsed.period.end)
        bucket_expr = entry.period_column
    else:
        buckets = D.month_starts(parsed.period) if parsed.time_grain == "month" else D.week_starts(parsed.period)
        agg_params.append(_TRUNC_UNIT[parsed.time_grain])
        bucket_expr = "CAST(date_trunc(?, " + entry.period_column + ") AS DATE)"

    spine_placeholders = ", ".join(["(?)"] * len(buckets))
    spine_sql = "(VALUES " + spine_placeholders + ") AS spine(bucket)"
    spine_params = list(buckets)

    agg_select_num = numerator.filtered_sql(None)
    agg_select_den = denominator.filtered_sql(None) if denominator else "1"

    inner = (
        "SELECT " + bucket_expr + " AS bucket, "
        + agg_select_num + " AS num_val, "
        + agg_select_den + " AS den_val\n"
        + "FROM (\n" + relation_sql + "\n) AS base\n"
        + "WHERE " + where_sql + "\n"
        + "GROUP BY 1"
    )

    sql = (
        "SELECT spine.bucket AS bucket, " + value_sql + " AS value\n"
        + "FROM " + spine_sql + "\n"
        + "LEFT JOIN (\n" + inner + "\n) AS agg ON agg.bucket = spine.bucket\n"
        + "ORDER BY spine.bucket"
    )
    # Textual placeholder order: spine's VALUES clause (in the outer FROM,
    # which appears first) precedes the LEFT JOINed inner query's own
    # date_trunc unit + WHERE-clause params.
    all_params = spine_params + agg_params + params
    return CompiledQuery(sql=sql, params=all_params)


# --------------------------------------------------------------------------
# breakdown_query
# --------------------------------------------------------------------------

def compile_breakdown_query(parsed, resolved_filters: dict) -> CompiledQuery:
    entry = registry.get_metric(parsed.metric)
    dims_in_play = _dims_in_play(parsed, resolved_filters)
    relation_sql, dim_cols, numerator, denominator = _select_relation(entry, dims_in_play)
    member_col = dim_cols[parsed.dimension]

    params: list = []
    where_clauses = [_period_where(entry.period_column, entry.period_column_type, parsed.period, params)]
    where_clauses.extend(_filter_where(dim_cols, resolved_filters, params))
    where_sql = _wrap_where(where_clauses)

    num_sql = numerator.filtered_sql(None)
    den_sql = denominator.filtered_sql(None) if denominator else "1"
    has_den = denominator is not None

    agg_cte = (
        "agg AS (\n"
        + "SELECT " + member_col + " AS member, " + num_sql + " AS num_val, " + den_sql + " AS den_val\n"
        + "FROM (\n" + relation_sql + "\n) AS base\n"
        + "WHERE " + where_sql + "\n"
        + "GROUP BY " + member_col + "\n"
        + ")"
    )

    ranked_value_sql = _ratio_value_sql(entry.key, "num_val", "den_val", has_den)
    sort_dir = _SORT_DIRECTION_SQL[parsed.sort]
    params.append(parsed.top_n)

    ranked_cte = (
        "ranked AS (\n"
        + "SELECT member, num_val, den_val,\n"
        + "ROW_NUMBER() OVER (ORDER BY " + ranked_value_sql + " " + sort_dir + " NULLS LAST) AS rn\n"
        + "FROM agg\n"
        + ")"
    )

    folded_cte = (
        "folded AS (\n"
        + "SELECT CASE WHEN rn <= ? THEN member ELSE '" + OTHERS_LABEL + "' END AS member,\n"
        + "SUM(num_val) AS num_val, SUM(den_val) AS den_val\n"
        + "FROM ranked\n"
        + "GROUP BY 1\n"
        + ")"
    )

    final_value_sql = _ratio_value_sql(entry.key, "num_val", "den_val", has_den)

    sql = (
        "WITH " + agg_cte + ",\n" + ranked_cte + ",\n" + folded_cte + "\n"
        + "SELECT member, " + final_value_sql + " AS value FROM folded\n"
        + "UNION ALL\n"
        + "SELECT '" + TOTAL_LABEL + "' AS member, " + final_value_sql + " AS value\n"
        + "FROM (SELECT SUM(num_val) AS num_val, SUM(den_val) AS den_val FROM folded) AS grand_total"
    )
    return CompiledQuery(sql=sql, params=params)


# --------------------------------------------------------------------------
# change_decomposition
# --------------------------------------------------------------------------

def compile_change_decomposition(parsed, resolved_filters: dict) -> CompiledQuery:
    entry = registry.get_metric(parsed.metric)
    dims_in_play = _dims_in_play(parsed, resolved_filters)
    relation_sql, dim_cols, numerator, denominator = _select_relation(entry, dims_in_play)
    member_col = dim_cols[parsed.dimension]

    filter_params: list = []
    filter_clauses = _filter_where(dim_cols, resolved_filters, filter_params)

    a_start, a_end = _period_bounds_for_type(entry.period_column_type, parsed.period_a)
    b_start, b_end = _period_bounds_for_type(entry.period_column_type, parsed.period_b)

    # Restrict to rows in EITHER period (plus any filters) before tagging,
    # so the GROUP BY below never has to look at rows outside both windows.
    window_sql = (
        "((" + entry.period_column + " BETWEEN ? AND ?) OR (" + entry.period_column + " BETWEEN ? AND ?))"
    )
    tagged_where_sql = _wrap_where([window_sql] + filter_clauses)

    # `* ` carries every column the base relation exposes (on_time,
    # qty_delivered, ...) through untouched, so num_a/den_a below can FILTER
    # on the metric's own condition AND the period tag in one FILTER clause.
    tagged_sql = (
        "SELECT " + member_col + " AS member,\n"
        + "(" + entry.period_column + " BETWEEN ? AND ?) AS in_a,\n"
        + "(" + entry.period_column + " BETWEEN ? AND ?) AS in_b,\n"
        + "*\n"
        + "FROM (\n" + relation_sql + "\n) AS base\n"
        + "WHERE " + tagged_where_sql
    )

    num_a = numerator.filtered_sql("in_a")
    den_a = denominator.filtered_sql("in_a") if denominator else "COUNT(*) FILTER (WHERE in_a)"
    num_b = numerator.filtered_sql("in_b")
    den_b = denominator.filtered_sql("in_b") if denominator else "COUNT(*) FILTER (WHERE in_b)"

    grouped_sql = (
        "SELECT member,\n"
        + num_a + " AS num_a, " + den_a + " AS den_a,\n"
        + num_b + " AS num_b, " + den_b + " AS den_b\n"
        + "FROM (\n" + tagged_sql + "\n) AS tagged\n"
        + "GROUP BY member"
    )

    # Placeholder order must match their textual order: in_a, in_b (in the
    # SELECT list), then the OR'd window (in the WHERE clause), then filters.
    all_params = [a_start, a_end, b_start, b_end] + [a_start, a_end, b_start, b_end] + filter_params
    return CompiledQuery(sql=grouped_sql, params=all_params)


def _period_bounds_for_type(period_column_type: str, period):
    if period_column_type == "date":
        return D.period_to_date_range(period)
    return period.start, period.end
