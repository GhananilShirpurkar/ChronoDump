"""Integration tests for Database persistence, APScheduler, Snooze, Complete, and Undo."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from app.scheduler.jobs import SchedulerService
from app.storage.database import (
    complete_reminder,
    create_dump,
    create_reminder,
    create_vague_clarification,
    get_or_create_user,
    get_reminder,
    init_db,
    snooze_reminder,
    undo_complete_reminder,
    update_user_timezone,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Reset DB tables before each test to guarantee isolation."""
    from app.storage.database import engine
    from app.storage.models import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_user_creation_and_timezone():
    user = get_or_create_user(12345678, "Asia/Kolkata")
    assert user.telegram_id == 12345678
    assert user.timezone == "Asia/Kolkata"

    # Update timezone
    assert update_user_timezone(12345678, "America/New_York")
    updated = get_or_create_user(12345678)
    assert updated.timezone == "America/New_York"

    # Reject invalid timezone
    assert not update_user_timezone(12345678, "Invalid/Timezone")


def test_dump_creation():
    dump = create_dump(
        user_id=12345678,
        raw_content="Read chapter 4 and buy coffee",
        input_type="text",
        summary="Chapter 4 reading",
        clean_notes=["Chapter 4 is needed for quiz"],
        action_items=["Buy coffee"],
    )
    assert dump.id is not None
    assert dump.clean_notes == ["Chapter 4 is needed for quiz"]
    assert dump.action_items == ["Buy coffee"]


def test_reminder_lifecycle_complete_and_undo():
    now = datetime.now(timezone.utc)
    target = now + timedelta(hours=1)

    reminder = create_reminder(
        user_id=12345678,
        task="Read Chapter 4",
        target_timestamp=target,
        display_time="In 1 hour",
    )
    assert reminder.id is not None
    assert reminder.status == "pending"

    # Mark complete
    completed = complete_reminder(reminder.id)
    assert completed.status == "completed"
    assert completed.completed_at is not None

    # Undo complete
    restored = undo_complete_reminder(reminder.id)
    assert restored.status == "fired"
    assert restored.completed_at is None


def test_reminder_snooze():
    now = datetime.now(timezone.utc)
    target = now + timedelta(hours=1)

    reminder = create_reminder(
        user_id=12345678,
        task="Drink water",
        target_timestamp=target,
        display_time="In 1 hour",
    )

    new_target = target + timedelta(minutes=30)
    snoozed = snooze_reminder(reminder.id, new_target, "In 1 hour 30 mins", "job_123")
    assert snoozed.status == "snoozed"
    assert snoozed.snooze_count == 1
    # SQLite naive vs aware comparison
    snoozed_ts = snoozed.target_timestamp.replace(tzinfo=timezone.utc) if snoozed.target_timestamp.tzinfo is None else snoozed.target_timestamp
    assert snoozed_ts == new_target


@pytest.mark.asyncio
async def test_apscheduler_persistence_and_restart(tmp_path):
    """Verify that jobs persist in SQLite jobstore across scheduler restarts."""
    jobstore_db = tmp_path / "test_scheduler.db"
    db_url = f"sqlite:///{jobstore_db}"

    # Instance 1: Schedule a job
    svc1 = SchedulerService(db_url=db_url)
    svc1.scheduler.start(paused=True)
    run_date = datetime.now(timezone.utc) + timedelta(minutes=10)
    job_id = svc1.schedule_reminder(reminder_id=999, run_date=run_date)
    assert job_id == "rem_999"

    # Check job exists in scheduler
    job = svc1.scheduler.get_job("rem_999")
    assert job is not None

    # Shut down instance 1
    svc1.shutdown(wait=False)

    # Instance 2: Start new scheduler instance pointing to the same SQLite db
    svc2 = SchedulerService(db_url=db_url)
    svc2.scheduler.start(paused=True)
    reloaded_job = svc2.scheduler.get_job("rem_999")
    assert reloaded_job is not None
    assert reloaded_job.id == "rem_999"

    svc2.shutdown(wait=False)
