"""V1-V6 spec validation. Runs strictly after spec.py's structural parse
would otherwise be the only gate; this module adds the layers that need
project knowledge spec.py doesn't have (the registry's compatibility matrix
and decomposable flags, the data window, entity resolution).

Rule numbering (matches the brief):
  V1  structural            — Pydantic union parse / unknown fields
  V2  compatibility         — breakdown/decomposition dimension AND every
                               filter dimension, checked against the registry
  V3  decomposable flag     — change_decomposition only
  V4  period bounds         — inside the data window, start <= end, week
                               grain capped at 26 weeks, decomposition
                               periods non-overlapping and non-identical
  V5  resolution            — delegates to resolve.py
  V6  caps                  — top_n range, filter count, values count,
                               duplicate filter dimensions

V1 and V6 are BOTH enforced by spec.py/Pydantic in a single parse pass (the
caps are part of docs/SPEC.md's grammar, not a separate business rule, so
there is exactly one place that rejects them). This module's job for V1/V6
is to correctly LABEL which one fired, by inspecting the Pydantic error —
never to re-implement the check.

V7 (retry orchestration) is Stage 1's job, not this module's — that's the
NL layer deciding whether to re-prompt, not this deterministic gate.
"""

from dataclasses import dataclass, field

from pydantic import ValidationError

from copilot import dateutil as D
from copilot import registry, resolve, spec
from copilot import constants as C

_V6_TOP_N_MARKER = "top_n"
_V6_FILTER_COUNT_MARKER = "max 3 filters"
_V6_DUPLICATE_DIM_MARKER = "duplicate filter dimensions"


@dataclass(frozen=True)
class Accepted:
    spec: object
    resolved_filters: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Rejected:
    rule: str
    reason_code: str | None
    message: str


@dataclass(frozen=True)
class NeedsClarification:
    rule: str
    question: str
    options: list[str]
    pending_context: dict


ValidationOutcome = Accepted | Rejected | NeedsClarification


def _classify_structural_error(exc: ValidationError) -> str:
    for err in exc.errors():
        loc_str = ".".join(str(p) for p in err["loc"])
        msg = err.get("msg", "")
        if _V6_TOP_N_MARKER in loc_str:
            return "V6"
        if _V6_FILTER_COUNT_MARKER in msg or _V6_DUPLICATE_DIM_MARKER in msg:
            return "V6"
        if loc_str.endswith(".values") or loc_str.endswith("values"):
            if "at most" in msg or "at least" in msg:
                return "V6"
    return "V1"


def _check_compatibility(parsed) -> Rejected | None:
    entry = registry.get_metric(parsed.metric)
    dims_to_check = []
    dimension = getattr(parsed, "dimension", None)
    if dimension is not None:
        dims_to_check.append(dimension)
    time_grain = getattr(parsed, "time_grain", None)
    if time_grain is not None:
        dims_to_check.append(time_grain)
    filters = getattr(parsed, "filters", None) or []
    dims_to_check.extend(f.dimension for f in filters)
    for d in dims_to_check:
        if d not in entry.compatible_dimensions:
            return Rejected(
                rule="V2", reason_code="incompatible_pair",
                message=f"{parsed.metric} cannot be cut or filtered by {d}.",
            )
    return None


def _check_decomposable(parsed) -> Rejected | None:
    if parsed.spec_type != "change_decomposition":
        return None
    entry = registry.get_metric(parsed.metric)
    if not entry.decomposable:
        return Rejected(
            rule="V3", reason_code="not_decomposable",
            message=f"{parsed.metric} is not decomposable.",
        )
    return None


def _check_period_bounds(period, label: str) -> Rejected | None:
    if period.start > period.end:
        return Rejected(rule="V4", reason_code=None, message=f"{label}: start ({period.start}) is after end ({period.end}).")

    window_start, _ = D.month_to_date_range(C.WINDOW_START_MONTH)
    _, window_end = D.month_to_date_range(C.WINDOW_END_MONTH)
    p_start, p_end = D.period_to_date_range(period)
    if p_start < window_start or p_end > window_end:
        return Rejected(
            rule="V4", reason_code="out_of_window",
            message=f"{label} falls outside the data window {C.WINDOW_START_MONTH}..{C.WINDOW_END_MONTH}.",
        )

    if period.grain == "week" and D.week_span_count(period) > 26:
        return Rejected(
            rule="V4", reason_code="out_of_window",
            message=f"{label} spans more than 26 weeks at week grain; ask again at month grain instead.",
        )
    return None


def _check_decomposition_periods_distinct(period_a, period_b) -> Rejected | None:
    a_start, a_end = D.period_to_date_range(period_a)
    b_start, b_end = D.period_to_date_range(period_b)
    if a_start == b_start and a_end == b_end:
        return Rejected(rule="V4", reason_code=None, message="period_a and period_b are identical.")
    if a_start <= b_end and b_start <= a_end:
        return Rejected(rule="V4", reason_code=None, message="period_a and period_b overlap.")
    return None


def _check_and_resolve_filters(parsed) -> tuple[Rejected | NeedsClarification | None, dict[str, list[str]]]:
    filters = getattr(parsed, "filters", None)
    if not filters:
        return None, {}

    resolved: dict[str, list[str]] = {}
    for f in filters:
        ids: list[str] = []
        for value in f.values:
            outcome = resolve.resolve_entity(f.dimension, value)
            if isinstance(outcome, resolve.Unresolvable):
                return Rejected(
                    rule="V5", reason_code="unresolvable_filter",
                    message=f"Could not resolve {f.dimension}={value!r} to a known entity.",
                ), {}
            if isinstance(outcome, resolve.NeedsClarification):
                options = [c.display for c in outcome.candidates]
                return NeedsClarification(
                    rule="V5",
                    question=f"Which {f.dimension} did you mean by {value!r}?",
                    options=options,
                    pending_context={},
                ), {}
            ids.append(outcome.canonical_id)
        resolved[f.dimension] = ids
    return None, resolved


def validate(raw: dict) -> ValidationOutcome:
    try:
        parsed = spec.parse_spec(raw)
    except ValidationError as exc:
        rule = _classify_structural_error(exc)
        return Rejected(rule=rule, reason_code=None, message=str(exc))

    if parsed.spec_type in ("clarification", "refusal"):
        return Accepted(spec=parsed, resolved_filters={})

    rejection = _check_compatibility(parsed)
    if rejection is not None:
        return rejection

    rejection = _check_decomposable(parsed)
    if rejection is not None:
        return rejection

    if parsed.spec_type == "change_decomposition":
        rejection = _check_period_bounds(parsed.period_a, "period_a") or _check_period_bounds(parsed.period_b, "period_b")
        if rejection is not None:
            return rejection
        rejection = _check_decomposition_periods_distinct(parsed.period_a, parsed.period_b)
        if rejection is not None:
            return rejection
    else:
        rejection = _check_period_bounds(parsed.period, "period")
        if rejection is not None:
            return rejection

    outcome, resolved_filters = _check_and_resolve_filters(parsed)
    if outcome is not None:
        return outcome

    return Accepted(spec=parsed, resolved_filters=resolved_filters)
