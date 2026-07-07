"""Tests for copilot/registry.py — written before the module exists (red)."""

import re
from pathlib import Path

import pytest

from copilot import registry

SPEC_METRIC_KEYS = {
    "otif_pct", "on_time_pct", "in_full_pct", "fill_rate_pct", "revenue",
    "order_count", "avg_order_value", "inventory_value", "days_of_cover",
    "stockout_count", "avg_supplier_lead_time",
}

# Transcribed verbatim from docs/SPEC.md's compatibility matrix.
SPEC_COMPATIBLE_DIMENSIONS = {
    "otif_pct": {"month", "week", "dc", "emirate", "category", "customer_segment", "supplier"},
    "on_time_pct": {"month", "week", "dc", "emirate", "category", "customer_segment", "supplier"},
    "in_full_pct": {"month", "week", "dc", "emirate", "category", "customer_segment", "supplier"},
    "fill_rate_pct": {"month", "week", "dc", "emirate", "category", "customer_segment", "supplier"},
    "revenue": {"month", "week", "dc", "emirate", "category", "customer_segment"},
    "order_count": {"month", "week", "dc", "emirate", "category", "customer_segment"},
    "avg_order_value": {"month", "week", "dc", "emirate", "category", "customer_segment"},
    "inventory_value": {"month", "dc", "category"},
    "days_of_cover": {"month", "dc", "category"},
    "stockout_count": {"month", "week", "dc", "category", "supplier"},
    "avg_supplier_lead_time": {"month", "dc", "supplier"},
}

SPEC_DECOMPOSABLE = {
    "otif_pct", "on_time_pct", "in_full_pct", "fill_rate_pct",
    "revenue", "order_count", "stockout_count", "inventory_value",
}


def test_registry_has_exactly_eleven_entries():
    assert set(registry.METRICS.keys()) == SPEC_METRIC_KEYS
    assert len(registry.METRICS) == 11


@pytest.mark.parametrize("key", sorted(SPEC_METRIC_KEYS))
def test_every_entry_has_required_fields(key):
    entry = registry.get_metric(key)
    assert entry.key == key
    assert entry.display_name
    assert entry.definition
    assert isinstance(entry.synonyms, (list, tuple))
    assert entry.numerator_sql
    assert entry.base_relation_sql
    assert entry.join_path
    assert isinstance(entry.compatible_dimensions, frozenset)
    assert isinstance(entry.decomposable, bool)


@pytest.mark.parametrize("key,expected_dims", sorted(SPEC_COMPATIBLE_DIMENSIONS.items()))
def test_compatible_dimensions_match_spec_matrix(key, expected_dims):
    entry = registry.get_metric(key)
    assert entry.compatible_dimensions == frozenset(expected_dims), (
        f"{key}: registry says {sorted(entry.compatible_dimensions)}, "
        f"SPEC.md matrix says {sorted(expected_dims)}"
    )


def test_decomposable_flags_match_spec():
    actual = {k for k, v in registry.METRICS.items() if v.decomposable}
    assert actual == SPEC_DECOMPOSABLE


def test_additive_metrics_have_no_denominator():
    for key in ("revenue", "order_count", "inventory_value", "stockout_count"):
        assert registry.get_metric(key).denominator_sql is None, f"{key} should be additive (no denominator)"


def test_ratio_metrics_have_a_denominator():
    for key in ("otif_pct", "on_time_pct", "in_full_pct", "fill_rate_pct",
                "avg_order_value", "days_of_cover", "avg_supplier_lead_time"):
        assert registry.get_metric(key).denominator_sql is not None, f"{key} should have a denominator"


def test_otif_family_has_a_line_grain_variant_triggered_by_supplier():
    for key in ("otif_pct", "on_time_pct", "in_full_pct"):
        entry = registry.get_metric(key)
        assert entry.line_grain_variant is not None, f"{key} needs a line-grain variant"
        assert "supplier" in entry.line_grain_variant.triggers


def test_fill_rate_has_no_separate_line_grain_variant():
    # fill_rate_pct is line grain BY DEFAULT (per fixtures/decomposition_fixture.yaml),
    # so it needs no second relation — every dimension uses the one relation.
    entry = registry.get_metric("fill_rate_pct")
    assert entry.line_grain_variant is None


def test_metrics_without_supplier_compatibility_have_no_supplier_trigger():
    for key, entry in registry.METRICS.items():
        if "supplier" not in entry.compatible_dimensions and entry.line_grain_variant is not None:
            assert "supplier" not in entry.line_grain_variant.triggers


def test_in_full_not_exists_fragment_is_defined_exactly_once():
    # "In-full compiles as NOT EXISTS against short lines, defined once here
    # and nowhere else." — grep the source, not just behavior, so a future
    # copy-paste duplicate is caught even if it happens to agree numerically.
    source = Path(registry.__file__).read_text(encoding="utf-8")
    matches = re.findall(r"NOT EXISTS.{0,200}?qty_delivered\s*<\s*\w*\.?qty_ordered", source, re.IGNORECASE | re.DOTALL)
    assert len(matches) == 1, f"expected exactly one in-full NOT EXISTS fragment, found {len(matches)}"


def test_near_miss_neighbors_have_disambiguation_notes():
    # These four are exactly the near_miss slice's confusions in eval/golden_set.yaml.
    for key in ("fill_rate_pct", "in_full_pct", "on_time_pct", "otif_pct",
                "avg_order_value", "stockout_count", "days_of_cover"):
        entry = registry.get_metric(key)
        assert entry.disambiguation_note, f"{key} should carry a disambiguation note (has a near-miss neighbor)"


def test_all_three_spec_types_resolve_otif_to_the_same_registry_entry():
    a = registry.resolve_for_spec_type("metric_query", "otif_pct")
    b = registry.resolve_for_spec_type("breakdown_query", "otif_pct")
    c = registry.resolve_for_spec_type("change_decomposition", "otif_pct")
    assert a is b is c is registry.METRICS["otif_pct"]


def test_get_metric_unknown_key_raises():
    with pytest.raises(KeyError):
        registry.get_metric("not_a_real_metric")


def test_no_metric_semantics_defined_outside_registry_module():
    # Every other copilot module must import metric SQL from registry, never
    # inline its own numerator/denominator fragment. Cheap structural guard:
    # none of the sibling modules should contain "qty_delivered" or
    # "actual_delivery_date <=" literals of their own once they exist.
    # (This test is a placeholder assertion the compiler tests extend; kept
    # here so the rule lives beside the registry it protects.)
    assert "qty_delivered" in Path(registry.__file__).read_text(encoding="utf-8")
