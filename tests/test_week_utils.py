"""
Tests for ISO week utilities.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.config.week_utils import (
    current_iso_week,
    format_iso_week,
    iso_week_date_range,
    parse_iso_week,
    review_window_range,
)


class TestCurrentISOWeek:
    """Test current_iso_week()."""

    def test_returns_tuple(self) -> None:
        result = current_iso_week()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_year_reasonable(self) -> None:
        year, _week = current_iso_week()
        assert 2020 <= year <= 2100

    def test_week_in_range(self) -> None:
        _, week = current_iso_week()
        assert 1 <= week <= 53


class TestParseISOWeek:
    """Test parse_iso_week()."""

    def test_standard_format(self) -> None:
        assert parse_iso_week("2026-W23") == (2026, 23)

    def test_single_digit_week(self) -> None:
        assert parse_iso_week("2026-W3") == (2026, 3)

    def test_padded_week(self) -> None:
        assert parse_iso_week("2026-W03") == (2026, 3)

    def test_week_1(self) -> None:
        assert parse_iso_week("2026-W01") == (2026, 1)

    def test_week_52(self) -> None:
        assert parse_iso_week("2026-W52") == (2026, 52)

    def test_whitespace_stripped(self) -> None:
        assert parse_iso_week("  2026-W23  ") == (2026, 23)

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ISO week format"):
            parse_iso_week("2026-23")

    def test_invalid_format_no_w_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid ISO week format"):
            parse_iso_week("2026W23")

    def test_week_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="ISO week must be 1-53"):
            parse_iso_week("2026-W0")

    def test_week_54_raises(self) -> None:
        with pytest.raises(ValueError, match="ISO week must be 1-53"):
            parse_iso_week("2026-W54")

    def test_week_53_in_year_without_53_raises(self) -> None:
        # 2025 has 52 weeks.
        with pytest.raises(ValueError, match="only has"):
            parse_iso_week("2025-W53")


class TestISOWeekDateRange:
    """Test iso_week_date_range()."""

    def test_known_week(self) -> None:
        # 2026-W01 starts on Monday Dec 29, 2025
        start, end = iso_week_date_range(2026, 1)
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday
        assert (end - start).days == 6

    def test_week_23_2026(self) -> None:
        start, end = iso_week_date_range(2026, 23)
        assert start.weekday() == 0
        assert end.weekday() == 6

    def test_start_before_end(self) -> None:
        start, end = iso_week_date_range(2026, 10)
        assert start < end


class TestReviewWindowRange:
    """Test review_window_range()."""

    def test_default_window(self) -> None:
        start, end = review_window_range(2026, 23)
        # Default is 10 weeks
        diff = (end - start).days
        assert 69 <= diff <= 71  # ~10 weeks

    def test_custom_window(self) -> None:
        start, end = review_window_range(2026, 23, window_weeks=8)
        diff = (end - start).days
        assert 55 <= diff <= 57  # ~8 weeks

    def test_start_is_datetime(self) -> None:
        start, end = review_window_range(2026, 23)
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_end_is_end_of_day(self) -> None:
        _, end = review_window_range(2026, 23)
        assert end.hour == 23
        assert end.minute == 59


class TestFormatISOWeek:
    """Test format_iso_week()."""

    def test_standard(self) -> None:
        assert format_iso_week(2026, 23) == "2026-W23"

    def test_padded(self) -> None:
        assert format_iso_week(2026, 3) == "2026-W03"

    def test_week_1(self) -> None:
        assert format_iso_week(2026, 1) == "2026-W01"
