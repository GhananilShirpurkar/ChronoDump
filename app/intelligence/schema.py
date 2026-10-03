"""Pydantic v2 schemas for structured LLM input/output validation."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ScheduledReminder(BaseModel):
    """Action item with a resolved or proposed timestamp."""

    task: str = Field(description="Clear title or description of what needs to be done.")
    raw_time_expression: Optional[str] = Field(
        default=None, description="The original temporal phrasing extracted from speech (e.g. 'tonight by 10', 'in 2 minutes')."
    )
    target_timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 formatted timestamp including timezone offset (e.g. 2026-10-02T22:00:00+05:30).",
    )
    display_time: Optional[str] = Field(
        default=None, description="Human-friendly time label (e.g. 'Tonight @ 10:00 PM', 'In 2 minutes')."
    )
    confidence: str = Field(
        default="exact",
        description="'exact' if explicit time given, 'inferred' if logical default was used (e.g. morning -> 9 AM).",
    )


class VagueReminder(BaseModel):
    """Task with ambiguous temporal constraint requiring user clarification."""

    task: str = Field(description="Action item associated with the vague time window.")
    window: str = Field(
        description="Categorical window (e.g. 'this_weekend', 'this_week', 'later_today', 'sometime')."
    )
    clarify_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 timestamp with offset for when the bot should ping the user for clarification.",
    )
    options: List[str] = Field(
        default_factory=list,
        description="List of clarification options presented to user as buttons (e.g. ['Saturday 9:00 AM', 'Sunday 9:00 AM']).",
    )


class ExtractedDump(BaseModel):
    """Complete structured model output extracted from user's brain dump."""

    summary: str = Field(default="", description="One-line digest of the user's brain dump.")
    clean_notes: List[str] = Field(
        default_factory=list,
        description="Context, non-actionable thoughts, observations, ideas, and notes.",
    )
    action_items: List[str] = Field(
        default_factory=list,
        description="Actionable tasks that do NOT have any time constraints.",
    )
    scheduled_reminders: List[ScheduledReminder] = Field(
        default_factory=list,
        description="Actionable tasks with specific, resolvable deadlines or times.",
    )
    vague_reminders: List[VagueReminder] = Field(
        default_factory=list,
        description="Actionable tasks with ambiguous time references ('this weekend', 'later today', etc.).",
    )
