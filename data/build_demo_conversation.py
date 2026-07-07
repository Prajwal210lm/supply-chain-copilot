#!/usr/bin/env python
"""Builds data/demo_conversation.json by ACTUALLY running the pipeline five
times against the real Anthropic API (needs ANTHROPIC_API_KEY) — the March
OTIF story, as a natural conversation thread: monthly OTIF series showing
the March dip, decomposed by supplier (SUP-07/Anadolu dominates), Anadolu's
lead-time blowout, an AUH-vs-JEB breakdown, and the June recovery check.

GET /api/demo serves this file verbatim, so it needs no LLM and no key at
request time — this script is the only thing that spends money, and only
when someone chooses to re-run it (e.g. after a prompt or data change).

CONTEXT_INDICES below is a curatorial choice, not a mechanical "last 5
turns" carry-forward: turn 3 (Anadolu's lead times) is a side-quest off
turns 1-2's OTIF/March thread, and turn 4 ("hit harder") means to continue
that OTIF/March thread, not turn 3's lead-time detour, so turn 4's context
deliberately skips turn 3. Turn 5 ("how are we doing now") means to return
to the thread's original framing, not any of the specific detours, so it
only carries turn 1. This was found empirically: threading full history
naively pulled turn 4 onto avg_supplier_lead_time (wrong metric) and turn 5
onto the still-pending Anadolu filter (wrong scope) — seeing the actual
model behavior is what surfaced that a fixed 5-question demo script needs
per-turn context curation instead of blind accumulation.

Run: python data/build_demo_conversation.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot import api, constants as C, pipeline, stage1
from copilot.client import AnthropicClient

OUTPUT_PATH = C.PROJECT_ROOT / "data" / "demo_conversation.json"

QUESTIONS = [
    "How did OTIF perform over the last year?",
    "Why did OTIF drop in March 2026?",
    "What happened to Anadolu's lead times?",
    "Was Abu Dhabi hit harder than Jebel Ali?",
    "How are we doing now?",
]

# Indices (into the already-answered turns) each question's context should
# carry — see the module docstring for why this isn't just "everything so far".
CONTEXT_INDICES = [
    [],        # 1: fresh
    [0],       # 2: "in March 2026" is explicit in the question, but knowing
               #    we've been discussing OTIF doesn't hurt
    [0, 1],    # 3: needs turn 2's March-drop framing to place "lead times"
               #    in the same month, and to already know SUP-07/Anadolu
    [0, 1],    # 4: continues turns 1-2's OTIF/March thread, NOT turn 3's
               #    lead-time detour
    [0],       # 5: returns to the thread's original general framing
]

NARRATION_RESAMPLE_ATTEMPTS = 4


def _run_with_narration_resample(question, context_turns, client_instance):
    """narrate.py already retries once per call, naming the specific
    violation, per the locked render-gate contract — that policy is
    unchanged here. What this adds is specific to building a canned demo:
    for a stat-card metric_query/breakdown_query, the result contract
    (results.py) exposes no period/date path at all, so a model that
    wants to situate the number in time has no {{path}} available for it
    and can trip R1. Rather than changing the locked prompt or the result
    contract to route around that, this draws a few more independent
    samples from the SAME unmodified system (each a fresh API call, not a
    hand-edit) and keeps the first one that lands a real narration —
    exactly what a real user hitting a withheld paragraph would do by
    asking again."""
    result = pipeline.run_question(question, context_turns=context_turns, client_instance=client_instance)
    attempt = 1
    while result.outcome_kind == "answer" and result.narration is None and attempt < NARRATION_RESAMPLE_ATTEMPTS:
        print(f"  (narration withheld: {result.withheld_reason!r} — resampling, attempt {attempt + 1})")
        result = pipeline.run_question(question, context_turns=context_turns, client_instance=client_instance)
        attempt += 1
    return result


def build() -> dict:
    client_instance = AnthropicClient()
    answered_turns = []  # parallel to QUESTIONS, filled in as we go
    turns = []

    for i, question in enumerate(QUESTIONS):
        context_turns = [answered_turns[j] for j in CONTEXT_INDICES[i]]
        result = _run_with_narration_resample(question, context_turns, client_instance)
        response = api._ask_response(result)
        turns.append({"question": question, "response": response})

        if result.outcome_kind != "answer":
            raise RuntimeError(f"demo question {i + 1} got {result.outcome_kind!r} instead of an answer: {question!r}\n{response}")
        answered_turns.append(stage1.ContextTurn(question=question, spec=result.spec))

    return {"placeholder": False, "turns": turns}


def main() -> None:
    payload = build()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {OUTPUT_PATH} ({len(payload['turns'])} turns)")


if __name__ == "__main__":
    main()
