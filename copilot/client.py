"""Anthropic client wrapper. The emit_spec tool's input_schema is generated
directly from copilot.spec's Pydantic models — this is the ONLY place that
schema is built, so a change to spec.py propagates here automatically and
there is never a hand-maintained JSON schema that can drift out of sync with
the actual validation models. See _emit_spec_input_schema()'s docstring for
why it merges each spec model's own schema rather than generating one
straight off the QuerySpec union.

The API key is read from ANTHROPIC_API_KEY (loaded from a .env file at the
project root via python-dotenv, or from the real environment) but is only
ever CHECKED when a call is actually made — constructing AnthropicClient()
never raises, so tests can build and mock one without a key.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from copilot import constants as C
from copilot import spec

MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0
TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
MAX_OUTPUT_TOKENS = 1024

_env_loaded = False


def _ensure_env_loaded() -> None:
    global _env_loaded
    if not _env_loaded:
        load_dotenv(dotenv_path=C.PROJECT_ROOT / ".env")
        _env_loaded = True


_SPEC_TYPE_MODELS = (
    spec.MetricQuerySpec, spec.BreakdownQuerySpec, spec.ChangeDecompositionSpec,
    spec.ClarificationSpec, spec.RefusalSpec,
)


def _emit_spec_input_schema() -> dict:
    """Generated from copilot.spec's Pydantic models — but NOT via
    `TypeAdapter(QuerySpec).json_schema()` directly. That produces a
    discriminated-union schema ({"$defs", "discriminator", "oneOf"}), which
    is valid JSON Schema on its own but is exactly the shape Anthropic's
    tool API rejects: "input_schema does not support oneOf, allOf, or anyOf
    at the top level". Tool inputs must be one flat object schema.

    So instead: call .model_json_schema() on each of the five spec models
    individually (still 100% Pydantic-generated) and merge their properties
    into one flat schema, with spec_type widened from each model's single
    `const` value into the enum of all five. This makes the JSON-schema
    layer permissive about which fields are present for a given spec_type —
    the real per-type requirement (e.g. breakdown_query needs `dimension`)
    is enforced where it always was, by spec.parse_spec() during Stage 1's
    V1/V7 retry pass, not by the tool schema itself.
    """
    properties: dict = {}
    defs: dict = {}
    spec_type_values: list[str] = []

    for model in _SPEC_TYPE_MODELS:
        model_schema = model.model_json_schema()
        defs.update(model_schema.get("$defs", {}))
        spec_type_values.append(model_schema["properties"]["spec_type"]["const"])
        for prop_name, prop_schema in model_schema["properties"].items():
            if prop_name != "spec_type":
                properties.setdefault(prop_name, prop_schema)

    properties["spec_type"] = {"type": "string", "enum": spec_type_values}

    schema = {
        "type": "object",
        "properties": properties,
        "required": ["spec_type"],
        "additionalProperties": False,
    }
    if defs:
        schema["$defs"] = defs
    return schema


EMIT_SPEC_TOOL = {
    "name": "emit_spec",
    "description": "Emit the single structured QuerySpec answer for this turn.",
    "input_schema": _emit_spec_input_schema(),
}


class MissingAPIKeyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class ClientResponse:
    tool_input: dict
    usage: Usage
    raw: object


@dataclass(frozen=True)
class TextResponse:
    text: str
    usage: Usage
    raw: object


class AnthropicClient:
    def __init__(self, api_key: str | None = None):
        _ensure_env_loaded()
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        self._sdk_client = None

    def _get_sdk_client(self):
        if not self._api_key:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Add it to a .env file at the project "
                "root (see .env.example) or export it in the environment before "
                "calling Stage 1."
            )
        if self._sdk_client is None:
            import anthropic
            self._sdk_client = anthropic.Anthropic(
                api_key=self._api_key, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES,
            )
        return self._sdk_client

    def call(self, system: str, messages: list) -> ClientResponse:
        sdk_client = self._get_sdk_client()
        response = sdk_client.messages.create(
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system,
            messages=messages,
            tools=[EMIT_SPEC_TOOL],
            tool_choice={"type": "tool", "name": "emit_spec"},
        )
        tool_use_block = next(block for block in response.content if block.type == "tool_use")
        usage = Usage(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
        return ClientResponse(tool_input=tool_use_block.input, usage=usage, raw=response)

    def call_text(self, system: str, messages: list, max_tokens: int = MAX_OUTPUT_TOKENS) -> TextResponse:
        """Plain free-text completion — no forced tool use. Used by narrate.py,
        which needs a prose paragraph, not a structured emit_spec call."""
        sdk_client = self._get_sdk_client()
        response = sdk_client.messages.create(
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        text_block = next(block for block in response.content if block.type == "text")
        usage = Usage(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
        return TextResponse(text=text_block.text, usage=usage, raw=response)
