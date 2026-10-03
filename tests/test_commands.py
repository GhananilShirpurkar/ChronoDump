"""Unit and integration tests for ChronoDump slash commands: /today, /queue, /notes, /focus, /stats, /export."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from app.bot.messages import (
    format_focus_status,
    format_notes_view,
    format_queue_header,
    format_stats_view,
    format_today_agenda,
)
from app.storage.database import (
    cancel_reminder,
    create_dump,
    create_reminder,
    engine,
    get_export_markdown,
    get_or_create_user,
    get_pending_reminders,
    get_recent_notes,
    get_stats,
    get_today_reminders,
    get_user_focus,
    set_user_focus,
)
from app.storage.models import Base


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_today_agenda_query_and_formatting():
    tz = ZoneInfo("Asia/Kolkata")
    user_id = 999111
    get_or_create_user(user_id, "Asia/Kolkata")
    now = datetime.now(tz)

    # 1. Reminder for today
    rem_today = create_reminder(
        user_id=user_id,
        task="Finish report",
        target_timestamp=now + timedelta(hours=2),
        display_time="Tonight @ 8:00 PM",
    )
    # 2. Reminder for tomorrow (should not appear in /today)
    rem_tmrw = create_reminder(
        user_id=user_id,
        task="Next day task",
        target_timestamp=now + timedelta(days=1, hours=2),
        display_time="Tomorrow @ 9:00 AM",
    )

    today_rems = get_today_reminders(user_id, tz)
    assert len(today_rems) == 1
    assert today_rems[0].task == "Finish report"

    card = format_today_agenda(now, today_rems, [{"action": "Buy paper"}], 3)
    assert "TODAY'S RADAR" in card
    assert "Finish report" in card
    assert "Buy paper" in card


def test_queue_pending_and_cancellation():
    user_id = 999222
    get_or_create_user(user_id, "UTC")
    now = datetime.now(timezone.utc)

    r1 = create_reminder(user_id, "Task 1", now + timedelta(hours=1), "In 1h")
    r2 = create_reminder(user_id, "Task 2", now + timedelta(hours=2), "In 2h")

    pending = get_pending_reminders(user_id)
    assert len(pending) == 2

    # Cancel r1
    cancelled = cancel_reminder(r1.id)
    assert cancelled.status == "cancelled"

    pending_after = get_pending_reminders(user_id)
    assert len(pending_after) == 1
    assert pending_after[0].id == r2.id


def test_focus_mode_lifecycle():
    user_id = 999333
    get_or_create_user(user_id, "UTC")
    now = datetime.now(timezone.utc)

    # Initially not in focus mode
    assert get_user_focus(user_id) is None

    # Set focus for 2 hours
    focus_target = now + timedelta(hours=2)
    set_user_focus(user_id, focus_target)

    active_focus = get_user_focus(user_id)
    assert active_focus is not None
    assert (active_focus - now).total_seconds() > 7000

    msg = format_focus_status(active_focus, now)
    assert "DEEP FOCUS ACTIVE" in msg

    # Clear focus
    set_user_focus(user_id, None)
    assert get_user_focus(user_id) is None


def test_notes_view_and_export():
    user_id = 999444
    get_or_create_user(user_id, "Asia/Kolkata")

    create_dump(
        user_id=user_id,
        raw_content="Raw dump 1",
        input_type="voice",
        clean_notes=["Fact A: Database architecture", "Fact B: API pattern"],
        action_items=["Buy groceries"],
    )

    notes = get_recent_notes(user_id)
    assert len(notes) == 2
    assert notes[0]["note"] == "Fact A: Database architecture"

    notes_msg = format_notes_view(notes)
    assert "CLEAN NOTES REPOSITORY" in notes_msg
    assert "Fact A: Database architecture" in notes_msg

    # Test export document
    tz = ZoneInfo("Asia/Kolkata")
    md = get_export_markdown(user_id, tz)
    assert "# ChronoDump Export" in md
    assert "Fact A: Database architecture" in md
    assert "[ ] Buy groceries" in md


def test_stats_view():
    user_id = 999555
    get_or_create_user(user_id, "UTC")
    stats = get_stats(user_id)
    assert "whisper_model" in stats
    assert "ollama_model" in stats
    assert "db_size_kb" in stats

    msg = format_stats_view(stats)
    assert "CHRONODUMP SYSTEM & AI STATS" in msg
    assert "faster-whisper" in msg
    assert "Ollama" in msg
