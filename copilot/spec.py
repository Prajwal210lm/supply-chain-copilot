"""Pydantic models for the five-type QuerySpec envelope defined in
docs/SPEC.md. This module is purely structural (V1 in validate.py's
numbering) — it rejects malformed shapes (unknown fields, wrong types, an
out-of-range top_n, a bad ISO period string) but knows nothing about the
registry, the data window, or resolvable entities. Compatibility (V2),
decomposability (V3), period-bounds/window checks (V4), and entity
resolution (V5) all live in validate.py / resolve.py and run AFTER a spec
has already parsed successfully here.

METRIC_KEYS and DIMENSION_KEYS are hardcoded tuples, not read live from
copilot.registry, because Pydantic's Literal needs static values. They are
the one thing in this file that could drift from the registry, so
tests/test_spec.py cross-checks METRIC_KEYS against registry.METRICS.keys()
on every run.
"""

import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

METRIC_KEYS = (
    "otif_pct", "on_time_pct", "in_full_pct", "fill_rate_pct", "revenue",
    "order_count", "avg_order_value", "inventory_value", "days_of_cover",
    "stockout_count", "avg_supplier_lead_time",
)
DIMENSION_KEYS = ("month", "week", "dc", "emirate", "category", "customer_segment", "supplier")
FILTER_DIMENSION_KEYS = ("dc", "emirate", "category", "customer_segment", "supplier")
REASON_CODE_KEYS = (
    "out_of_catalog", "incompatible_pair", "not_decomposable", "out_of_window",
    "unresolvable_filter", "not_a_data_question", "unsafe_request",
)

Metric = Literal[METRIC_KEYS]
Dimension = Literal[DIMENSION_KEYS]
FilterDimension = Literal[FILTER_DIMENSION_KEYS]
ReasonCode = Literal[REASON_CODE_KEYS]
Grain = Literal["month", "week"]

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_WEEK_RE = re.compile(r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$")


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grain: Grain
    start: str
    end: str

    @model_validator(mode="after")
    def _check_iso_format(self) -> "Period":
        pattern = _MONTH_RE if self.grain == "month" else _WEEK_RE
        for field_name, value in (("start", self.start), ("end", self.end)):
            if not pattern.match(value):
                kind = "month (YYYY-MM)" if self.grain == "month" else "ISO week (YYYY-Wnn)"
                raise ValueError(f"period.{field_name}={value!r} is not a valid {kind} string for grain={self.grain!r}")
        return self


class FilterEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: FilterDimension
    values: list[str] = Field(min_length=1, max_length=5)


def _check_filter_list(filters: list[FilterEntry] | None) -> list[FilterEntry] | None:
    if filters is None:
        return filters
    if len(filters) > 3:
        raise ValueError(f"max 3 filters, got {len(filters)}")
    dims = [f.dimension for f in filters]
    if len(dims) != len(set(dims)):
        raise ValueError(f"duplicate filter dimensions: {dims}")
    return filters


class MetricQuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_type: Literal["metric_query"]
    metric: Metric
    period: Period
    time_grain: Grain | None = None
    filters: list[FilterEntry] | None = None

    @field_validator("filters")
    @classmethod
    def _validate_filters(cls, v):
        return _check_filter_list(v)


class BreakdownQuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_type: Literal["breakdown_query"]
    metric: Metric
    period: Period
    dimension: Dimension
    filters: list[FilterEntry] | None = None
    top_n: int = Field(default=10, ge=1, le=20)
    sort: Literal["desc", "asc"] = "desc"

    @field_validator("filters")
    @classmethod
    def _validate_filters(cls, v):
        return _check_filter_list(v)


class ChangeDecompositionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_type: Literal["change_decomposition"]
    metric: Metric
    dimension: Dimension
    period_a: Period
    period_b: Period
    filters: list[FilterEntry] | None = None

    @field_validator("filters")
    @classmethod
    def _validate_filters(cls, v):
        return _check_filter_list(v)


class PendingContext(BaseModel):
    """Partial spec carried by a clarification, holding whatever the caller
    already resolved (period, filters, ...) so the follow-up turn can
    complete it. Every field is optional; the field SET is still pinned
    (extra="forbid") so a typo'd key fails loudly instead of silently
    vanishing."""
    model_config = ConfigDict(extra="forbid")

    metric: Metric | None = None
    period: Period | None = None
    dimension: Dimension | None = None
    filters: list[FilterEntry] | None = None
    time_grain: Grain | None = None

    @field_validator("filters")
    @classmethod
    def _validate_filters(cls, v):
        return _check_filter_list(v)


class ClarificationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_type: Literal["clarification"]
    question: str
    options: list[str] = Field(min_length=2, max_length=4)
    pending_context: PendingContext = Field(default_factory=PendingContext)


class RefusalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_type: Literal["refusal"]
    reason_code: ReasonCode
    message: str
    suggestions: list[str] = Field(default_factory=list, max_length=3)


QuerySpec = Annotated[
    Union[MetricQuerySpec, BreakdownQuerySpec, ChangeDecompositionSpec, ClarificationSpec, RefusalSpec],
    Field(discriminator="spec_type"),
]

_ENVELOPE_ADAPTER: TypeAdapter = TypeAdapter(QuerySpec)


def parse_spec(data: dict) -> QuerySpec:
    """Parses a raw dict into the matching spec_type model. Raises
    pydantic.ValidationError on any structural problem, including an
    unrecognized spec_type (Pydantic's union resolution tries every member
    and reports the aggregate failure when none match)."""
    return _ENVELOPE_ADAPTER.validate_python(data)
