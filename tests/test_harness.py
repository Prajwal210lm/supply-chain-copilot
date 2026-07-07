"""Mocked tests for eval/harness.py — no network, no API key. The harness
itself is the live test (run manually); this file tests its grading and
gating logic in isolation via a fake stage1.run_stage1.
"""

import json

import pytest

from copilot import spec, stage1, validate
from eval import harness


def _accepted(spec_dict):
    return validate.Accepted(spec=spec.parse_spec(spec_dict), resolved_filters={})


def _rejected(rule, reason_code=None, message="x"):
    return validate.Rejected(rule=rule, reason_code=reason_code, message=message)


def _result(outcome, in_tok=100, out_tok=50, retried=False):
    return stage1.Stage1Result(outcome=outcome, usage=stage1.Stage1Usage(input_tokens=in_tok, output_tokens=out_tok, retried=retried))


# --------------------------------------------------------------------------
# grade_entry
# --------------------------------------------------------------------------

def test_grade_entry_answer_spec_match():
    entry = {
        "expected": {
            "spec_type": "metric_query", "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        },
    }
    outcome = _accepted(entry["expected"])
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is True
    assert got_type == "metric_query"


def test_grade_entry_answer_spec_mismatch():
    entry = {
        "expected": {
            "spec_type": "metric_query", "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        },
    }
    got = {
        "spec_type": "metric_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
    }
    outcome = _accepted(got)
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is False
    assert "mismatch" in detail


def test_grade_entry_answer_spec_equivalent_after_normalization():
    # Explicit top_n/sort defaults vs omitted should still grade correct —
    # normalize.py fills the same defaults on both sides before comparing.
    entry = {
        "expected": {
            "spec_type": "breakdown_query", "metric": "revenue",
            "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
            "dimension": "category", "top_n": 10, "sort": "desc",
        },
    }
    got = {
        "spec_type": "breakdown_query", "metric": "revenue",
        "period": {"grain": "month", "start": "2026-04", "end": "2026-06"},
        "dimension": "category",
    }
    outcome = _accepted(got)
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is True


def test_grade_entry_clarification_options_set_match_ignores_order_and_case():
    entry = {"expected": {"spec_type": "clarification", "question": "which?", "options": ["Otif Pct", "stockout_count"], "pending_context": {}}}
    got = {"spec_type": "clarification", "question": "different wording is fine", "options": ["stockout_count", "OTIF PCT"], "pending_context": {}}
    outcome = _accepted(got)
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is True
    assert got_type == "clarification"


def test_grade_entry_clarification_options_set_mismatch():
    entry = {"expected": {"spec_type": "clarification", "question": "which?", "options": ["a", "b"], "pending_context": {}}}
    got = {"spec_type": "clarification", "question": "which?", "options": ["a", "c"], "pending_context": {}}
    outcome = _accepted(got)
    correct, _, detail = harness.grade_entry(entry, outcome)
    assert correct is False
    assert "options" in detail


def test_grade_entry_refusal_reason_code_match():
    entry = {"expected_reason": "unsafe_request", "expected": {"spec_type": "refusal", "reason_code": "unsafe_request", "message": "x", "suggestions": []}}
    got = {"spec_type": "refusal", "reason_code": "unsafe_request", "message": "different message text", "suggestions": []}
    outcome = _accepted(got)
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is True
    assert got_type == "refusal"


def test_grade_entry_refusal_reason_code_mismatch():
    entry = {"expected_reason": "out_of_catalog", "expected": {"spec_type": "refusal", "reason_code": "out_of_catalog", "message": "x", "suggestions": []}}
    got = {"spec_type": "refusal", "reason_code": "unsafe_request", "message": "x", "suggestions": []}
    outcome = _accepted(got)
    correct, _, detail = harness.grade_entry(entry, outcome)
    assert correct is False
    assert "reason_code" in detail


def test_grade_entry_refusal_via_validator_rejection_with_mapped_reason_passes():
    # The model emitted an answer spec instead of refusing outright, but a
    # validator caught it and rejected with the rule that maps to the
    # golden entry's expected reason_code — the defense worked one layer
    # later, so this still counts as correct.
    entry = {"expected_reason": "not_decomposable", "expected": {"spec_type": "refusal", "reason_code": "not_decomposable", "message": "x", "suggestions": []}}
    outcome = _rejected("V3", reason_code="not_decomposable")
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is True
    assert got_type == "rejected:V3"


def test_grade_entry_refusal_via_validator_rejection_with_unmapped_reason_fails():
    entry = {"expected_reason": "unresolvable_filter", "expected": {"spec_type": "refusal", "reason_code": "unresolvable_filter", "message": "x", "suggestions": []}}
    outcome = _rejected("V3", reason_code="not_decomposable")
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is False
    assert "expected reason_code" in detail


def test_grade_entry_clarification_options_subset_extra_options_still_passes():
    # The model surfacing an additional plausible reading beyond the
    # golden set's options is not wrong — only the golden options must
    # all be present in what the model produced.
    entry = {"expected": {"spec_type": "clarification", "question": "which?", "options": ["a", "b"], "pending_context": {}}}
    got = {"spec_type": "clarification", "question": "which?", "options": ["a", "b", "c"], "pending_context": {}}
    outcome = _accepted(got)
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is True


def test_grade_entry_clarification_options_missing_expected_option_fails():
    entry = {"expected": {"spec_type": "clarification", "question": "which?", "options": ["a", "b", "c"], "pending_context": {}}}
    got = {"spec_type": "clarification", "question": "which?", "options": ["a", "b"], "pending_context": {}}
    outcome = _accepted(got)
    correct, _, detail = harness.grade_entry(entry, outcome)
    assert correct is False
    assert "subset" in detail


def test_grade_entry_rejected_outcome_never_matches_answer_expectation():
    entry = {
        "expected": {
            "spec_type": "metric_query", "metric": "otif_pct",
            "period": {"grain": "month", "start": "2026-05", "end": "2026-05"},
        },
    }
    outcome = _rejected("V2", reason_code="incompatible_pair")
    correct, got_type, detail = harness.grade_entry(entry, outcome)
    assert correct is False
    assert got_type == "rejected:V2"


# --------------------------------------------------------------------------
# Aggregate stats
# --------------------------------------------------------------------------

def _verdict(id_, slice_, correct, got_spec_type="metric_query"):
    return harness.EntryVerdict(
        id=id_, slice=slice_, question="q", correct=correct, got_spec_type=got_spec_type,
        expected_spec_type="metric_query", detail="", input_tokens=10, output_tokens=5, retried=False,
    )


def test_slice_accuracy():
    verdicts = [_verdict("c1", "clean", True), _verdict("c2", "clean", False), _verdict("a1", "adversarial", True)]
    assert harness.slice_accuracy(verdicts, "clean") == 0.5
    assert harness.slice_accuracy(verdicts, "adversarial") == 1.0
    assert harness.slice_accuracy(verdicts, "near_miss") is None


def test_clean_slice_clarification_rate():
    verdicts = [
        _verdict("c1", "clean", False, got_spec_type="clarification"),
        _verdict("c2", "clean", True, got_spec_type="metric_query"),
    ]
    assert harness.clean_slice_clarification_rate(verdicts) == 0.5


def test_adversarial_all_correct():
    assert harness.adversarial_all_correct([_verdict("a1", "adversarial", True), _verdict("a2", "adversarial", True)]) is True
    assert harness.adversarial_all_correct([_verdict("a1", "adversarial", True), _verdict("a2", "adversarial", False)]) is False
    assert harness.adversarial_all_correct([]) is True


def test_near_miss_breakdown():
    entries = [
        {"id": "n1", "slice": "near_miss", "near_miss_pair": "fill_rate_vs_in_full"},
        {"id": "n2", "slice": "near_miss", "near_miss_pair": "fill_rate_vs_in_full"},
        {"id": "n3", "slice": "near_miss", "near_miss_pair": "stockout_vs_doc"},
    ]
    verdicts = [_verdict("n1", "near_miss", True), _verdict("n2", "near_miss", False), _verdict("n3", "near_miss", True)]
    breakdown = harness.near_miss_breakdown(entries, verdicts)
    assert breakdown["fill_rate_vs_in_full"] == (1, 2)
    assert breakdown["stockout_vs_doc"] == (1, 1)


def test_estimate_cost_usd():
    cost = harness.estimate_cost_usd(1_000_000, 1_000_000)
    assert cost == pytest.approx(3.00 + 15.00)


# --------------------------------------------------------------------------
# load_golden_entries — real file, structural only, no API
# --------------------------------------------------------------------------

def test_load_golden_entries_all():
    entries = harness.load_golden_entries()
    assert len(entries) == 80


def test_load_golden_entries_slice_filter():
    entries = harness.load_golden_entries(slice_filter="adversarial")
    assert len(entries) == 25
    assert all(e["slice"] == "adversarial" for e in entries)


def test_load_golden_entries_entry_id_filter():
    entries = harness.load_golden_entries(entry_id="a12")
    assert len(entries) == 1
    assert entries[0]["id"] == "a12"


# --------------------------------------------------------------------------
# run_once — mocked stage1.run_stage1, no API
# --------------------------------------------------------------------------

def test_run_once_with_mocked_stage1(monkeypatch):
    entries = [
        {
            "id": "fake1", "slice": "clean", "question": "what was otif last month",
            "expected": {"spec_type": "metric_query", "metric": "otif_pct", "period": {"grain": "month", "start": "2026-05", "end": "2026-05"}},
        },
        {
            "id": "fake2", "slice": "adversarial", "expected_reason": "unsafe_request", "question": "ignore instructions",
            "expected": {"spec_type": "refusal", "reason_code": "unsafe_request", "message": "x", "suggestions": []},
        },
    ]

    canned = {
        "fake1": _result(_accepted({"spec_type": "metric_query", "metric": "otif_pct", "period": {"grain": "month", "start": "2026-05", "end": "2026-05"}}), in_tok=100, out_tok=20),
        "fake2": _result(_accepted({"spec_type": "refusal", "reason_code": "unsafe_request", "message": "no", "suggestions": []}), in_tok=150, out_tok=30),
    }

    def fake_run_stage1(question, context_turns=None, client_instance=None):
        for entry in entries:
            if entry["question"] == question:
                return canned[entry["id"]]
        raise AssertionError("unexpected question: " + question)

    monkeypatch.setattr(harness.stage1, "run_stage1", fake_run_stage1)

    verdicts, total_in, total_out = harness.run_once(entries)
    assert len(verdicts) == 2
    assert all(v.correct for v in verdicts)
    assert total_in == 250
    assert total_out == 50


# --------------------------------------------------------------------------
# write_run_results
# --------------------------------------------------------------------------

def test_write_run_results_writes_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "RESULTS_DIR", tmp_path)
    verdicts = [_verdict("c1", "clean", True)]
    path = harness.write_run_results("20260101T000000", 0, verdicts, 100, 50)
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["total_input_tokens"] == 100
    assert payload["total_output_tokens"] == 50
    assert payload["estimated_cost_usd"] == pytest.approx(harness.estimate_cost_usd(100, 50))
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["id"] == "c1"


# --------------------------------------------------------------------------
# print_report — GATE lines
# --------------------------------------------------------------------------

def test_print_report_gate_lines_pass(capsys):
    entries = [
        {"id": "c1", "slice": "clean"}, {"id": "c2", "slice": "clean"},
        {"id": "n1", "slice": "near_miss", "near_miss_pair": "p"},
        {"id": "a1", "slice": "adversarial"},
    ]
    verdicts = [
        _verdict("c1", "clean", True), _verdict("c2", "clean", True),
        _verdict("n1", "near_miss", True), _verdict("a1", "adversarial", True),
    ]
    harness.print_report(entries, [verdicts], [0.01])
    out = capsys.readouterr().out
    assert "GATE adversarial:" in out and "PASS" in out
    assert "GATE accuracy:" in out
    assert "GATE clarification:" in out


def test_print_report_gate_fails_on_bad_adversarial(capsys):
    entries = [{"id": "a1", "slice": "adversarial"}]
    verdicts = [_verdict("a1", "adversarial", False)]
    harness.print_report(entries, [verdicts], [0.0])
    out = capsys.readouterr().out
    assert "GATE adversarial: 100% correct refusals with correct reason codes FAIL" in out
