"""Tests for copilot/dateutil.py's period_label — the one formatter shared
by the echo bar (pipeline.py) and the result contract (results.py), so a
period reads identically wherever it appears.
"""

from copilot import dateutil as D
from copilot.spec import Period


def _period(start, end=None, grain="month"):
    return Period(grain=grain, start=start, end=end or start)


def test_month_label_formats_iso_month():
    assert D.month_label("2026-06") == "Jun 2026"


def test_single_month_period_label():
    assert D.period_label(_period("2026-06")) == "Jun 2026"


def test_quarter_width_period_label_q1():
    assert D.period_label(_period("2026-01", "2026-03")) == "Q1 2026"


def test_quarter_width_period_label_q4():
    assert D.period_label(_period("2026-10", "2026-12")) == "Q4 2026"


def test_full_year_period_label_is_not_compacted():
    assert D.period_label(_period("2025-01", "2025-12")) == "Jan 2025 to Dec 2025"


def test_three_month_span_not_aligned_to_a_quarter_is_not_compacted():
    # Apr-Jun would be Q2, but Feb-Apr isn't any calendar quarter.
    assert D.period_label(_period("2026-02", "2026-04")) == "Feb 2026 to Apr 2026"


def test_quarter_width_but_spanning_a_year_boundary_is_not_compacted():
    assert D.period_label(_period("2025-11", "2026-01")) == "Nov 2025 to Jan 2026"


def test_arbitrary_two_month_range_uses_to_form():
    assert D.period_label(_period("2026-04", "2026-05")) == "Apr 2026 to May 2026"


def test_week_grain_single_week_returns_raw_iso_week():
    assert D.period_label(_period("2026-W10", grain="week")) == "2026-W10"


def test_week_grain_range_returns_raw_to_form():
    assert D.period_label(_period("2026-W10", "2026-W12", grain="week")) == "2026-W10 to 2026-W12"
