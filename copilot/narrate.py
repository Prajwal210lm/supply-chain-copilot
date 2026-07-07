"""Stage 4: result -> narration paragraph, plus the deterministic chart
spec that always accompanies it (from copilot.chart, never from the model).

run_narrate() renders copilot/prompts/narrate_system.md verbatim (no
{CATALOG}/{EXAMPLES} slots in this prompt — it's static, unlike Stage 1's),
asks the LLM for a short paragraph describing the result object, and passes
that paragraph through the render gate (R1-R4 below) before returning it.

RENDER GATE — four deterministic checks, run in order against the model's
raw text (before placeholder substitution, except where noted):
  R1  bare-digit rejection   any digit outside a {{...}} placeholder fails.
  R2  path validation        every {{path}} must resolve to a leaf scalar
                              on the actual result object; an unknown path
                              withholds (never retried — a hallucinated
                              path on retry is exactly as likely).
  R3  spelled-number lexicon million/billion/percent/half/double/tripled/
                              hundred/thousand/two..ninety, word-boundary,
                              case-insensitive. "one" is an intentional,
                              documented exception.
  R4  length cap              max 500 chars AFTER placeholder substitution
                              (checked last, since it needs the rendered
                              values, and never retried).

R1/R3 are retried once, with the specific violation named in the retry
prompt (V7-style, mirroring stage1.py's retry — see _RETRYABLE_RULES). R2
and R4 are never retried: on any final failure the narration is withheld
(paragraph=None, withheld_reason set) but chart_spec is always returned —
a withheld paragraph must never take the chart down with it.
"""

import dataclasses
import re
from dataclasses import dataclass
from pathlib import Path

from copilot import chart
from copilot import client as client_module
from copilot import registry

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "narrate_system.md"

_PLACEHOLDER_RE = re.compile(r"\{\{([^{}]+)\}\}")
_PATH_SEGMENT_RE = re.compile(r"^(\w+)(?:\[(\d+)\])?$")

# Number words two through ninety. Compounds ("twenty-one", "forty five")
# still trip this: the hyphen/space is a word boundary, so the base word
# ("twenty", "forty") is what actually matches.
_NUMBER_WORDS = (
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety",
)
_R3_LEXICON = ("million", "billion", "percent", "half", "double", "tripled", "hundred", "thousand") + _NUMBER_WORDS
_R3_PATTERNS = tuple((w, re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)) for w in _R3_LEXICON)

_MAX_PARAGRAPH_CHARS = 500
_RETRYABLE_RULES = frozenset({"R1", "R3"})


class PathError(Exception):
    pass


@dataclass(frozen=True)
class GateOutcome:
    ok: bool
    rendered: str | None
    violation_rule: str | None
    violation_detail: str | None


@dataclass(frozen=True)
class NarrationUsage:
    input_tokens: int
    output_tokens: int
    retried: bool = False


@dataclass(frozen=True)
class NarrationResult:
    paragraph: str | None
    chart_spec: object  # chart.ChartSpec
    withheld_reason: str | None
    usage: NarrationUsage


# --------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------

_SYSTEM_TEXT: str | None = None


def system_prompt_text() -> str:
    global _SYSTEM_TEXT
    if _SYSTEM_TEXT is None:
        _SYSTEM_TEXT = _PROMPT_PATH.read_text(encoding="utf-8")
    return _SYSTEM_TEXT


def _flatten_result(obj, prefix: str = "") -> list:
    """Every leaf of the result dataclass as a 'path = value' line, so the
    model can see both the paths it's allowed to reference and the actual
    values behind them."""
    lines = []
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        for f in dataclasses.fields(obj):
            value = getattr(obj, f.name)
            path = f.name if not prefix else prefix + "." + f.name
            lines.extend(_flatten_result(value, path))
    elif isinstance(obj, tuple):
        for i, item in enumerate(obj):
            lines.extend(_flatten_result(item, prefix + "[" + str(i) + "]"))
    else:
        lines.append(prefix + " = " + repr(obj))
    return lines


def _describe_period(period) -> str:
    if period.start == period.end:
        return period.start
    return period.start + " to " + period.end


def _describe_filters(filters) -> str:
    if not filters:
        return ""
    parts = [f.dimension + "=" + "/".join(f.values) for f in filters]
    return " filtered by " + ", ".join(parts)


def build_query_description(parsed) -> str:
    """Plain-text context for the LLM only — not the user-facing echo bar
    (Rule 4 tells the model the user already sees that separately)."""
    metric_name = registry.get_metric(parsed.metric).display_name

    if parsed.spec_type == "metric_query":
        text = metric_name + " for " + _describe_period(parsed.period)
        if parsed.time_grain:
            text += ", by " + parsed.time_grain
        return text + _describe_filters(parsed.filters)

    if parsed.spec_type == "breakdown_query":
        text = metric_name + " by " + parsed.dimension + " for " + _describe_period(parsed.period)
        return text + _describe_filters(parsed.filters)

    if parsed.spec_type == "change_decomposition":
        text = (
            metric_name + " change by " + parsed.dimension + " from "
            + _describe_period(parsed.period_a) + " to " + _describe_period(parsed.period_b)
        )
        return text + _describe_filters(parsed.filters)

    raise ValueError(f"narrate.build_query_description: no narration for spec_type={parsed.spec_type!r}")


def build_user_message(parsed, result) -> str:
    description = build_query_description(parsed)
    result_lines = "\n".join(_flatten_result(result))
    return (
        "Query description: " + description + "\n\n"
        "Result object (dot-paths you may reference as {{path}}):\n" + result_lines
    )


def _retry_prompt(violation_rule: str, violation_detail: str) -> str:
    return (
        "That paragraph violated " + violation_rule + ": " + violation_detail + ". "
        "Rewrite it, fixing that violation. Every number must be a {{path}} "
        "placeholder referencing the result object; never write a digit or a "
        "spelled-out number outside a placeholder."
    )


# --------------------------------------------------------------------------
# Path resolution (R2)
# --------------------------------------------------------------------------

def resolve_path(root, path: str):
    current = root
    for segment in path.strip().split("."):
        match = _PATH_SEGMENT_RE.match(segment)
        if not match:
            raise PathError(f"malformed path segment {segment!r} in {path!r}")
        name, index = match.group(1), match.group(2)
        if not hasattr(current, name):
            raise PathError(f"unknown attribute {name!r} in path {path!r}")
        current = getattr(current, name)
        if index is not None:
            i = int(index)
            if not isinstance(current, (tuple, list)) or i >= len(current):
                raise PathError(f"index [{i}] out of range in path {path!r}")
            current = current[i]
    if current is not None and not isinstance(current, (str, int, float, bool)):
        raise PathError(f"path {path!r} does not resolve to a leaf value (got {type(current).__name__})")
    return current


# --------------------------------------------------------------------------
# Render gate (R1-R4)
# --------------------------------------------------------------------------

def _check_bare_digits(raw_text: str) -> str | None:
    stripped = _PLACEHOLDER_RE.sub("", raw_text)
    match = re.search(r"\d", stripped)
    if match:
        return "found a bare digit outside a {{...}} placeholder"
    return None


def _check_spelled_numbers(raw_text: str) -> str | None:
    stripped = _PLACEHOLDER_RE.sub("", raw_text)
    for word, pattern in _R3_PATTERNS:
        if pattern.search(stripped):
            return f"found forbidden number word {word!r}"
    return None


def _render_with_paths(raw_text: str, result) -> str:
    def _sub(match: re.Match) -> str:
        value = resolve_path(result, match.group(1))
        return "" if value is None else str(value)

    return _PLACEHOLDER_RE.sub(_sub, raw_text)


def apply_render_gate(raw_text: str, result) -> GateOutcome:
    detail = _check_bare_digits(raw_text)
    if detail:
        return GateOutcome(ok=False, rendered=None, violation_rule="R1", violation_detail=detail)

    detail = _check_spelled_numbers(raw_text)
    if detail:
        return GateOutcome(ok=False, rendered=None, violation_rule="R3", violation_detail=detail)

    try:
        rendered = _render_with_paths(raw_text, result)
    except PathError as exc:
        return GateOutcome(ok=False, rendered=None, violation_rule="R2", violation_detail=str(exc))

    if len(rendered) > _MAX_PARAGRAPH_CHARS:
        detail = f"rendered paragraph is {len(rendered)} chars, max {_MAX_PARAGRAPH_CHARS}"
        return GateOutcome(ok=False, rendered=None, violation_rule="R4", violation_detail=detail)

    return GateOutcome(ok=True, rendered=rendered, violation_rule=None, violation_detail=None)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def run_narrate(parsed, result, client_instance=None) -> NarrationResult:
    chart_spec = chart.build_chart_spec(parsed, result)
    the_client = client_instance if client_instance is not None else client_module.AnthropicClient()

    system = system_prompt_text()
    messages = [{"role": "user", "content": build_user_message(parsed, result)}]

    response = the_client.call_text(system=system, messages=messages)
    total_in, total_out = response.usage.input_tokens, response.usage.output_tokens
    retried = False

    outcome = apply_render_gate(response.text, result)

    if not outcome.ok and outcome.violation_rule in _RETRYABLE_RULES:
        retry_messages = list(messages) + [
            {"role": "assistant", "content": response.text},
            {"role": "user", "content": _retry_prompt(outcome.violation_rule, outcome.violation_detail)},
        ]
        retried = True
        retry_response = the_client.call_text(system=system, messages=retry_messages)
        total_in += retry_response.usage.input_tokens
        total_out += retry_response.usage.output_tokens
        outcome = apply_render_gate(retry_response.text, result)

    usage = NarrationUsage(input_tokens=total_in, output_tokens=total_out, retried=retried)

    if outcome.ok:
        return NarrationResult(paragraph=outcome.rendered, chart_spec=chart_spec, withheld_reason=None, usage=usage)

    withheld_reason = outcome.violation_rule + ": " + outcome.violation_detail
    return NarrationResult(paragraph=None, chart_spec=chart_spec, withheld_reason=withheld_reason, usage=usage)
