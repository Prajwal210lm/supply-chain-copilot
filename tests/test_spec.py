"""Tests for copilot/spec.py — written before the module exists (red)."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from copilot import registry, spec

GOLDEN_SET_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden_set.yaml"


# --------------------------------------------------------------------------
# Envelope basics
# --------------------------------------------------------------------------

def test_metric_literal_matches_registry_keys():
    # spec.py hardcodes its own Metric literal (Pydantic Literal types need
    # static values); this cross-check is what keeps it from drifting from
    # the registry, which is the actual single source of truth for keys.
    assert set(spec.METRIC_KEYS) == set(registry.METRICS.keys())


def test_metric_query_parses_minimal():
    parsed = spec.parse_spec({
        "spec_type": "metric_query",
        "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    assert isinstance(parsed, spec.MetricQuerySpec)
    assert parsed.metric == "otif_pct"


def test_metric_query_rejects_extra_field():
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "metric_query",
            "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
            "not_a_real_field": 1,
        })


def test_period_rejects_extra_field():
    with pytest.raises(ValidationError):
        spec.Period(grain="month", start="2026-03", end="2026-03", bogus="x")


def test_filter_entry_rejects_extra_field():
    with pytest.raises(ValidationError):
        spec.FilterEntry(dimension="dc", values=["JEB"], bogus="x")


def test_breakdown_query_defaults_top_n_and_sort():
    parsed = spec.parse_spec({
        "spec_type": "breakdown_query",
        "metric": "revenue",
        "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
        "dimension": "category",
    })
    assert parsed.top_n == 10
    assert parsed.sort == "desc"


@pytest.mark.parametrize("top_n", [0, 21, -1])
def test_breakdown_query_top_n_out_of_range_rejected(top_n):
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "breakdown_query",
            "metric": "revenue",
            "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
            "dimension": "category",
            "top_n": top_n,
        })


def test_filters_reject_more_than_three():
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "metric_query",
            "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
            "filters": [
                {"dimension": "dc", "values": ["JEB"]},
                {"dimension": "emirate", "values": ["Dubai"]},
                {"dimension": "category", "values": ["home_care"]},
                {"dimension": "supplier", "values": ["S1"]},
            ],
        })


def test_filters_reject_duplicate_dimension():
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "metric_query",
            "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
            "filters": [
                {"dimension": "dc", "values": ["JEB"]},
                {"dimension": "dc", "values": ["AUH"]},
            ],
        })


def test_filter_values_reject_more_than_five():
    with pytest.raises(ValidationError):
        spec.FilterEntry(dimension="emirate", values=["a", "b", "c", "d", "e", "f"])


def test_filter_dimension_rejects_time_dimensions():
    # Time never appears in filters — dimension is entity-only.
    with pytest.raises(ValidationError):
        spec.FilterEntry(dimension="month", values=["2026-03"])


def test_change_decomposition_requires_two_periods():
    parsed = spec.parse_spec({
        "spec_type": "change_decomposition",
        "metric": "otif_pct",
        "dimension": "supplier",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    assert isinstance(parsed, spec.ChangeDecompositionSpec)


def test_clarification_options_bounds():
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "clarification",
            "question": "which one?",
            "options": ["only one"],
            "pending_context": {},
        })


def test_clarification_pending_context_rejects_unknown_field():
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "clarification",
            "question": "which one?",
            "options": ["a", "b"],
            "pending_context": {"bogus_field": 1},
        })


def test_refusal_suggestions_max_three():
    with pytest.raises(ValidationError):
        spec.parse_spec({
            "spec_type": "refusal",
            "reason_code": "out_of_catalog",
            "message": "no such metric",
            "suggestions": ["a", "b", "c", "d"],
        })


def test_refusal_allows_zero_suggestions():
    parsed = spec.parse_spec({
        "spec_type": "refusal",
        "reason_code": "not_a_data_question",
        "message": "not a data question",
        "suggestions": [],
    })
    assert isinstance(parsed, spec.RefusalSpec)


def test_unknown_spec_type_rejected():
    with pytest.raises(ValidationError):
        spec.parse_spec({"spec_type": "not_a_real_type"})


def test_period_month_format_validated():
    with pytest.raises(ValidationError):
        spec.Period(grain="month", start="not-a-month", end="2026-03")


def test_period_week_format_validated():
    spec.Period(grain="week", start="2026-W10", end="2026-W12")  # valid, must not raise
    with pytest.raises(ValidationError):
        spec.Period(grain="week", start="2026-03", end="2026-W12")  # month string under week grain


# --------------------------------------------------------------------------
# Golden set round-trip — the whole point of this module existing before
# any LLM code does.
# --------------------------------------------------------------------------

def _load_golden_entries():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc["entries"]


def test_golden_set_file_exists_and_has_eighty_entries():
    entries = _load_golden_entries()
    assert len(entries) == 80


@pytest.mark.parametrize("entry", _load_golden_entries(), ids=lambda e: e["id"])
def test_every_golden_expected_spec_parses(entry):
    parsed = spec.parse_spec(entry["expected"])
    assert parsed.spec_type == entry["expected"]["spec_type"]


def test_every_golden_context_spec_parses():
    # multi_turn entries carry prior-turn specs in `context`; those are also
    # real, complete QuerySpec instances and should round-trip too.
    checked = 0
    for entry in _load_golden_entries():
        for turn in entry.get("context", []):
            spec.parse_spec(turn["spec"])
            checked += 1
    assert checked > 0, "expected at least one multi_turn context spec to check"
