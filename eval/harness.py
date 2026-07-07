#!/usr/bin/env python
"""Golden-set evaluation harness. CLI, not a pytest suite — this is the live
test against the real Anthropic API and is run manually:

    python eval/harness.py --runs 1
    python eval/harness.py --slice adversarial
    python eval/harness.py --entry a12

Comparison rules:
  - metric_query / breakdown_query / change_decomposition: compare as
    normalized canonical JSON (copilot.normalize).
  - clarification: assert spec_type == "clarification" and the golden
    entry's options are a SUBSET of the model's produced options
    (order-insensitive, case-insensitive — question text is advisory, not
    graded). The model surfacing additional plausible readings beyond the
    golden set's is not wrong. True semantic matching would need its own
    model call; this harness doesn't add one.
  - refusal: assert spec_type == "refusal" and reason_code matches
    (message text is advisory, not graded). If the model instead emitted
    an answer spec that a validator then REJECTED, and the rejecting
    rule maps to the golden entry's expected reason_code (see
    _REJECTED_RULE_TO_REASON_CODE below), that also counts as a pass —
    the defense worked, just at the validator layer instead of the model
    layer.

Per-run results land in eval/results/run_<timestamp>_r<i>.json. Never wired
into CI or pytest — see tests/test_harness.py for the mocked unit tests of
this file's grading/gating logic.
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from copilot import constants as C
from copilot import normalize, stage1, validate

GOLDEN_SET_PATH = C.PROJECT_ROOT / "eval" / "golden_set.yaml"
RESULTS_DIR = C.PROJECT_ROOT / "eval" / "results"

# claude-sonnet-4-6 pricing, USD per million tokens.
COST_PER_MTOK_INPUT_USD = 3.00
COST_PER_MTOK_OUTPUT_USD = 15.00

ANSWER_SPEC_TYPES = ("metric_query", "breakdown_query", "change_decomposition")

# A validator rejection is an equally valid refusal, just caught one layer
# later than the model — the reason_code it maps to must still match the
# golden entry's expected reason for it to count as a pass.
_REJECTED_RULE_TO_REASON_CODE = {
    "V2": "incompatible_pair",
    "V3": "not_decomposable",
    "V4": "out_of_window",
    "V5": "unresolvable_filter",
}


@dataclass
class EntryVerdict:
    id: str
    slice: str
    question: str
    correct: bool
    got_spec_type: str | None
    expected_spec_type: str
    detail: str
    input_tokens: int
    output_tokens: int
    retried: bool
    expected: dict = None  # the golden entry's raw "expected" block, for verbatim failure reporting
    got: dict = None       # full debug view of the outcome — never just the type label


def load_golden_entries(slice_filter: str | None = None, entry_id: str | None = None) -> list:
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    entries = doc["entries"]
    if entry_id:
        entries = [e for e in entries if e["id"] == entry_id]
    if slice_filter:
        entries = [e for e in entries if e["slice"] == slice_filter]
    return entries


def _context_turns_for_entry(entry: dict) -> list:
    return [stage1.ContextTurn(question=t["question"], spec=t["spec"]) for t in entry.get("context", [])]


def _outcome_spec_dict(outcome):
    if isinstance(outcome, validate.Accepted):
        return outcome.spec.model_dump(exclude_none=True)
    return None


def _outcome_debug_dict(outcome) -> dict:
    """Full representation of whatever Stage 1 + validate.py produced, for
    verbatim failure reporting — grade_entry only needs the type label, but
    a human reading a failure needs the actual content."""
    if isinstance(outcome, validate.Accepted):
        return {"kind": "accepted", "spec": outcome.spec.model_dump(exclude_none=True)}
    if isinstance(outcome, validate.Rejected):
        return {"kind": "rejected", "rule": outcome.rule, "reason_code": outcome.reason_code, "message": outcome.message}
    if isinstance(outcome, validate.NeedsClarification):
        return {"kind": "needs_clarification_v5", "question": outcome.question, "options": outcome.options}
    return {"kind": "unknown"}


def grade_entry(entry: dict, outcome) -> tuple[bool, str, str]:
    """Returns (correct, got_spec_type_label, detail)."""
    expected = entry["expected"]
    expected_type = expected["spec_type"]
    got_dict = _outcome_spec_dict(outcome)

    if got_dict is not None:
        got_type = got_dict["spec_type"]
    elif isinstance(outcome, validate.Rejected):
        got_type = "rejected:" + outcome.rule
    elif isinstance(outcome, validate.NeedsClarification):
        got_type = "needs_clarification(v5)"
    else:
        got_type = "unknown"

    if expected_type in ANSWER_SPEC_TYPES:
        if got_dict is None or got_dict["spec_type"] != expected_type:
            return False, got_type, "expected spec_type=" + expected_type + ", got " + got_type
        correct = normalize.specs_equal(got_dict, expected)
        return correct, got_type, ("" if correct else "normalized spec mismatch")

    if expected_type == "clarification":
        if got_dict is None or got_dict["spec_type"] != "clarification":
            return False, got_type, "expected clarification, got " + got_type
        got_options = {o.strip().lower() for o in got_dict.get("options", [])}
        expected_options = {o.strip().lower() for o in expected.get("options", [])}
        correct = expected_options.issubset(got_options)
        return correct, got_type, ("" if correct else "expected options not a subset of got options")

    if expected_type == "refusal":
        expected_reason = entry.get("expected_reason") or expected.get("reason_code")
        if isinstance(outcome, validate.Rejected):
            mapped_reason = _REJECTED_RULE_TO_REASON_CODE.get(outcome.rule)
            correct = mapped_reason is not None and mapped_reason == expected_reason
            detail = "" if correct else (
                "validator rejected via " + outcome.rule + " (-> " + str(mapped_reason) + "), expected reason_code " + str(expected_reason)
            )
            return correct, got_type, detail
        if got_dict is None or got_dict["spec_type"] != "refusal":
            return False, got_type, "expected refusal, got " + got_type
        got_reason = got_dict.get("reason_code")
        correct = got_reason == expected_reason
        return correct, got_type, ("" if correct else "reason_code mismatch: got " + str(got_reason) + " expected " + str(expected_reason))

    return False, got_type, "unknown expected spec_type: " + str(expected_type)


def run_once(entries: list) -> tuple[list, int, int]:
    verdicts = []
    total_in, total_out = 0, 0
    for entry in entries:
        context_turns = _context_turns_for_entry(entry)
        result = stage1.run_stage1(entry["question"], context_turns=context_turns)
        correct, got_type, detail = grade_entry(entry, result.outcome)
        verdicts.append(EntryVerdict(
            id=entry["id"], slice=entry["slice"], question=entry["question"],
            correct=correct, got_spec_type=got_type, expected_spec_type=entry["expected"]["spec_type"],
            detail=detail, input_tokens=result.usage.input_tokens, output_tokens=result.usage.output_tokens,
            retried=result.usage.retried,
            expected=entry["expected"], got=_outcome_debug_dict(result.outcome),
        ))
        total_in += result.usage.input_tokens
        total_out += result.usage.output_tokens
    return verdicts, total_in, total_out


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * COST_PER_MTOK_INPUT_USD + (output_tokens / 1_000_000) * COST_PER_MTOK_OUTPUT_USD


def slice_accuracy(verdicts: list, slice_name: str) -> float | None:
    subset = [v for v in verdicts if v.slice == slice_name]
    if not subset:
        return None
    return sum(1 for v in subset if v.correct) / len(subset)


def clean_slice_clarification_rate(verdicts: list) -> float:
    clean = [v for v in verdicts if v.slice == "clean"]
    if not clean:
        return 0.0
    return sum(1 for v in clean if v.got_spec_type == "clarification") / len(clean)


def adversarial_all_correct(verdicts: list) -> bool:
    adversarial = [v for v in verdicts if v.slice == "adversarial"]
    return all(v.correct for v in adversarial) if adversarial else True


def near_miss_breakdown(entries: list, verdicts: list) -> dict:
    by_id = {v.id: v for v in verdicts}
    pairs: dict[str, list[bool]] = {}
    for e in entries:
        if e["slice"] != "near_miss":
            continue
        pair = e.get("near_miss_pair", "unknown")
        pairs.setdefault(pair, []).append(by_id[e["id"]].correct)
    return {pair: (sum(1 for c in results if c), len(results)) for pair, results in pairs.items()}


def write_run_results(session_timestamp: str, run_index: int, verdicts: list, in_tok: int, out_tok: int) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / ("run_" + session_timestamp + "_r" + str(run_index) + ".json")
    payload = {
        "timestamp": session_timestamp,
        "run_index": run_index,
        "entries": [asdict(v) for v in verdicts],
        "total_input_tokens": in_tok,
        "total_output_tokens": out_tok,
        "estimated_cost_usd": estimate_cost_usd(in_tok, out_tok),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def print_report(entries: list, all_run_verdicts: list, all_run_costs: list) -> None:
    slices = sorted({e["slice"] for e in entries})

    print("=" * 70)
    print("PER-SLICE ACCURACY (min / max across runs)")
    print("=" * 70)
    for s in slices:
        accs = [a for a in (slice_accuracy(rv, s) for rv in all_run_verdicts) if a is not None]
        if not accs:
            continue
        n = sum(1 for e in entries if e["slice"] == s)
        print("  %-15s min=%.1f%%  max=%.1f%%  (n=%d)" % (s, min(accs) * 100, max(accs) * 100, n))

    clarify_rates = [clean_slice_clarification_rate(rv) for rv in all_run_verdicts]
    print()
    print("Clean-slice clarification rate: min=%.1f%%  max=%.1f%%" % (min(clarify_rates) * 100, max(clarify_rates) * 100))

    print()
    print("NEAR-MISS BREAKDOWN BY PAIR (last run)")
    breakdown = near_miss_breakdown(entries, all_run_verdicts[-1])
    for pair, (correct, total) in sorted(breakdown.items()):
        print("  %-35s %d/%d" % (pair, correct, total))

    adversarial_ok = all(adversarial_all_correct(rv) for rv in all_run_verdicts)
    accuracy_ok = all(
        (slice_accuracy(rv, "clean") or 1.0) >= 0.90 and (slice_accuracy(rv, "near_miss") or 1.0) >= 0.90
        for rv in all_run_verdicts
    )
    clarification_ok = all(r < 0.10 for r in clarify_rates)

    print()
    print("GATE adversarial: 100% correct refusals with correct reason codes " + ("PASS" if adversarial_ok else "FAIL"))
    print("GATE accuracy: clean and near-miss each >= 90% in every run " + ("PASS" if accuracy_ok else "FAIL"))
    print("GATE clarification: clean-slice clarification rate < 10% in every run " + ("PASS" if clarification_ok else "FAIL"))

    total_cost = sum(all_run_costs)
    print()
    print("Total estimated cost across %d run(s): $%.4f USD" % (len(all_run_verdicts), total_cost))


def main() -> None:
    parser = argparse.ArgumentParser(description="Golden-set evaluation harness (live API — run manually).")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--slice", type=str, default=None)
    parser.add_argument("--entry", type=str, default=None)
    args = parser.parse_args()

    entries = load_golden_entries(slice_filter=args.slice, entry_id=args.entry)
    if not entries:
        print("No matching golden entries.")
        sys.exit(1)

    session_timestamp = time.strftime("%Y%m%dT%H%M%S")
    all_run_verdicts, all_run_costs = [], []
    for run_index in range(args.runs):
        verdicts, in_tok, out_tok = run_once(entries)
        cost = estimate_cost_usd(in_tok, out_tok)
        all_run_verdicts.append(verdicts)
        all_run_costs.append(cost)
        path = write_run_results(session_timestamp, run_index, verdicts, in_tok, out_tok)
        print("Run %d/%d complete -> %s" % (run_index + 1, args.runs, path))

    print()
    print_report(entries, all_run_verdicts, all_run_costs)

    any_gate_failed = not (
        all(adversarial_all_correct(rv) for rv in all_run_verdicts)
        and all((slice_accuracy(rv, "clean") or 1.0) >= 0.90 and (slice_accuracy(rv, "near_miss") or 1.0) >= 0.90 for rv in all_run_verdicts)
        and all(clean_slice_clarification_rate(rv) < 0.10 for rv in all_run_verdicts)
    )
    if any_gate_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
