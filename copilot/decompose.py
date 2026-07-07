"""Contribution math and the residual gate. Pure Python, no SQL, no
database — compile_change_decomposition (compile.py) hands this module raw
per-member numerators and denominators; this module computes shares, rates,
contributions, and a residual, and decides whether the result is trustworthy
enough to show a member breakdown at all.

Supplier cuts of the OTIF family arrive here already at LINE grain — that
grain selection is compile.py's job (see registry.py's LineGrainVariant);
this module doesn't know or care which grain produced its rows, it just
computes contributions from whatever numerator/denominator pairs it's given.

Two independent paths, matching the two metric shapes in the registry:

- Additive metrics (revenue, order_count, stockout_count, inventory_value):
  contribution_i = value_b_i - value_a_i. All arithmetic is done in whatever
  integer unit the caller passes (fils for currency metrics, so a caller
  converts AED -> fils by multiplying by 100 before calling and divides back
  after) — integers only, so the residual is EXACTLY zero, never "close to".
- Ratio metrics (otif_pct, on_time_pct, in_full_pct, fill_rate_pct):
  contribution_i = share_b_i * rate_b_i - share_a_i * rate_a_i. Floating
  point, so the residual gate uses RATIO_RESIDUAL_REL_TOL instead of exact
  equality.

Both decompose_additive and decompose_ratio accept OPTIONAL externally
supplied totals (total_a/total_b, or total_num_a/total_den_a/...). Omitted,
the "true total" is just the sum of the member rows, which is always
self-consistent with those same rows and can never trip the residual gate
by itself. Supplied, it lets a caller cross-check the per-member breakdown
against an independently computed grand total (e.g. a plain metric_query
for the same two periods) — a real integrity check, catching cases like the
breakdown query's WHERE clause silently disagreeing with the total query's.
When the residual gate trips, the member breakdown is withheld entirely and
only totals are returned, with a reason string.
"""

from dataclasses import dataclass

RATIO_RESIDUAL_REL_TOL = 1e-9


@dataclass(frozen=True)
class AdditiveMemberContribution:
    member: str
    value_a: int
    value_b: int
    contribution: int


@dataclass(frozen=True)
class AdditiveDecompositionResult:
    members: tuple
    total_a: int
    total_b: int
    delta: int
    sum_of_contributions: int
    residual: int
    residual_ok: bool
    withheld: bool
    withheld_reason: str | None


@dataclass(frozen=True)
class RatioMemberContribution:
    member: str
    share_a: float
    rate_a: float
    share_b: float
    rate_b: float
    contribution: float


@dataclass(frozen=True)
class RatioDecompositionResult:
    members: tuple
    rate_a: float | None
    rate_b: float | None
    delta: float | None
    sum_of_contributions: float
    residual: float
    residual_ok: bool
    withheld: bool
    withheld_reason: str | None


def decompose_additive(rows, total_a: int | None = None, total_b: int | None = None) -> AdditiveDecompositionResult:
    """rows: iterable of (member, value_a, value_b) integers."""
    rows = list(rows)
    derived_total_a = sum(r[1] for r in rows)
    derived_total_b = sum(r[2] for r in rows)
    check_total_a = derived_total_a if total_a is None else total_a
    check_total_b = derived_total_b if total_b is None else total_b
    delta = check_total_b - check_total_a

    members = [
        AdditiveMemberContribution(member=member, value_a=value_a, value_b=value_b, contribution=value_b - value_a)
        for member, value_a, value_b in rows
    ]
    sum_of_contributions = sum(m.contribution for m in members)
    residual = sum_of_contributions - delta
    residual_ok = residual == 0

    reason = None
    if not residual_ok:
        reason = "residual " + str(residual) + " is nonzero; member breakdown withheld, totals only"

    return AdditiveDecompositionResult(
        members=tuple(members) if residual_ok else (),
        total_a=check_total_a,
        total_b=check_total_b,
        delta=delta,
        sum_of_contributions=sum_of_contributions,
        residual=residual,
        residual_ok=residual_ok,
        withheld=not residual_ok,
        withheld_reason=reason,
    )


def decompose_ratio(
    rows,
    total_num_a: float | None = None,
    total_den_a: float | None = None,
    total_num_b: float | None = None,
    total_den_b: float | None = None,
) -> RatioDecompositionResult:
    """rows: iterable of (member, num_a, den_a, num_b, den_b)."""
    rows = list(rows)
    derived_den_a = sum(r[2] for r in rows)
    derived_den_b = sum(r[4] for r in rows)
    derived_num_a = sum(r[1] for r in rows)
    derived_num_b = sum(r[3] for r in rows)

    check_num_a = derived_num_a if total_num_a is None else total_num_a
    check_den_a = derived_den_a if total_den_a is None else total_den_a
    check_num_b = derived_num_b if total_num_b is None else total_num_b
    check_den_b = derived_den_b if total_den_b is None else total_den_b

    rate_a = (check_num_a / check_den_a * 100.0) if check_den_a else None
    rate_b = (check_num_b / check_den_b * 100.0) if check_den_b else None
    delta = (rate_b - rate_a) if (rate_a is not None and rate_b is not None) else None

    members = []
    sum_of_contributions = 0.0
    for member, num_a, den_a, num_b, den_b in rows:
        share_a = (den_a / derived_den_a) if derived_den_a else 0.0
        rate_a_i = (num_a / den_a * 100.0) if den_a else 0.0
        share_b = (den_b / derived_den_b) if derived_den_b else 0.0
        rate_b_i = (num_b / den_b * 100.0) if den_b else 0.0
        contribution = share_b * rate_b_i - share_a * rate_a_i
        sum_of_contributions += contribution
        members.append(RatioMemberContribution(
            member=member, share_a=share_a, rate_a=rate_a_i, share_b=share_b, rate_b=rate_b_i,
            contribution=contribution,
        ))

    if delta is None:
        residual = 0.0
        residual_ok = True
    else:
        residual = sum_of_contributions - delta
        tolerance = RATIO_RESIDUAL_REL_TOL * max(abs(delta), 1.0)
        residual_ok = abs(residual) <= tolerance

    reason = None
    if not residual_ok:
        reason = "residual " + repr(residual) + " exceeds tolerance; member breakdown withheld, totals only"

    return RatioDecompositionResult(
        members=tuple(members) if residual_ok else (),
        rate_a=rate_a,
        rate_b=rate_b,
        delta=delta,
        sum_of_contributions=sum_of_contributions,
        residual=residual,
        residual_ok=residual_ok,
        withheld=not residual_ok,
        withheld_reason=reason,
    )
