"""SQLAlchemy models for ChronoDump."""

import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User preferences and authentication record."""
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    timezone = Column(String(64), nullable=False, default="UTC")
    focus_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    dumps = relationship("Dump", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    clarifications = relationship("VagueClarification", back_populates="user", cascade="all, delete-orphan")


class Dump(Base):
    """Voice note or text brain dump history."""
    __tablename__ = "dumps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    raw_content = Column(Text, nullable=False)
    input_type = Column(String(16), nullable=False, default="text")  # 'voice' or 'text'
    summary = Column(Text, nullable=True)
    clean_notes_json = Column(Text, nullable=False, default="[]")
    action_items_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="dumps")
    reminders = relationship("Reminder", back_populates="dump")
    clarifications = relationship("VagueClarification", back_populates="dump")

    @property
    def clean_notes(self) -> List[str]:
        try:
            return json.loads(self.clean_notes_json)
        except Exception:
            return []

    @clean_notes.setter
    def clean_notes(self, value: List[str]) -> None:
        self.clean_notes_json = json.dumps(value)

    @property
    def action_items(self) -> List[str]:
        try:
            return json.loads(self.action_items_json)
        except Exception:
            return []

    @action_items.setter
    def action_items(self, value: List[str]) -> None:
        self.action_items_json = json.dumps(value)


class Reminder(Base):
    """Scheduled task reminder record."""
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    dump_id = Column(Integer, ForeignKey("dumps.id", ondelete="SET NULL"), nullable=True)
    task = Column(Text, nullable=False)
    target_timestamp = Column(DateTime(timezone=True), nullable=False)
    display_time = Column(String(128), nullable=False)
    confidence = Column(String(16), nullable=False, default="exact")  # 'exact' or 'inferred'
    status = Column(String(32), nullable=False, default="pending")  # 'pending', 'fired', 'completed', 'snoozed', 'cancelled'
    snooze_count = Column(Integer, nullable=False, default=0)
    scheduler_job_id = Column(String(128), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="reminders")
    dump = relationship("Dump", back_populates="reminders")


class VagueClarification(Base):
    """Pending ambiguous reminder to be clarified at boundary."""
    __tablename__ = "vague_clarifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    dump_id = Column(Integer, ForeignKey("dumps.id", ondelete="SET NULL"), nullable=True)
    task = Column(Text, nullable=False)
    window = Column(String(64), nullable=False)  # 'this_weekend', 'this_week', 'later_today'
    clarify_at = Column(DateTime(timezone=True), nullable=False)
    options_json = Column(Text, nullable=False, default="[]")
    status = Column(String(32), nullable=False, default="pending")  # 'pending', 'clarified', 'dismissed_no_rush'
    scheduler_job_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="clarifications")
    dump = relationship("Dump", back_populates="clarifications")

    @property
    def options(self) -> List[str]:
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    @options.setter
    def options(self, value: List[str]) -> None:
        self.options_json = json.dumps(value)
