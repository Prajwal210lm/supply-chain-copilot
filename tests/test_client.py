"""Tests for copilot/client.py — written before the module exists (red).

No network calls, no API key required — these tests only check schema
generation and the missing-key error path.
"""

import pytest

from copilot import client, spec


def test_emit_spec_tool_schema_root_has_no_oneof_allof_anyof():
    # Regression: Anthropic's tool API rejected the first version of this
    # schema with "input_schema does not support oneOf, allOf, or anyOf at
    # the top level" — TypeAdapter(QuerySpec).json_schema() produces exactly
    # that shape ({"$defs", "discriminator", "oneOf"}). The merged schema
    # must never reintroduce a top-level combinator.
    schema = client.EMIT_SPEC_TOOL["input_schema"]
    assert "oneOf" not in schema
    assert "allOf" not in schema
    assert "anyOf" not in schema
    assert "discriminator" not in schema


def test_emit_spec_tool_schema_has_root_type_object():
    assert client.EMIT_SPEC_TOOL["input_schema"]["type"] == "object"


def test_emit_spec_tool_schema_merges_fields_from_all_five_models():
    schema = client.EMIT_SPEC_TOOL["input_schema"]
    properties = schema["properties"]
    # One field unique to each spec type, proving the merge actually pulled
    # from all five .model_json_schema() calls rather than just one.
    assert "period" in properties  # metric_query
    assert "dimension" in properties  # breakdown_query / change_decomposition
    assert "period_a" in properties and "period_b" in properties  # change_decomposition
    assert "question" in properties and "options" in properties  # clarification
    assert "reason_code" in properties and "suggestions" in properties  # refusal


def test_emit_spec_tool_schema_spec_type_enum_has_all_five_values():
    schema = client.EMIT_SPEC_TOOL["input_schema"]
    assert set(schema["properties"]["spec_type"]["enum"]) == {
        "metric_query", "breakdown_query", "change_decomposition", "clarification", "refusal",
    }


def test_emit_spec_tool_schema_generated_not_hand_typed():
    # Cross-check against a fresh per-model generation, proving the merge is
    # reproducible from spec.py's models rather than a frozen hand copy.
    schema = client.EMIT_SPEC_TOOL["input_schema"]
    for model in (spec.MetricQuerySpec, spec.BreakdownQuerySpec, spec.ChangeDecompositionSpec, spec.ClarificationSpec, spec.RefusalSpec):
        model_schema = model.model_json_schema()
        for prop_name, prop_schema in model_schema["properties"].items():
            if prop_name == "spec_type":
                continue
            assert schema["properties"][prop_name] == prop_schema


def test_emit_spec_tool_has_name_and_description():
    assert client.EMIT_SPEC_TOOL["name"] == "emit_spec"
    assert client.EMIT_SPEC_TOOL["description"]


def test_client_constants():
    assert client.MODEL
    assert client.TEMPERATURE == 0
    assert client.TIMEOUT_SECONDS == 120
    assert client.MAX_RETRIES == 2


def test_missing_api_key_raises_at_call_time_not_construction(monkeypatch):
    # A real .env now sits at the project root (needed for the live harness
    # run), so _ensure_env_loaded()'s load_dotenv() would silently restore
    # the deleted var on the first client construction of the whole pytest
    # session and defeat this test. Force the "already loaded" guard so no
    # reload happens, regardless of test execution order.
    monkeypatch.setattr(client, "_env_loaded", True)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = client.AnthropicClient(api_key=None)  # must not raise here
    with pytest.raises(client.MissingAPIKeyError):
        c.call(system="x", messages=[{"role": "user", "content": "y"}])


def test_explicit_api_key_overrides_env(monkeypatch):
    monkeypatch.setattr(client, "_env_loaded", True)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = client.AnthropicClient(api_key="sk-test-explicit")
    assert c._api_key == "sk-test-explicit"


def test_env_var_used_when_no_explicit_key(monkeypatch):
    monkeypatch.setattr(client, "_env_loaded", True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-from-env")
    c = client.AnthropicClient()
    assert c._api_key == "sk-test-from-env"
