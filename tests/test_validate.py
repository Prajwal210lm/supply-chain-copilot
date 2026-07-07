"""Tests for copilot/validate.py — written before the module exists (red).

V1 structural and V6 caps both surface as Pydantic failures in spec.py; this
module's job is to run the parse and correctly LABEL which rule fired, then
run V2 (compatibility) / V3 (decomposable) / V4 (period bounds) / V5
(delegates to resolve.py) against an already-parsed spec.
"""

import pytest

from copilot import validate


def test_v1_unknown_spec_type_rejected():
    outcome = validate.validate({"spec_type": "bogus"})
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V1"


def test_v1_extra_field_rejected():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "not_a_field": True,
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V1"


def test_v6_top_n_out_of_range_labeled_v6():
    outcome = validate.validate({
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
        "dimension": "category", "top_n": 99,
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V6"


def test_v6_too_many_filters_labeled_v6():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "filters": [
            {"dimension": "dc", "values": ["JEB"]},
            {"dimension": "emirate", "values": ["Dubai"]},
            {"dimension": "category", "values": ["home_care"]},
            {"dimension": "supplier", "values": ["Anadolu"]},
        ],
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V6"


def test_v6_duplicate_filter_dimensions_labeled_v6():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "filters": [
            {"dimension": "dc", "values": ["JEB"]},
            {"dimension": "dc", "values": ["AUH"]},
        ],
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V6"


# ---- V2: compatibility (golden a16-a18) -----------------------------------

def test_v2_revenue_by_supplier_incompatible():
    outcome = validate.validate({
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-01", "end": "2026-03"},
        "dimension": "supplier",
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V2"
    assert outcome.reason_code == "incompatible_pair"


def test_v2_inventory_value_by_customer_segment_incompatible():
    outcome = validate.validate({
        "spec_type": "breakdown_query", "metric": "inventory_value",
        "period": {"grain": "month", "start": "2026-06", "end": "2026-06"},
        "dimension": "customer_segment",
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.reason_code == "incompatible_pair"


def test_v2_lead_time_by_emirate_incompatible():
    outcome = validate.validate({
        "spec_type": "breakdown_query", "metric": "avg_supplier_lead_time",
        "period": {"grain": "month", "start": "2026-06", "end": "2026-06"},
        "dimension": "emirate",
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.reason_code == "incompatible_pair"


def test_v2_checks_filter_dimensions_too():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "avg_supplier_lead_time",
        "period": {"grain": "month", "start": "2026-06", "end": "2026-06"},
        "filters": [{"dimension": "emirate", "values": ["Dubai"]}],
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V2"
    assert outcome.reason_code == "incompatible_pair"


def test_v2_time_grain_week_incompatible_with_days_of_cover():
    # days_of_cover has no week-level data (compat matrix excludes "week"),
    # so a series request at week grain must be rejected the same way a
    # week BREAKDOWN would be.
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "days_of_cover",
        "period": {"grain": "week", "start": "2026-W01", "end": "2026-W10"},
        "time_grain": "week",
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V2"
    assert outcome.reason_code == "incompatible_pair"


def test_v2_time_grain_month_compatible_with_days_of_cover():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "days_of_cover",
        "period": {"grain": "month", "start": "2026-01", "end": "2026-06"},
        "time_grain": "month",
    })
    assert isinstance(outcome, validate.Accepted)


def test_v2_compatible_breakdown_is_accepted():
    outcome = validate.validate({
        "spec_type": "breakdown_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "dimension": "supplier",
    })
    assert isinstance(outcome, validate.Accepted)


# ---- V3: decomposable (golden a19-a20) ------------------------------------

def test_v3_aov_not_decomposable():
    outcome = validate.validate({
        "spec_type": "change_decomposition", "metric": "avg_order_value",
        "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "period_b": {"grain": "month", "start": "2026-04", "end": "2026-04"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V3"
    assert outcome.reason_code == "not_decomposable"


def test_v3_days_of_cover_not_decomposable():
    outcome = validate.validate({
        "spec_type": "change_decomposition", "metric": "days_of_cover",
        "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "period_b": {"grain": "month", "start": "2026-06", "end": "2026-06"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.reason_code == "not_decomposable"


def test_v3_otif_is_decomposable():
    outcome = validate.validate({
        "spec_type": "change_decomposition", "metric": "otif_pct",
        "dimension": "supplier",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    assert isinstance(outcome, validate.Accepted)


# ---- V4: period bounds (golden a21-a22) -----------------------------------

def test_v4_period_before_window_start_rejected():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2023-01", "end": "2023-12"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V4"
    assert outcome.reason_code == "out_of_window"


def test_v4_period_after_window_end_rejected():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "order_count",
        "period": {"grain": "month", "start": "2026-07", "end": "2026-07"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.reason_code == "out_of_window"


def test_v4_start_after_end_rejected():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-06", "end": "2026-03"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V4"


def test_v4_week_grain_over_26_weeks_rejected_with_month_suggestion():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "week", "start": "2025-W01", "end": "2025-W30"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V4"
    assert "month" in outcome.message.lower()


def test_v4_week_grain_within_26_weeks_accepted():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "week", "start": "2026-W01", "end": "2026-W10"},
    })
    assert isinstance(outcome, validate.Accepted)


def test_v4_decomposition_identical_periods_rejected():
    outcome = validate.validate({
        "spec_type": "change_decomposition", "metric": "revenue", "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-03", "end": "2026-03"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V4"


def test_v4_decomposition_overlapping_periods_rejected():
    outcome = validate.validate({
        "spec_type": "change_decomposition", "metric": "revenue", "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-01", "end": "2026-03"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-05"},
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V4"


def test_v4_decomposition_nonoverlapping_periods_accepted():
    outcome = validate.validate({
        "spec_type": "change_decomposition", "metric": "revenue", "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })
    assert isinstance(outcome, validate.Accepted)


# ---- V5: resolution, delegated to resolve.py (golden a23-a24) ------------

def test_v5_unresolvable_filter_rejected():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "order_count",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "filters": [{"dimension": "customer_segment", "values": ["carrefour"]}],
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.rule == "V5"
    assert outcome.reason_code == "unresolvable_filter"


def test_v5_sharjah_dc_unresolvable():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "filters": [{"dimension": "dc", "values": ["sharjah dc"]}],
    })
    assert isinstance(outcome, validate.Rejected)
    assert outcome.reason_code == "unresolvable_filter"


def test_v5_resolvable_filter_accepted_with_canonical_id():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "filters": [{"dimension": "supplier", "values": ["anadolu"]}],
    })
    assert isinstance(outcome, validate.Accepted)
    assert outcome.resolved_filters["supplier"] == ["SUP-07"]


def test_v5_ambiguous_filter_value_returns_clarification():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "order_count",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "filters": [{"dimension": "customer_segment", "values": ["trade"]}],
    })
    assert isinstance(outcome, (validate.NeedsClarification, validate.Rejected))


# ---- No dimension / no filters: happy path --------------------------------

def test_plain_metric_query_with_no_filters_accepted():
    outcome = validate.validate({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    })
    assert isinstance(outcome, validate.Accepted)
    assert outcome.resolved_filters == {}


def test_clarification_and_refusal_spec_types_pass_through_accepted():
    outcome = validate.validate({
        "spec_type": "refusal", "reason_code": "not_a_data_question",
        "message": "no", "suggestions": [],
    })
    assert isinstance(outcome, validate.Accepted)
