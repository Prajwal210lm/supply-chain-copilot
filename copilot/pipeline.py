"""End-to-end question pipeline: Stage 1 -> compile -> execute -> decompose
(where needed) -> narrate. This module adds no new query logic of its own —
every step below calls into a module built in Steps 1-4 (stage1, compile,
decompose, results, narrate); this file only orchestrates and shapes what
comes back into one PipelineResult.

run_question() is the single entry point copilot/api.py calls. For a
clarification or refusal outcome (whether model-authored or synthesized by
validate.py's V2-V6 rules or resolve.py's V5 ambiguity check) it returns
immediately after Stage 1 — spec and usage only, no compile/execute/narrate.
"""

import dataclasses
from dataclasses import dataclass

from copilot import compile as compiler
from copilot import constants as C
from copilot import dateutil as D
from copilot import db, decompose, narrate, registry, results, stage1, validate

# Same per-MTok pricing eval/harness.py uses for claude-sonnet-4-6 — kept as
# a small duplicated constant rather than a cross-module import, since it's
# two float literals, not shared logic.
COST_PER_MTOK_INPUT_USD = 3.00
COST_PER_MTOK_OUTPUT_USD = 15.00

_PERIOD_GRAIN_LABEL = {"month": "monthly", "week": "weekly"}

# Additive decomposable metrics that are currency-valued need integer "fils"
# (AED x100) arithmetic in decompose.py so the residual gate can require
# EXACT zero rather than "close to zero" — see decompose.py's module
# docstring. order_count/stockout_count are already integers and need no
# scaling; the ratio-metric family (otif_pct et al.) goes through
# decompose_ratio instead, which is float-native by design.
_CURRENCY_ADDITIVE_METRICS = frozenset({"revenue", "inventory_value"})


# --------------------------------------------------------------------------
# Result shapes
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class PipelineResult:
    outcome_kind: str  # "answer" | "clarification" | "refusal"
    spec: dict
    usage: PipelineUsage
    result: object | None = None
    narration: str | None = None
    withheld_reason: str | None = None
    chart_spec: object | None = None
    echo_bar: str | None = None
    query_sql: str | None = None


def _make_usage(input_tokens: int, output_tokens: int) -> PipelineUsage:
    cost = (input_tokens / 1_000_000) * COST_PER_MTOK_INPUT_USD + (output_tokens / 1_000_000) * COST_PER_MTOK_OUTPUT_USD
    return PipelineUsage(input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)


def to_plain_dict(obj):
    """Recursively turns a results.py/chart.py dataclass tree into plain
    dicts/lists — the JSON-safe form api.py puts on the wire. Pipeline
    internals keep the live dataclasses; this is only for the boundary."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_plain_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, tuple):
        return [to_plain_dict(item) for item in obj]
    return obj


# --------------------------------------------------------------------------
# Outcome classification — Stage 1 can hand back three different shapes
# (validate.Accepted wrapping any of the five spec types, validate.Rejected,
# or validate.NeedsClarification); this collapses all of that into exactly
# one of "answer" / "clarification" / "refusal" plus a plain dict, so the
# rest of the pipeline (and api.py) never has to branch on outcome type.
# --------------------------------------------------------------------------

def _classify_outcome(outcome):
    if isinstance(outcome, validate.Rejected):
        return "refusal", {"reason_code": outcome.reason_code, "message": outcome.message, "suggestions": []}
    if isinstance(outcome, validate.NeedsClarification):
        return "clarification", {"question": outcome.question, "options": outcome.options, "pending_context": outcome.pending_context}

    parsed = outcome.spec
    if parsed.spec_type == "clarification":
        return "clarification", parsed.model_dump(exclude_none=True)
    if parsed.spec_type == "refusal":
        return "refusal", parsed.model_dump(exclude_none=True)
    return "answer", outcome


# --------------------------------------------------------------------------
# Echo bar — deterministic, built only from the validated spec, never from
# model text (Rule 4 of narrate_system.md leans on this: the paragraph must
# not repeat what's already here). Period formatting itself lives in
# copilot.dateutil.period_label — the result contract (results.py) uses the
# exact same formatter, so a period reads identically in the echo bar and in
# a narration placeholder.
# --------------------------------------------------------------------------

def _needs_line_grain_note(parsed) -> bool:
    dimension = getattr(parsed, "dimension", None)
    if dimension is None:
        return False
    variant = registry.get_metric(parsed.metric).line_grain_variant
    return variant is not None and dimension in variant.triggers


def _describe_filters(filters) -> str:
    return ", ".join(f.dimension + "=" + "/".join(f.values) for f in filters)


def build_echo_bar(parsed) -> str:
    if parsed.spec_type not in ("metric_query", "breakdown_query", "change_decomposition"):
        raise ValueError(f"pipeline.build_echo_bar: no echo bar for spec_type={parsed.spec_type!r}")

    metric_name = registry.get_metric(parsed.metric).display_name
    parts = [metric_name]

    if parsed.spec_type == "metric_query":
        parts.append(D.period_label(parsed.period))
        if parsed.time_grain:
            parts.append(_PERIOD_GRAIN_LABEL.get(parsed.time_grain, parsed.time_grain))
    elif parsed.spec_type == "breakdown_query":
        parts.append(D.period_label(parsed.period))
        parts.append("by " + parsed.dimension)
    else:
        parts.append(D.period_label(parsed.period_b) + " vs " + D.period_label(parsed.period_a))
        parts.append("by " + parsed.dimension)

    if _needs_line_grain_note(parsed):
        parts.append("line grain")

    filters = getattr(parsed, "filters", None)
    if filters:
        parts.append(_describe_filters(filters))

    return ", ".join(parts)


# --------------------------------------------------------------------------
# Compile -> execute -> (decompose) -> results object
# --------------------------------------------------------------------------

def _format_bucket(value, time_grain: str) -> str:
    if isinstance(value, str):
        return value
    if time_grain == "week":
        iso_year, iso_week, _ = value.isocalendar()
        return "%04d-W%02d" % (iso_year, iso_week)
    return value.strftime("%Y-%m")


def _run_metric_query(con, parsed, resolved_filters):
    compiled = compiler.compile_metric_query(parsed, resolved_filters)
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()

    if parsed.time_grain is None:
        value = rows[0][0] if rows else None
        result_obj = results.build_metric_query_result(parsed.metric, value, parsed.period)
    else:
        points = [(_format_bucket(r[0], parsed.time_grain), r[1]) for r in rows]
        result_obj = results.build_series_result(parsed.metric, points)
    return compiled.sql, result_obj


def _run_breakdown_query(con, parsed, resolved_filters):
    compiled = compiler.compile_breakdown_query(parsed, resolved_filters)
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()

    member_rows = [(member, value) for member, value in rows if member != compiler.TOTAL_LABEL]
    total = next(value for member, value in rows if member == compiler.TOTAL_LABEL)
    result_obj = results.build_breakdown_result(parsed.metric, parsed.dimension, member_rows, total, parsed.period)
    return compiled.sql, result_obj


def _run_change_decomposition(con, parsed, resolved_filters):
    compiled = compiler.compile_change_decomposition(parsed, resolved_filters)
    finalized = compiler.finalize_for_execution(compiled.sql, compiled.params)
    rows = con.execute(finalized.sql, finalized.params).fetchall()

    entry = registry.get_metric(parsed.metric)
    if entry.denominator is not None:
        decomposed = decompose.decompose_ratio([(r[0], r[1], r[2], r[3], r[4]) for r in rows])
    else:
        scale = 100 if parsed.metric in _CURRENCY_ADDITIVE_METRICS else 1
        additive_rows = [(r[0], round(r[1] * scale), round(r[3] * scale)) for r in rows]
        decomposed = decompose.decompose_additive(additive_rows)
        if scale != 1:
            decomposed = _rescale_additive_result(decomposed, scale)

    result_obj = results.build_decomposition_result(parsed.metric, parsed.dimension, decomposed, parsed.period_a, parsed.period_b)
    return compiled.sql, result_obj


def _rescale_additive_result(decomposed, scale: int):
    """Undoes the fils (x100) scaling decompose_additive needed for an exact
    residual check, back into the metric's natural AED units."""
    members = tuple(
        decompose.AdditiveMemberContribution(
            member=m.member, value_a=m.value_a / scale, value_b=m.value_b / scale, contribution=m.contribution / scale,
        )
        for m in decomposed.members
    )
    return decompose.AdditiveDecompositionResult(
        members=members,
        total_a=decomposed.total_a / scale, total_b=decomposed.total_b / scale,
        delta=decomposed.delta / scale,
        sum_of_contributions=decomposed.sum_of_contributions / scale,
        residual=decomposed.residual / scale,
        residual_ok=decomposed.residual_ok,
        withheld=decomposed.withheld,
        withheld_reason=decomposed.withheld_reason,
    )


_RUNNERS = {
    "metric_query": _run_metric_query,
    "breakdown_query": _run_breakdown_query,
    "change_decomposition": _run_change_decomposition,
}


def _compile_and_execute(parsed, resolved_filters, db_path):
    con = db.connect(db_path)
    try:
        return _RUNNERS[parsed.spec_type](con, parsed, resolved_filters)
    finally:
        con.close()


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def run_question(question: str, context_turns=None, db_path=None, client_instance=None) -> PipelineResult:
    db_path = db_path if db_path is not None else C.DB_PATH

    stage1_result = stage1.run_stage1(question, context_turns=context_turns, client_instance=client_instance)
    total_in = stage1_result.usage.input_tokens
    total_out = stage1_result.usage.output_tokens

    kind, payload = _classify_outcome(stage1_result.outcome)

    if kind != "answer":
        return PipelineResult(outcome_kind=kind, spec=payload, usage=_make_usage(total_in, total_out))

    accepted = payload
    parsed = accepted.spec

    query_sql, result_obj = _compile_and_execute(parsed, accepted.resolved_filters, db_path)
    echo_bar = build_echo_bar(parsed)

    narration_result = narrate.run_narrate(parsed, result_obj, client_instance=client_instance)
    total_in += narration_result.usage.input_tokens
    total_out += narration_result.usage.output_tokens

    return PipelineResult(
        outcome_kind="answer",
        spec=parsed.model_dump(exclude_none=True),
        usage=_make_usage(total_in, total_out),
        result=result_obj,
        narration=narration_result.paragraph,
        withheld_reason=narration_result.withheld_reason,
        chart_spec=narration_result.chart_spec,
        echo_bar=echo_bar,
        query_sql=query_sql,
    )
