"""Period <-> calendar date conversion shared by validate.py (window/overlap
checks) and compile.py (turning a Period into bound date parameters).

Deliberately separate from copilot/gen/util.py: that module belongs to the
data generator and this package's query layer (validate/compile) shouldn't
reach into generator internals for something as small as month arithmetic.
"""

import calendar
from datetime import date, datetime, timedelta

_QUARTER_START_MONTHS = {1, 4, 7, 10}


def month_label(month: str) -> str:
    """'YYYY-MM' -> 'Mon YYYY', e.g. '2026-06' -> 'Jun 2026'."""
    year, mon = int(month[:4]), int(month[5:7])
    return calendar.month_abbr[mon] + " " + str(year)


def _quarter_label(start: str, end: str) -> str | None:
    start_year, start_mon = int(start[:4]), int(start[5:7])
    end_year, end_mon = int(end[:4]), int(end[5:7])
    if start_year != end_year or start_mon not in _QUARTER_START_MONTHS or end_mon != start_mon + 2:
        return None
    quarter_number = (start_mon - 1) // 3 + 1
    return "Q" + str(quarter_number) + " " + str(start_year)


def period_label(period) -> str:
    """Deterministic, human-readable period label — the one place this
    formatting lives, shared by the echo bar (pipeline.py) and the result
    contract (results.py): a single month -> 'Jun 2026', an exact calendar
    quarter -> 'Q1 2026', anything else (including a full year) ->
    'start to end', e.g. 'Jan 2025 to Dec 2025'. Week grain has no quarter
    concept, so it always falls through to the raw ISO week string(s)."""
    if period.grain == "week":
        return period.start if period.start == period.end else period.start + " to " + period.end
    if period.start == period.end:
        return month_label(period.start)
    quarter = _quarter_label(period.start, period.end)
    if quarter:
        return quarter
    return month_label(period.start) + " to " + month_label(period.end)


def month_to_date_range(month: str) -> tuple[date, date]:
    year, mon = int(month[:4]), int(month[5:7])
    start = date(year, mon, 1)
    end = (date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)) - timedelta(days=1)
    return start, end


def week_to_date_range(week: str) -> tuple[date, date]:
    """ISO week string 'YYYY-Www' -> (Monday, Sunday)."""
    monday = datetime.strptime(f"{week}-1", "%G-W%V-%u").date()
    return monday, monday + timedelta(days=6)


def period_to_date_range(period) -> tuple[date, date]:
    if period.grain == "month":
        start, _ = month_to_date_range(period.start)
        _, end = month_to_date_range(period.end)
        return start, end
    start, _ = week_to_date_range(period.start)
    _, end = week_to_date_range(period.end)
    return start, end


def week_span_count(period) -> int:
    """Number of ISO weeks between period.start and period.end, inclusive."""
    start_monday, _ = week_to_date_range(period.start)
    end_monday, _ = week_to_date_range(period.end)
    return (end_monday - start_monday).days // 7 + 1


def month_range(start_month: str, end_month: str) -> list[str]:
    """List of 'YYYY-MM' strings from start_month to end_month, inclusive."""
    year, mon = int(start_month[:4]), int(start_month[5:7])
    end_year, end_mon = int(end_month[:4]), int(end_month[5:7])
    months = []
    while (year, mon) <= (end_year, end_mon):
        months.append("%04d-%02d" % (year, mon))
        mon += 1
        if mon > 12:
            mon, year = 1, year + 1
    return months


def month_starts(period) -> list[date]:
    """First-of-month date for every month spanning period.start..period.end
    (month grain only — used to build a series bucket spine)."""
    return [month_to_date_range(m)[0] for m in month_range(period.start, period.end)]


def week_starts(period) -> list[date]:
    """Monday date for every ISO week spanning period.start..period.end
    (week grain only — used to build a series bucket spine)."""
    start_monday, _ = week_to_date_range(period.start)
    end_monday, _ = week_to_date_range(period.end)
    result = []
    current = start_monday
    while current <= end_monday:
        result.append(current)
        current += timedelta(days=7)
    return result
