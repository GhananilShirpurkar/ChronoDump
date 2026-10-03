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
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
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
