"""Tests for copilot/resolve.py — written before the module exists (red).

The MUST_RESOLVE / MUST_NOT_RESOLVE tables ARE the threshold spec, per the
brief: HIGH/LOW get tuned until this set passes, not the other way around.
"""

import pytest

from copilot import resolve

MUST_RESOLVE = [
    # (dimension, verbatim mention, expected canonical id)
    ("supplier", "anadolou", "SUP-07"),
    ("emirate", "abu dhabbi", "Abu Dhabi"),
    ("customer_segment", "modern trad", "modern_trade"),
    ("category", "personel care", "personal_care"),
    ("dc", "jebal ali", "JEB"),
    ("dc", "abu dhabi dc", "AUH"),
    ("dc", "abu dhabi", "AUH"),
    ("category", "beverages", "food_beverage"),
]

MUST_NOT_RESOLVE = [
    # (dimension, verbatim mention) — must come back Unresolvable, never Resolved
    ("customer_segment", "carrefour"),
    ("dc", "sharjah dc"),
    ("supplier", "acme corp"),
]


@pytest.mark.parametrize("dimension,mention,expected_id", MUST_RESOLVE, ids=[m for _, m, _ in MUST_RESOLVE])
def test_calibration_set_must_resolve(dimension, mention, expected_id):
    outcome = resolve.resolve_entity(dimension, mention)
    assert isinstance(outcome, resolve.Resolved), f"{mention!r} under {dimension!r} should auto-resolve, got {outcome!r}"
    assert outcome.canonical_id == expected_id


@pytest.mark.parametrize("dimension,mention", MUST_NOT_RESOLVE, ids=[m for _, m in MUST_NOT_RESOLVE])
def test_calibration_set_must_not_resolve(dimension, mention):
    outcome = resolve.resolve_entity(dimension, mention)
    assert isinstance(outcome, resolve.Unresolvable), f"{mention!r} under {dimension!r} should be unresolvable, got {outcome!r}"


def test_exact_case_insensitive_match_resolves():
    for value in ("JEB", "jeb", "Jeb", "jEb"):
        outcome = resolve.resolve_entity("dc", value)
        assert isinstance(outcome, resolve.Resolved)
        assert outcome.canonical_id == "JEB"
        assert outcome.score == 1.0


def test_exact_display_name_resolves():
    outcome = resolve.resolve_entity("emirate", "Abu Dhabi")
    assert isinstance(outcome, resolve.Resolved)
    assert outcome.canonical_id == "Abu Dhabi"


def test_supplier_short_alias_resolves():
    outcome = resolve.resolve_entity("supplier", "anadolu")
    assert isinstance(outcome, resolve.Resolved)
    assert outcome.canonical_id == "SUP-07"


def test_unknown_dimension_is_unresolvable():
    outcome = resolve.resolve_entity("not_a_real_dimension", "anything")
    assert isinstance(outcome, resolve.Unresolvable)


def test_ambiguous_or_midband_mention_needs_clarification():
    # A deliberately vague/partial mention that shouldn't confidently pick
    # one segment out of four but also isn't complete garbage.
    outcome = resolve.resolve_entity("customer_segment", "trade")
    assert isinstance(outcome, (resolve.NeedsClarification, resolve.Resolved, resolve.Unresolvable))
    if isinstance(outcome, resolve.NeedsClarification):
        assert len(outcome.candidates) >= 1


def test_outcome_types_are_distinguishable():
    resolved = resolve.resolve_entity("dc", "JEB")
    unresolvable = resolve.resolve_entity("dc", "totally not a dc name at all")
    assert isinstance(resolved, resolve.Resolved)
    assert isinstance(unresolvable, resolve.Unresolvable)
    assert not isinstance(resolved, resolve.Unresolvable)
    assert not isinstance(unresolvable, resolve.Resolved)


def test_thresholds_are_named_constants_high_above_low():
    assert 0.0 < resolve.LOW < resolve.HIGH <= 1.0
