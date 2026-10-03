"""Unit tests for deterministic Python Temporal Engine."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from app.intelligence.temporal import TemporalEngine


@pytest.fixture
def ref_now() -> datetime:
    """Fixed reference datetime in UTC+5:30 (India Standard Time)."""
    tz = ZoneInfo("Asia/Kolkata")
    # Saturday, Oct 3, 2026 at 14:30:00 (2:30 PM)
    return datetime(2026, 10, 3, 14, 30, 0, tzinfo=tz)


def test_in_two_minutes(ref_now: datetime) -> None:
    expr = "in two minutes"
    target, display, conf = TemporalEngine.resolve_expression(expr, ref_now)
    assert target is not None
    assert (target - ref_now).total_seconds() == 120
    assert display == "In 2 minutes"
    assert conf == "exact"


def test_in_five_minutes_digits(ref_now: datetime) -> None:
    expr = "in 5 minutes"
    target, display, conf = TemporalEngine.resolve_expression(expr, ref_now)
    assert target is not None
    assert (target - ref_now).total_seconds() == 300
    assert display == "In 5 minutes"
    assert conf == "exact"


def test_tonight_by_10(ref_now: datetime) -> None:
    expr = "tonight by 10"
    target, display, conf = TemporalEngine.resolve_expression(expr, ref_now)
    assert target is not None
    assert target.hour == 22
    assert target.minute == 0
    assert target.date() == ref_now.date()
    assert "Tonight @" in display
    assert conf == "exact"


def test_tomorrow_morning(ref_now: datetime) -> None:
    expr = "tomorrow morning"
    target, display, conf = TemporalEngine.resolve_expression(expr, ref_now)
    assert target is not None
    assert target.hour == 9
    assert target.minute == 0
    assert target.day == ref_now.day + 1
    assert "Tomorrow morning @" in display
    assert conf == "inferred"


def test_3rd_january(ref_now: datetime) -> None:
    expr = "3rd January"
    target, display, conf = TemporalEngine.resolve_expression(expr, ref_now)
    assert target is not None
    assert target.month == 1
    assert target.day == 3
    # Oct 2026 -> next Jan 3 is 2027
    assert target.year == 2027
    assert target.hour == 23
    assert target.minute == 59
    assert "Jan 3 @" in display


def test_next_friday(ref_now: datetime) -> None:
    expr = "next Friday"
    target, display, conf = TemporalEngine.resolve_expression(expr, ref_now)
    assert target is not None
    assert target.weekday() == 4  # Friday
    assert target > ref_now


def test_vague_weekend_clarification(ref_now: datetime) -> None:
    clarify_at, options = TemporalEngine.resolve_vague_window("this_weekend", ref_now)
    assert clarify_at is not None
    assert "Saturday 9:00 AM" in options
    assert "Sunday 9:00 AM" in options
    assert "No rush" in options


def test_vague_week_clarification(ref_now: datetime) -> None:
    clarify_at, options = TemporalEngine.resolve_vague_window("this_week", ref_now)
    assert clarify_at is not None
    assert any("9:00 AM" in opt for opt in options)
    assert "No rush" in options


def test_vague_later_today_clarification(ref_now: datetime) -> None:
    clarify_at, options = TemporalEngine.resolve_vague_window("later_today", ref_now)
    assert clarify_at is not None
    assert clarify_at > ref_now
    assert "No rush" in options


def test_validate_and_refine_reminder(ref_now: datetime) -> None:
    target, display, conf = TemporalEngine.validate_and_refine_reminder(
        task="Finish report",
        target_timestamp_str=None,
        raw_expr="tonight by 10",
        ref_now=ref_now,
    )
    assert target is not None
    assert target.hour == 22
    assert "Tonight @" in display
