"""Canonicalizes a raw spec dict so two textually-different-but-semantically-
identical specs compare equal. Operates on plain dicts, not copilot.spec's
Pydantic models — the locked grammar has only month|week period grains, but
a model will occasionally emit a quarter or year token, and the normalizer
exists specifically to tolerate and canonicalize that input variant (see the
comment on pair p1 in eval/normalizer_pairs.yaml). Feeding a quarter/year
period straight into spec.py would just raise ValidationError.

Transformations:
  - quarter/year periods -> expanded to the equivalent month range (the
    canonical form is always the month range, never the quarter/year token).
  - filters sorted by dimension; values sorted within each filter.
  - filter dimension/values lowercased (entity resolution is
    case-insensitive per resolve.py, so case carries no meaning here).
  - breakdown_query defaults filled explicitly: top_n=10, sort="desc".

Never mutates its input.
"""

import copy
import json

_QUARTER_MONTHS = {"Q1": ("01", "03"), "Q2": ("04", "06"), "Q3": ("07", "09"), "Q4": ("10", "12")}


def _expand_period(period: dict) -> dict:
    grain = period.get("grain")
    if grain == "quarter":
        start_year, start_q = period["start"][:4], period["start"][5:]
        end_year, end_q = period["end"][:4], period["end"][5:]
        start_mm = _QUARTER_MONTHS[start_q][0]
        end_mm = _QUARTER_MONTHS[end_q][1]
        return {"grain": "month", "start": start_year + "-" + start_mm, "end": end_year + "-" + end_mm}
    if grain == "year":
        return {"grain": "month", "start": period["start"] + "-01", "end": period["end"] + "-12"}
    return dict(period)


def _normalize_filters(filters: list) -> list:
    normalized = [
        {"dimension": f["dimension"].lower(), "values": sorted(v.lower() for v in f["values"])}
        for f in filters
    ]
    normalized.sort(key=lambda f: f["dimension"])
    return normalized


def normalize_spec(raw: dict) -> dict:
    spec = copy.deepcopy(raw)

    for period_field in ("period", "period_a", "period_b"):
        if period_field in spec:
            spec[period_field] = _expand_period(spec[period_field])

    if spec.get("filters"):
        spec["filters"] = _normalize_filters(spec["filters"])

    if spec.get("spec_type") == "breakdown_query":
        spec.setdefault("top_n", 10)
        spec.setdefault("sort", "desc")

    return spec


def specs_equal(a: dict, b: dict) -> bool:
    return normalize_spec(a) == normalize_spec(b)


def to_canonical_json(spec: dict) -> str:
    return json.dumps(normalize_spec(spec), sort_keys=True)
