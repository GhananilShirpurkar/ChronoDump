"""Database connection, session management, and CRUD helpers."""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.storage.models import Base, Dump, Reminder, User, VagueClarification, utc_now

logger = logging.getLogger(__name__)

# Create SQLAlchemy synchronous engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Initialize database tables and run lightweight migrations."""
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN focus_until DATETIME;"))
            conn.commit()
    except Exception:
        pass  # Column already exists
    logger.info("Database initialized successfully.")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for transactional database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# User CRUD operations
def get_or_create_user(telegram_id: int, default_timezone: Optional[str] = None) -> User:
    """Retrieve existing user or register a new one."""
    with get_db() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            tz = default_timezone or settings.DEFAULT_TIMEZONE
            user = User(telegram_id=telegram_id, timezone=tz)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Registered new user {telegram_id} with timezone {tz}")
        return user


def get_user_timezone(telegram_id: int) -> ZoneInfo:
    """Return user's ZoneInfo object."""
    with get_db() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        tz_name = user.timezone if user else settings.DEFAULT_TIMEZONE
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo("UTC")


def update_user_timezone(telegram_id: int, new_timezone: str) -> bool:
    """Update user's timezone."""
    try:
        # Validate timezone name
        ZoneInfo(new_timezone)
    except Exception as e:
        logger.error(f"Invalid timezone {new_timezone}: {e}")
        return False

    with get_db() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.timezone = new_timezone
            user.updated_at = utc_now()
            session.commit()
            return True
        else:
            user = User(telegram_id=telegram_id, timezone=new_timezone)
            session.add(user)
            session.commit()
            return True


# Dump CRUD operations
def create_dump(
    user_id: int,
    raw_content: str,
    input_type: str,
    summary: Optional[str] = None,
    clean_notes: Optional[List[str]] = None,
    action_items: Optional[List[str]] = None,
) -> Dump:
    """Record a raw brain dump and its structured interpretation."""
    with get_db() as session:
        dump = Dump(
            user_id=user_id,
            raw_content=raw_content,
            input_type=input_type,
            summary=summary,
        )
        if clean_notes:
            dump.clean_notes = clean_notes
        if action_items:
            dump.action_items = action_items
        session.add(dump)
        session.commit()
        session.refresh(dump)
        return dump


# Reminder CRUD operations
def create_reminder(
    user_id: int,
    task: str,
    target_timestamp: datetime,
    display_time: str,
    confidence: str = "exact",
    dump_id: Optional[int] = None,
    scheduler_job_id: Optional[str] = None,
) -> Reminder:
    """Create and persist a scheduled reminder."""
    # Convert to UTC for uniform SQLite persistence
    if target_timestamp.tzinfo is not None:
        target_timestamp = target_timestamp.astimezone(timezone.utc)
    else:
        target_timestamp = target_timestamp.replace(tzinfo=timezone.utc)

    with get_db() as session:
        reminder = Reminder(
            user_id=user_id,
            dump_id=dump_id,
            task=task,
            target_timestamp=target_timestamp,
            display_time=display_time,
            confidence=confidence,
            status="pending",
            scheduler_job_id=scheduler_job_id,
        )
        session.add(reminder)
        session.commit()
        session.refresh(reminder)
        return reminder


def get_reminder(reminder_id: int) -> Optional[Reminder]:
    """Retrieve reminder by primary key."""
    with get_db() as session:
        return session.query(Reminder).filter(Reminder.id == reminder_id).first()


def update_reminder_job_id(reminder_id: int, scheduler_job_id: str) -> None:
    """Associate scheduler job ID with reminder."""
    with get_db() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.scheduler_job_id = scheduler_job_id
            session.commit()


def mark_reminder_fired(reminder_id: int) -> None:
    """Mark reminder as fired."""
    with get_db() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder and reminder.status == "pending":
            reminder.status = "fired"
            reminder.updated_at = utc_now()
            session.commit()


def snooze_reminder(reminder_id: int, new_target: datetime, new_display_time: str, new_job_id: str) -> Optional[Reminder]:
    """Snooze a reminder to a new time."""
    if new_target.tzinfo is not None:
        new_target = new_target.astimezone(timezone.utc)
    else:
        new_target = new_target.replace(tzinfo=timezone.utc)

    with get_db() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.target_timestamp = new_target
            reminder.display_time = new_display_time
            reminder.scheduler_job_id = new_job_id
            reminder.status = "snoozed"
            reminder.snooze_count += 1
            reminder.updated_at = utc_now()
            session.commit()
            session.refresh(reminder)
            return reminder
        return None


def complete_reminder(reminder_id: int) -> Optional[Reminder]:
    """Mark a reminder as completed."""
    with get_db() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.status = "completed"
            reminder.completed_at = utc_now()
            reminder.updated_at = utc_now()
            session.commit()
            session.refresh(reminder)
            return reminder
        return None


def undo_complete_reminder(reminder_id: int) -> Optional[Reminder]:
    """Revert completed reminder back to fired or pending status."""
    with get_db() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder and reminder.status == "completed":
            reminder.status = "fired"
            reminder.completed_at = None
            reminder.updated_at = utc_now()
            session.commit()
            session.refresh(reminder)
            return reminder
        return None


# Vague Clarification CRUD operations
def create_vague_clarification(
    user_id: int,
    task: str,
    window: str,
    clarify_at: datetime,
    options: List[str],
    dump_id: Optional[int] = None,
    scheduler_job_id: Optional[str] = None,
) -> VagueClarification:
    """Record an ambiguous reminder scheduled for clarification."""
    with get_db() as session:
        clarification = VagueClarification(
            user_id=user_id,
            dump_id=dump_id,
            task=task,
            window=window,
            clarify_at=clarify_at,
            options=options,
            status="pending",
            scheduler_job_id=scheduler_job_id,
        )
        session.add(clarification)
        session.commit()
        session.refresh(clarification)
        return clarification


def get_vague_clarification(clarification_id: int) -> Optional[VagueClarification]:
    """Retrieve vague clarification by primary key."""
    with get_db() as session:
        return session.query(VagueClarification).filter(VagueClarification.id == clarification_id).first()


def resolve_vague_clarification(clarification_id: int, status: str) -> None:
    """Mark clarification resolved (e.g. 'clarified', 'dismissed_no_rush')."""
    with get_db() as session:
        clarification = session.query(VagueClarification).filter(VagueClarification.id == clarification_id).first()
        if clarification:
            clarification.status = status
            session.commit()


# ---------------------------------------------------------------------------
# Slash Command Helpers (Focus, Today, Queue, Notes, Stats, Export)
# ---------------------------------------------------------------------------

def get_user_focus(telegram_id: int) -> Optional[datetime]:
    """Retrieve active focus_until datetime for user if active."""
    with get_db() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.focus_until:
            now = utc_now()
            # If focus_until is naive, treat as UTC
            focus_dt = user.focus_until.replace(tzinfo=timezone.utc) if user.focus_until.tzinfo is None else user.focus_until
            if focus_dt > now:
                return focus_dt
            else:
                user.focus_until = None
                session.commit()
    return None


def set_user_focus(telegram_id: int, focus_until: Optional[datetime]) -> None:
    """Update user focus_until datetime or clear it."""
    with get_db() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.focus_until = focus_until
            user.updated_at = utc_now()
            session.commit()


def get_today_reminders(user_id: int, user_tz: ZoneInfo) -> List[Reminder]:
    """Retrieve reminders scheduled for the current calendar day in user's timezone."""
    now = datetime.now(user_tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    with get_db() as session:
        reminders = (
            session.query(Reminder)
            .filter(
                Reminder.user_id == user_id,
                Reminder.status.in_(["pending", "snoozed", "fired"]),
            )
            .order_by(Reminder.target_timestamp.asc())
            .all()
        )
        # Filter in Python to reliably handle timezone conversions
        today_list = []
        for r in reminders:
            ts = r.target_timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_local = ts.astimezone(user_tz)
            if start_of_day <= ts_local <= end_of_day:
                today_list.append(r)
        return today_list


def get_pending_reminders(user_id: int) -> List[Reminder]:
    """Retrieve all pending or snoozed reminders for user."""
    with get_db() as session:
        return (
            session.query(Reminder)
            .filter(
                Reminder.user_id == user_id,
                Reminder.status.in_(["pending", "snoozed", "fired"]),
            )
            .order_by(Reminder.target_timestamp.asc())
            .all()
        )


def cancel_reminder(reminder_id: int) -> Optional[Reminder]:
    """Cancel a reminder."""
    with get_db() as session:
        reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.status = "cancelled"
            reminder.updated_at = utc_now()
            session.commit()
            session.refresh(reminder)
            return reminder
        return None


def get_recent_notes(user_id: int, limit: int = 15) -> List[dict]:
    """Retrieve recent clean notes extracted from dumps."""
    with get_db() as session:
        dumps = (
            session.query(Dump)
            .filter(Dump.user_id == user_id)
            .order_by(Dump.created_at.desc())
            .limit(limit)
            .all()
        )
        notes = []
        for d in dumps:
            for note in d.clean_notes:
                notes.append({"note": note, "created_at": d.created_at, "input_type": d.input_type})
        return notes


def get_recent_action_items(user_id: int, limit: int = 15) -> List[dict]:
    """Retrieve recent action items without deadlines."""
    with get_db() as session:
        dumps = (
            session.query(Dump)
            .filter(Dump.user_id == user_id)
            .order_by(Dump.created_at.desc())
            .limit(limit)
            .all()
        )
        items = []
        for d in dumps:
            for action in d.action_items:
                items.append({"action": action, "created_at": d.created_at})
        return items


def get_stats(user_id: int) -> dict:
    """Retrieve system, AI model, and user activity statistics."""
    from pathlib import Path
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    db_size_kb = round(db_path.stat().st_size / 1024, 1) if db_path.exists() else 0.0

    with get_db() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        dump_count = session.query(Dump).filter(Dump.user_id == user_id).count()
        total_reminders = session.query(Reminder).filter(Reminder.user_id == user_id).count()
        active_reminders = (
            session.query(Reminder)
            .filter(
                Reminder.user_id == user_id,
                Reminder.status.in_(["pending", "snoozed", "fired"]),
            )
            .count()
        )
        completed_reminders = (
            session.query(Reminder)
            .filter(
                Reminder.user_id == user_id,
                Reminder.status == "completed",
            )
            .count()
        )

    return {
        "timezone": user.timezone if user else settings.DEFAULT_TIMEZONE,
        "dump_count": dump_count,
        "total_reminders": total_reminders,
        "active_reminders": active_reminders,
        "completed_reminders": completed_reminders,
        "db_size_kb": db_size_kb,
        "whisper_model": settings.WHISPER_MODEL,
        "whisper_device": settings.WHISPER_DEVICE,
        "whisper_compute": settings.WHISPER_COMPUTE_TYPE,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_url": settings.OLLAMA_BASE_URL,
    }


def get_export_markdown(user_id: int, user_tz: ZoneInfo) -> str:
    """Format complete user notes, action items, and reminders into a clean Markdown document."""
    now = datetime.now(user_tz)
    now_str = now.strftime("%Y-%m-%d %H:%M %Z")

    notes_data = get_recent_notes(user_id, limit=100)
    actions_data = get_recent_action_items(user_id, limit=100)
    pending = get_pending_reminders(user_id)

    with get_db() as session:
        completed = (
            session.query(Reminder)
            .filter(Reminder.user_id == user_id, Reminder.status == "completed")
            .order_by(Reminder.completed_at.desc())
            .limit(50)
            .all()
        )

    doc = [
        f"# ChronoDump Export — {now.strftime('%b %d, %Y')}",
        f"\n*Exported on {now_str}*\n",
        "## 📋 Clean Notes & Context",
    ]
    if notes_data:
        for item in notes_data:
            doc.append(f"- {item['note']}")
    else:
        doc.append("_No notes stored._")

    doc.append("\n## ✅ Open Action Items (No Time Constraints)")
    if actions_data:
        for act in actions_data:
            doc.append(f"- [ ] {act['action']}")
    else:
        doc.append("_No open action items._")

    doc.append("\n## ⏰ Active & Upcoming Reminders")
    if pending:
        for r in pending:
            doc.append(f"- [ ] **{r.task}** — Scheduled for `{r.display_time}`")
    else:
        doc.append("_No active reminders._")

    doc.append("\n## ✔️ Recently Completed Tasks")
    if completed:
        for c in completed:
            done_at = c.completed_at.strftime("%b %d, %H:%M") if c.completed_at else "completed"
            doc.append(f"- [x] **{c.task}** *(Done on {done_at})*")
    else:
        doc.append("_No completed tasks yet._")

    return "\n".join(doc)
