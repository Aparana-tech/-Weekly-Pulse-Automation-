"""
ISO Week Utilities — Helpers for ISO week calculations.

Provides functions for:
- Getting the current ISO week
- Parsing ISO week strings (e.g., '2026-W23')
- Computing date ranges for ISO weeks and review windows
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta


def current_iso_week() -> tuple[int, int]:
    """
    Get the current ISO year and week number.

    Returns
    -------
    tuple[int, int]
        (iso_year, iso_week)
    """
    today = date.today()
    iso_cal = today.isocalendar()
    return iso_cal[0], iso_cal[1]


def parse_iso_week(week_str: str) -> tuple[int, int]:
    """
    Parse an ISO week string into (year, week).

    Parameters
    ----------
    week_str
        ISO week string, e.g., '2026-W23' or '2026-W03'.

    Returns
    -------
    tuple[int, int]
        (iso_year, iso_week)

    Raises
    ------
    ValueError
        If the string format is invalid or the week number is out of range.
    """
    match = re.match(r"^(\d{4})-W(\d{1,2})$", week_str.strip())
    if not match:
        raise ValueError(
            f"Invalid ISO week format: '{week_str}'. Expected format: YYYY-Www (e.g., 2026-W23)."
        )

    year = int(match.group(1))
    week = int(match.group(2))

    if week < 1 or week > 53:
        raise ValueError(f"ISO week must be 1-53, got {week}.")

    # Validate that this week actually exists in the given year
    # ISO years can have 52 or 53 weeks
    max_week = _max_iso_week(year)
    if week > max_week:
        raise ValueError(f"Year {year} only has {max_week} ISO weeks, got W{week:02d}.")

    return year, week


def iso_week_date_range(year: int, week: int) -> tuple[date, date]:
    """
    Get the start (Monday) and end (Sunday) dates for an ISO week.

    Parameters
    ----------
    year
        ISO year.
    week
        ISO week number.

    Returns
    -------
    tuple[date, date]
        (start_date_monday, end_date_sunday)
    """
    # ISO week 1 contains the first Thursday of the year
    jan4 = date(year, 1, 4)
    # Monday of ISO week 1
    week1_monday = jan4 - timedelta(days=jan4.weekday())
    # Monday of the target week
    target_monday = week1_monday + timedelta(weeks=week - 1)
    target_sunday = target_monday + timedelta(days=6)
    return target_monday, target_sunday


def review_window_range(
    year: int, week: int, window_weeks: int = 10
) -> tuple[datetime, datetime]:
    """
    Compute the review ingestion date window ending at the given ISO week.

    Parameters
    ----------
    year
        ISO year.
    week
        ISO week number.
    window_weeks
        Number of weeks to look back (default: 10).

    Returns
    -------
    tuple[datetime, datetime]
        (window_start, window_end) as datetime objects.
    """
    _, end_date = iso_week_date_range(year, week)
    start_date = end_date - timedelta(weeks=window_weeks)

    return (
        datetime.combine(start_date, datetime.min.time()),
        datetime.combine(end_date, datetime.max.time().replace(microsecond=0)),
    )


def format_iso_week(year: int, week: int) -> str:
    """Format ISO year and week as a string (e.g., '2026-W23')."""
    return f"{year}-W{week:02d}"


def _max_iso_week(year: int) -> int:
    """Return the maximum ISO week number for a given year (52 or 53)."""
    # Dec 28 is always in the last ISO week of the year
    dec28 = date(year, 12, 28)
    return dec28.isocalendar()[1]
