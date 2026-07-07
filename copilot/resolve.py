"""Entity resolution: a user's verbatim filter mention -> canonical ID.

Pure and deterministic — no database connection, no network. The catalog is
a static reference table sourced from copilot.constants (the same roster
data.generate.py uses to build the customers/skus/suppliers tables), so
resolve.py has no dependency on a live DuckDB connection at all.

Algorithm: exact case-insensitive match first (this is just the fuzzy score
hitting 1.0, no special-cased branch needed). Otherwise, normalized fuzzy
match against every alias of every catalog entry for the given dimension,
using difflib.SequenceMatcher — stdlib, deterministic, no extra dependency.

- score >= HIGH and exactly one candidate at/above HIGH -> Resolved.
- score >= HIGH but tied with another candidate at/above HIGH -> NeedsClarification
  (ambiguous, not confidently one thing).
- LOW <= score < HIGH -> NeedsClarification (plausible but not confident).
- score < LOW -> Unresolvable.

HIGH and LOW are tuned against tests/test_resolve.py's MUST_RESOLVE /
MUST_NOT_RESOLVE calibration tables — that test set IS the threshold spec.
"""

import difflib
import re
from dataclasses import dataclass

from copilot import constants as C

HIGH = 0.72
LOW = 0.52


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    display: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Resolved:
    canonical_id: str
    display: str
    score: float


@dataclass(frozen=True)
class NeedsClarification:
    value: str
    dimension: str
    candidates: tuple[CatalogEntry, ...]


@dataclass(frozen=True)
class Unresolvable:
    value: str
    dimension: str


ResolutionOutcome = Resolved | NeedsClarification | Unresolvable


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _score(value: str, alias: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(value), _normalize(alias)).ratio()


def _best_score(value: str, entry: CatalogEntry) -> float:
    return max(_score(value, alias) for alias in entry.aliases)


_DC_CATALOG = (
    CatalogEntry("JEB", "Jebel Ali", ("JEB", "Jebel Ali", "Jebel Ali DC")),
    CatalogEntry("AUH", "Abu Dhabi DC", ("AUH", "Abu Dhabi DC", "Abu Dhabi")),
)

_EMIRATE_CATALOG = tuple(CatalogEntry(e, e, (e,)) for e in C.EMIRATES)

_CATEGORY_DISPLAY = {
    "food_beverage": "Food & Beverage",
    "personal_care": "Personal Care",
    "home_care": "Home Care",
    "otc_pharma": "OTC Pharma",
    "baby_care": "Baby Care",
}
_CATEGORY_CATALOG = tuple(
    CatalogEntry(key, display, (display, key.replace("_", " ")))
    for key, display in _CATEGORY_DISPLAY.items()
)

_SEGMENT_DISPLAY = {
    "modern_trade": "Modern Trade",
    "traditional_trade": "Traditional Trade",
    "pharmacies": "Pharmacies",
    "horeca": "HORECA",
}
_SEGMENT_CATALOG = tuple(
    CatalogEntry(key, display, (display, key.replace("_", " ")))
    for key, display in _SEGMENT_DISPLAY.items()
)

_SUPPLIER_CATALOG = tuple(
    CatalogEntry(
        s["supplier_id"],
        s["supplier_name"],
        (s["supplier_name"], s["supplier_name"].split()[0]),
    )
    for s in C.SUPPLIERS_ROSTER
)

CATALOGS: dict[str, tuple[CatalogEntry, ...]] = {
    "dc": _DC_CATALOG,
    "emirate": _EMIRATE_CATALOG,
    "category": _CATEGORY_CATALOG,
    "customer_segment": _SEGMENT_CATALOG,
    "supplier": _SUPPLIER_CATALOG,
}


def resolve_entity(dimension: str, value: str) -> ResolutionOutcome:
    catalog = CATALOGS.get(dimension, ())
    if not catalog:
        return Unresolvable(value=value, dimension=dimension)

    scored = sorted(
        ((entry, _best_score(value, entry)) for entry in catalog),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top_entry, top_score = scored[0]

    if top_score >= HIGH:
        tied = [entry for entry, s in scored if s >= HIGH]
        if len(tied) == 1:
            return Resolved(canonical_id=top_entry.id, display=top_entry.display, score=top_score)
        return NeedsClarification(value=value, dimension=dimension, candidates=tuple(tied))

    if top_score >= LOW:
        banded = [entry for entry, s in scored if s >= LOW][:4]
        return NeedsClarification(value=value, dimension=dimension, candidates=tuple(banded))

    return Unresolvable(value=value, dimension=dimension)
