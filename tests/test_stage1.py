"""Tests for copilot/stage1.py — mocked client, no network, no API key.

Written before stage1.py in the sense that it drove the design (message
shape, retry condition), but stage1.py and this file were developed
together rather than strictly red-then-green given the amount of shared
data (the ten examples) both needed to agree on.
"""

import difflib
from pathlib import Path

import pytest
import yaml

from copilot import client, registry, spec, stage1, validate

GOLDEN_SET_PATH = Path(__file__).resolve().parent.parent / "eval" / "golden_set.yaml"


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def call(self, system, messages):
        self.calls.append({"system": system, "messages": messages})
        tool_input = self._responses.pop(0)
        return client.ClientResponse(
            tool_input=tool_input,
            usage=client.Usage(input_tokens=100, output_tokens=50),
            raw=None,
        )


# --------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------

def test_assemble_system_prompt_has_no_leftover_placeholders():
    prompt = stage1.assemble_system_prompt()
    assert "{CATALOG}" not in prompt
    assert "{EXAMPLES}" not in prompt


def test_assemble_system_prompt_contains_every_metric_key():
    prompt = stage1.assemble_system_prompt()
    for key in registry.METRICS:
        assert key in prompt


def test_assemble_system_prompt_contains_resolution_defaults():
    prompt = stage1.assemble_system_prompt()
    assert "Missing period" in prompt
    assert "latest complete month" in prompt


def test_assemble_system_prompt_preserves_locked_rules_text():
    prompt = stage1.assemble_system_prompt()
    assert "Copy entity mentions verbatim into filter values" in prompt
    assert "unsafe_request" in prompt


def test_assemble_system_prompt_is_deterministic():
    assert stage1.assemble_system_prompt() == stage1.assemble_system_prompt()


# --------------------------------------------------------------------------
# The ten worked examples: each must parse, and none may collide with
# eval/golden_set.yaml.
# --------------------------------------------------------------------------

def test_ten_examples_exactly():
    assert len(stage1.EXAMPLES) == 10


@pytest.mark.parametrize("example", stage1.EXAMPLES, ids=lambda e: e["question"][:40])
def test_every_example_spec_parses(example):
    spec.parse_spec(example["spec"])
    for prior in example.get("question_context", []):
        spec.parse_spec(prior["spec"])


def _golden_questions():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    questions = []
    for entry in doc["entries"]:
        questions.append(entry["question"])
        for turn in entry.get("context", []):
            questions.append(turn["question"])
    return questions


def test_no_example_question_exactly_matches_a_golden_question():
    golden = set(_golden_questions())
    for example in stage1.EXAMPLES:
        assert example["question"] not in golden, "exact collision: " + example["question"]
        for prior in example.get("question_context", []):
            assert prior["question"] not in golden, "exact collision: " + prior["question"]


def test_no_example_question_closely_paraphrases_a_golden_question():
    # Heuristic guard, not a substitute for the manual review already done:
    # flag anything suspiciously close (ratio > 0.85) so a future example
    # edit can't silently reintroduce a near-duplicate.
    golden = _golden_questions()
    for example in stage1.EXAMPLES:
        questions_to_check = [example["question"]] + [p["question"] for p in example.get("question_context", [])]
        for q in questions_to_check:
            for g in golden:
                ratio = difflib.SequenceMatcher(None, q.lower(), g.lower()).ratio()
                assert ratio <= 0.85, "near-duplicate (ratio %.2f): %r vs golden %r" % (ratio, q, g)


# --------------------------------------------------------------------------
# run_stage1: happy path, V7 retry, no-retry-on-V2..V5
# --------------------------------------------------------------------------

def test_run_stage1_happy_path_accepted():
    valid_spec = {
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    }
    fake = FakeClient([valid_spec])
    result = stage1.run_stage1("what was OTIF last month", client_instance=fake)
    assert isinstance(result.outcome, validate.Accepted)
    assert len(fake.calls) == 1
    assert result.usage.retried is False
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50


def test_run_stage1_retries_once_on_structural_failure_then_succeeds():
    malformed = {"spec_type": "metric_query", "metric": "not_a_real_metric"}  # fails Pydantic enum -> V1
    valid_spec = {
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    }
    fake = FakeClient([malformed, valid_spec])
    result = stage1.run_stage1("what was OTIF last month", client_instance=fake)
    assert len(fake.calls) == 2
    assert isinstance(result.outcome, validate.Accepted)
    assert result.usage.retried is True
    assert result.usage.input_tokens == 200  # summed across both calls
    assert result.usage.output_tokens == 100


def test_run_stage1_retry_error_text_appended_to_retry_messages():
    malformed = {"spec_type": "metric_query", "metric": "not_a_real_metric"}
    valid_spec = {
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    }
    fake = FakeClient([malformed, valid_spec])
    stage1.run_stage1("what was OTIF last month", client_instance=fake)
    retry_call_messages = fake.calls[1]["messages"]
    last_message = retry_call_messages[-1]
    assert last_message["role"] == "user"
    assert last_message["content"][0]["type"] == "tool_result"
    assert last_message["content"][0]["is_error"] is True


def test_run_stage1_does_not_retry_on_v2_incompatible_pair():
    incompatible = {
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-01", "end": "2026-03"},
        "dimension": "supplier",
    }
    fake = FakeClient([incompatible])
    result = stage1.run_stage1("revenue by supplier last quarter", client_instance=fake)
    assert len(fake.calls) == 1  # no retry
    assert isinstance(result.outcome, validate.Rejected)
    assert result.outcome.rule == "V2"


def test_run_stage1_retries_on_v6_caps_since_its_still_a_pydantic_failure():
    # V6 (caps) and V1 both surface as the SAME Pydantic ValidationError
    # path in validate.py — the prompt excludes only V2-V4 from retry, so a
    # caps violation gets the same one-shot retry a structural failure does.
    over_cap = {
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-01", "end": "2026-03"},
        "dimension": "category", "top_n": 99,
    }
    valid_spec = {
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-01", "end": "2026-03"},
        "dimension": "category", "top_n": 10, "sort": "desc",
    }
    fake = FakeClient([over_cap, valid_spec])
    result = stage1.run_stage1("top 99 categories by revenue", client_instance=fake)
    assert len(fake.calls) == 2
    assert result.usage.retried is True
    assert isinstance(result.outcome, validate.Accepted)


def test_run_stage1_does_not_retry_on_v5_unresolvable_filter():
    unresolvable = {
        "spec_type": "metric_query", "metric": "order_count",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        "filters": [{"dimension": "customer_segment", "values": ["carrefour"]}],
    }
    fake = FakeClient([unresolvable])
    result = stage1.run_stage1("orders from carrefour last month", client_instance=fake)
    assert len(fake.calls) == 1
    assert result.outcome.rule == "V5"


# --------------------------------------------------------------------------
# Context turns
# --------------------------------------------------------------------------

def test_context_turns_produce_tool_use_and_tool_result_pairs():
    prior_spec = {
        "spec_type": "metric_query", "metric": "otif_pct",
        "period": {"grain": "month", "start": "2025-01", "end": "2025-12"}, "time_grain": "month",
    }
    context = [stage1.ContextTurn(question="how did OTIF look across 2025, month by month", spec=prior_spec)]
    follow_up_spec = dict(prior_spec)
    follow_up_spec["filters"] = [{"dimension": "emirate", "values": ["Dubai"]}]
    fake = FakeClient([follow_up_spec])

    stage1.run_stage1("now just for Dubai", context_turns=context, client_instance=fake)
    messages = fake.calls[0]["messages"]

    assert messages[0] == {"role": "user", "content": "how did OTIF look across 2025, month by month"}
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"][0]["type"] == "tool_use"
    assert messages[1]["content"][0]["input"] == prior_spec
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["type"] == "tool_result"
    assert messages[3] == {"role": "user", "content": "now just for Dubai"}


def test_context_turns_no_result_data_ever():
    prior_spec = {"spec_type": "metric_query", "metric": "revenue", "period": {"grain": "month", "start": "2026-05", "end": "2026-05"}}
    context = [stage1.ContextTurn(question="revenue last month", spec=prior_spec)]
    fake = FakeClient([{"spec_type": "metric_query", "metric": "revenue", "period": {"grain": "month", "start": "2026-05", "end": "2026-05"}}])
    stage1.run_stage1("and this month", context_turns=context, client_instance=fake)
    messages = fake.calls[0]["messages"]
    tool_result_content = messages[2]["content"][0]["content"]
    assert "revenue" not in tool_result_content.lower() or "recorded" in tool_result_content.lower()
    # No numeric-looking result payload anywhere in the tool_result ack.
    import re
    assert not re.search(r"\d+\.\d+|AED", tool_result_content)


def test_only_most_recent_five_context_turns_included():
    specs = [
        {"spec_type": "metric_query", "metric": "revenue", "period": {"grain": "month", "start": "2026-0" + str(i), "end": "2026-0" + str(i)}}
        for i in range(1, 8)
    ]
    context = [stage1.ContextTurn(question="q" + str(i), spec=specs[i]) for i in range(7)]
    fake = FakeClient([specs[0]])
    stage1.run_stage1("final question", context_turns=context, client_instance=fake)
    messages = fake.calls[0]["messages"]
    # 5 turns * 3 messages each + 1 final question = 16
    assert len(messages) == 16
    first_question_content = messages[0]["content"]
    assert first_question_content == "q2"  # the earliest 2 of 7 were dropped
