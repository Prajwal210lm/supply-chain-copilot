"""Tests for copilot/normalize.py — written before the module exists (red).

The five pairs in eval/normalizer_pairs.yaml ARE the spec for what counts as
equivalent; this file never edits that YAML, only reads it. The sixth,
non-equivalent pair is hand-written here since eval/normalizer_pairs.yaml
is off-limits to edit.
"""

from pathlib import Path

import pytest
import yaml

from copilot import normalize

PAIRS_PATH = Path(__file__).resolve().parent.parent / "eval" / "normalizer_pairs.yaml"


def _load_pairs():
    with open(PAIRS_PATH, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc["pairs"]


@pytest.mark.parametrize("pair", _load_pairs(), ids=lambda p: p["id"])
def test_normalizer_pairs_yaml_equivalent_pairs_compare_equal(pair):
    assert pair["equivalent"] is True
    assert normalize.normalize_spec(pair["spec_a"]) == normalize.normalize_spec(pair["spec_b"])


def test_sixth_non_equivalent_pair_compares_unequal():
    # Same shape as the pinned pairs but a genuinely different metric —
    # must NOT normalize equal.
    spec_a = {
        "spec_type": "metric_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
    }
    spec_b = {
        "spec_type": "metric_query", "metric": "order_count",
        "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
    }
    assert normalize.normalize_spec(spec_a) != normalize.normalize_spec(spec_b)


# --------------------------------------------------------------------------
# Unit-level behavior (each transformation the pairs collectively exercise)
# --------------------------------------------------------------------------

def test_quarter_period_expands_to_month_range():
    spec = {"spec_type": "metric_query", "metric": "revenue",
            "period": {"grain": "quarter", "start": "2026-Q2", "end": "2026-Q2"}}
    normalized = normalize.normalize_spec(spec)
    assert normalized["period"] == {"grain": "month", "start": "2026-04", "end": "2026-06"}


def test_year_period_expands_to_month_range():
    spec = {"spec_type": "metric_query", "metric": "revenue",
            "period": {"grain": "year", "start": "2025", "end": "2025"}}
    normalized = normalize.normalize_spec(spec)
    assert normalized["period"] == {"grain": "month", "start": "2025-01", "end": "2025-12"}


def test_filters_sorted_by_dimension():
    spec = {"spec_type": "metric_query", "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
            "filters": [{"dimension": "emirate", "values": ["dubai"]}, {"dimension": "customer_segment", "values": ["modern trade"]}]}
    normalized = normalize.normalize_spec(spec)
    assert [f["dimension"] for f in normalized["filters"]] == ["customer_segment", "emirate"]


def test_values_sorted_within_filter():
    spec = {"spec_type": "metric_query", "metric": "fill_rate_pct",
            "period": {"grain": "month", "start": "2026-06", "end": "2026-06"},
            "filters": [{"dimension": "emirate", "values": ["dubai", "sharjah", "abu dhabi"]}]}
    normalized = normalize.normalize_spec(spec)
    assert normalized["filters"][0]["values"] == ["abu dhabi", "dubai", "sharjah"]


def test_top_n_default_filled_explicitly():
    spec = {"spec_type": "breakdown_query", "metric": "revenue",
            "period": {"grain": "month", "start": "2026-04", "end": "2026-06"}, "dimension": "category"}
    normalized = normalize.normalize_spec(spec)
    assert normalized["top_n"] == 10
    assert normalized["sort"] == "desc"


def test_case_insensitive_filter_values_lowercased():
    spec = {"spec_type": "metric_query", "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
            "filters": [{"dimension": "emirate", "values": ["Dubai"]}]}
    normalized = normalize.normalize_spec(spec)
    assert normalized["filters"][0]["values"] == ["dubai"]


def test_normalize_does_not_mutate_input():
    spec = {"spec_type": "metric_query", "metric": "revenue",
            "period": {"grain": "quarter", "start": "2026-Q2", "end": "2026-Q2"}}
    original = dict(spec)
    normalize.normalize_spec(spec)
    assert spec["period"]["grain"] == "quarter"  # untouched
    assert spec == original


def test_specs_equal_helper():
    a = {"spec_type": "metric_query", "metric": "revenue", "period": {"grain": "quarter", "start": "2026-Q2", "end": "2026-Q2"}}
    b = {"spec_type": "metric_query", "metric": "revenue", "period": {"grain": "month", "start": "2026-04", "end": "2026-06"}}
    assert normalize.specs_equal(a, b) is True


def test_to_canonical_json_is_stable_regardless_of_key_order():
    a = {"period": {"grain": "month", "start": "2026-05", "end": "2026-05"}, "spec_type": "metric_query", "metric": "otif_pct"}
    b = {"metric": "otif_pct", "spec_type": "metric_query", "period": {"start": "2026-05", "grain": "month", "end": "2026-05"}}
    assert normalize.to_canonical_json(a) == normalize.to_canonical_json(b)
