"""Mocked tests for copilot/narrate.py — no network, no API key. The LLM is
a FakeTextClient returning canned strings; every render-gate check (R1-R4)
is also tested directly against hand-crafted paragraphs, independent of any
LLM call.
"""

import pytest

from copilot import client, decompose, narrate, results, spec


class FakeTextClient:
    def __init__(self, texts):
        self._texts = list(texts)
        self.calls = []

    def call_text(self, system, messages, max_tokens=None):
        self.calls.append({"system": system, "messages": messages})
        text = self._texts.pop(0)
        return client.TextResponse(text=text, usage=client.Usage(input_tokens=100, output_tokens=50), raw=None)


def _otif_spec():
    return spec.parse_spec({
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    })


def _otif_result():
    return results.build_metric_query_result("otif_pct", 84.2, _otif_spec().period)


def _decomposition_spec():
    return spec.parse_spec({
        "spec_type": "change_decomposition", "metric": "revenue", "dimension": "category",
        "period_a": {"grain": "month", "start": "2026-02", "end": "2026-02"},
        "period_b": {"grain": "month", "start": "2026-03", "end": "2026-03"},
    })


def _decomposition_result():
    decomposed = decompose.decompose_additive([("food_beverage", 1000, 1200), ("personal_care", 500, 400)])
    spec_obj = _decomposition_spec()
    return results.build_decomposition_result("revenue", "category", decomposed, spec_obj.period_a, spec_obj.period_b)


# --------------------------------------------------------------------------
# resolve_path (R2 mechanics)
# --------------------------------------------------------------------------

def test_resolve_path_simple_leaf():
    result = _otif_result()
    assert narrate.resolve_path(result, "value.formatted") == "84.2%"
    assert narrate.resolve_path(result, "value.raw") == 84.2


def test_resolve_path_indexed_member():
    result = _decomposition_result()
    assert narrate.resolve_path(result, "members[0].member") == "food_beverage"


def test_resolve_path_unknown_attribute_raises():
    result = _otif_result()
    with pytest.raises(narrate.PathError):
        narrate.resolve_path(result, "value.nonexistent")


def test_resolve_path_out_of_range_index_raises():
    result = _decomposition_result()
    with pytest.raises(narrate.PathError):
        narrate.resolve_path(result, "members[99].member")


def test_resolve_path_non_leaf_raises():
    result = _otif_result()
    with pytest.raises(narrate.PathError):
        narrate.resolve_path(result, "value")  # a FormattedNumber, not a leaf scalar


def test_resolve_path_none_leaf_is_allowed():
    decomposed = decompose.decompose_additive([("a", 100, 200)])
    spec_obj = _decomposition_spec()
    result = results.build_decomposition_result("revenue", "category", decomposed, spec_obj.period_a, spec_obj.period_b)
    assert narrate.resolve_path(result, "withheld_reason") is None


# --------------------------------------------------------------------------
# Render gate — individual checks
# --------------------------------------------------------------------------

def test_r1_bare_digit_outside_placeholder_fails():
    result = _otif_result()
    outcome = narrate.apply_render_gate("OTIF was 84.2% last month.", result)
    assert outcome.ok is False
    assert outcome.violation_rule == "R1"


def test_r1_digits_inside_placeholder_are_fine():
    result = _otif_result()
    outcome = narrate.apply_render_gate("OTIF was {{value.formatted}} last month.", result)
    assert outcome.ok is True


def test_r3_spelled_number_word_fails():
    result = _otif_result()
    outcome = narrate.apply_render_gate("OTIF was roughly double the usual rate at {{value.formatted}}.", result)
    assert outcome.ok is False
    assert outcome.violation_rule == "R3"


def test_r3_percent_word_fails():
    result = _otif_result()
    outcome = narrate.apply_render_gate("OTIF hit {{value.formatted}}, a strong percent gain.", result)
    assert outcome.ok is False
    assert outcome.violation_rule == "R3"


def test_r3_one_of_the_is_allowed():
    result = _decomposition_result()
    outcome = narrate.apply_render_gate(
        "One of the categories, {{members[0].member}}, contributed {{members[0].contribution.formatted}} to the change.",
        result,
    )
    assert outcome.ok is True


def test_r2_unknown_path_withholds_no_retry_needed_to_detect():
    result = _otif_result()
    outcome = narrate.apply_render_gate("OTIF was {{value.made_up_field}} last month.", result)
    assert outcome.ok is False
    assert outcome.violation_rule == "R2"


def test_r4_length_cap_fails_after_rendering():
    result = _otif_result()
    long_text = "OTIF was {{value.formatted}}. " + ("This is filler text to pad the paragraph out. " * 15)
    outcome = narrate.apply_render_gate(long_text, result)
    assert outcome.ok is False
    assert outcome.violation_rule == "R4"


def test_clean_paragraph_with_valid_paths_passes_and_renders():
    result = _otif_result()
    outcome = narrate.apply_render_gate("OTIF landed at {{value.formatted}} for the period.", result)
    assert outcome.ok is True
    assert outcome.rendered == "OTIF landed at 84.2% for the period."


# --------------------------------------------------------------------------
# run_narrate — retry / withhold orchestration
# --------------------------------------------------------------------------

def test_run_narrate_happy_path_no_retry():
    fake = FakeTextClient(["OTIF landed at {{value.formatted}} for the period."])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph == "OTIF landed at 84.2% for the period."
    assert narration.withheld_reason is None
    assert narration.usage.retried is False
    assert len(fake.calls) == 1


def test_run_narrate_retries_on_r1_bare_digit():
    fake = FakeTextClient([
        "OTIF was 84.2% for the period.",
        "OTIF landed at {{value.formatted}} for the period.",
    ])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph == "OTIF landed at 84.2% for the period."
    assert narration.usage.retried is True
    assert len(fake.calls) == 2
    assert "R1" in fake.calls[1]["messages"][-1]["content"]


def test_run_narrate_retries_on_r3_spelled_number():
    fake = FakeTextClient([
        "OTIF was roughly double the prior period at {{value.formatted}}.",
        "OTIF landed at {{value.formatted}} for the period.",
    ])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph == "OTIF landed at 84.2% for the period."
    assert narration.usage.retried is True
    assert len(fake.calls) == 2


def test_run_narrate_withholds_on_r2_hallucinated_path_no_retry():
    fake = FakeTextClient(["OTIF was {{value.made_up_field}} for the period."])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph is None
    assert narration.withheld_reason.startswith("R2")
    assert len(fake.calls) == 1  # R2 is never retried


def test_run_narrate_withholds_on_r4_length_cap_no_retry():
    long_text = "OTIF was {{value.formatted}}. " + ("Filler text padding this paragraph out further. " * 15)
    fake = FakeTextClient([long_text])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph is None
    assert narration.withheld_reason.startswith("R4")
    assert len(fake.calls) == 1  # R4 is never retried


def test_run_narrate_withholds_when_retry_also_fails():
    fake = FakeTextClient([
        "OTIF was 84.2% for the period.",
        "OTIF was still 90.0% for the period.",
    ])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph is None
    assert narration.withheld_reason.startswith("R1")
    assert narration.usage.retried is True
    assert len(fake.calls) == 2


def test_withheld_narration_still_returns_a_valid_chart_spec():
    fake = FakeTextClient(["OTIF was {{value.made_up_field}} for the period."])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.paragraph is None
    assert narration.chart_spec is not None
    assert narration.chart_spec.type == "stat_card"
    assert narration.chart_spec.points[0].formatted == "84.2%"


def test_chart_spec_always_present_on_happy_path_too():
    fake = FakeTextClient(["OTIF landed at {{value.formatted}} for the period."])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.chart_spec.type == "stat_card"


def test_run_narrate_accumulates_usage_across_retry():
    fake = FakeTextClient([
        "OTIF was 84.2% for the period.",
        "OTIF landed at {{value.formatted}} for the period.",
    ])
    narration = narrate.run_narrate(_otif_spec(), _otif_result(), client_instance=fake)
    assert narration.usage.input_tokens == 200
    assert narration.usage.output_tokens == 100


def test_build_query_description_does_not_include_the_paragraph_output():
    description = narrate.build_query_description(_otif_spec())
    assert "OTIF" in description or "OTIF %" in description
    assert "2026-05" in description
