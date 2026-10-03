"""Deterministic Python Temporal Engine for resolving natural time expressions into timezone-aware datetimes."""

import re
from datetime import datetime, time, timedelta
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo
from dateutil import parser as date_parser

# Word-to-number mapping for common spoken words
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
}

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


def word_to_int(text: str) -> Optional[int]:
    """Convert spoken number word or digits to integer."""
    text = text.lower().strip()
    if text.isdigit():
        return int(text)
    if text in NUMBER_WORDS:
        return NUMBER_WORDS[text]
    return None


class TemporalEngine:
    """Resolves natural language time references against a reference datetime in a specific timezone."""

    @staticmethod
    def format_display_time(target_dt: datetime, ref_now: datetime) -> str:
        """Format a human-readable display string matching PRD convention."""
        # Convert both to same tz
        tz = ref_now.tzinfo
        if target_dt.tzinfo != tz and tz is not None:
            target_dt = target_dt.astimezone(tz)

        delta = target_dt - ref_now
        total_seconds = delta.total_seconds()

        # Relative minutes if very close
        if 0 <= total_seconds < 3600:
            minutes = max(1, round(total_seconds / 60))
            if minutes == 1:
                return "In 1 minute"
            return f"In {minutes} minutes"

        is_today = (target_dt.date() == ref_now.date())
        is_tomorrow = (target_dt.date() == (ref_now + timedelta(days=1)).date())

        time_str = target_dt.strftime("%I:%M %p").lstrip("0")
        if target_dt.minute == 0:
            # e.g., 10:00 PM -> 10:00 PM
            time_str = target_dt.strftime("%I:%M %p").lstrip("0")

        if is_today:
            if target_dt.hour >= 18:
                return f"Tonight @ {time_str}"
            elif target_dt.hour >= 12:
                return f"This afternoon @ {time_str}"
            else:
                return f"Today @ {time_str}"
        elif is_tomorrow:
            if target_dt.hour < 12:
                return f"Tomorrow morning @ {time_str}"
            else:
                return f"Tomorrow @ {time_str}"
        else:
            month_day = target_dt.strftime("%b %-d")
            return f"{month_day} @ {time_str}"

    @classmethod
    def resolve_expression(
        cls, expression: str, ref_now: datetime
    ) -> Tuple[Optional[datetime], Optional[str], str]:
        """
        Parse natural language temporal expression into (target_datetime, display_time, confidence).
        ref_now must be timezone-aware.
        """
        expr = expression.strip().lower()
        tz = ref_now.tzinfo

        # 1. "in X minutes / seconds / hours / days"
        rel_match = re.search(
            r"\bin\s+([a-zA-Z0-9]+|\d+)\s*(mins?|minutes?|secs?|seconds?|hours?|hrs?|days?)\b",
            expr,
        )
        if rel_match:
            num_raw = rel_match.group(1)
            unit = rel_match.group(2)
            num = word_to_int(num_raw)
            if num is not None:
                if unit.startswith("sec"):
                    target = ref_now + timedelta(seconds=num)
                elif unit.startswith("min"):
                    target = ref_now + timedelta(minutes=num)
                elif unit.startswith("hour") or unit.startswith("hr"):
                    target = ref_now + timedelta(hours=num)
                elif unit.startswith("day"):
                    target = ref_now + timedelta(days=num)
                else:
                    target = ref_now + timedelta(minutes=num)
                display = cls.format_display_time(target, ref_now)
                return target, display, "exact"

        # Half an hour
        if "half an hour" in expr or "in half hour" in expr:
            target = ref_now + timedelta(minutes=30)
            return target, cls.format_display_time(target, ref_now), "exact"

        # 2. "tonight by 10", "tonight at 10", "tonight @ 10:00 PM"
        tonight_match = re.search(
            r"tonight\s+(?:by|at|@)?\s*([a-zA-Z0-9]+|\d+)(?::(\d+))?\s*(am|pm)?",
            expr,
        )
        if tonight_match:
            hour_raw = tonight_match.group(1)
            min_raw = tonight_match.group(2)
            meridiem = tonight_match.group(3)
            hour = word_to_int(hour_raw)
            minute = int(min_raw) if min_raw else 0
            if hour is not None:
                if meridiem == "pm" or (meridiem is None and hour < 12):
                    hour = hour + 12 if hour != 12 else 12
                target = ref_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target < ref_now:
                    # If tonight at that hour already passed, move to tomorrow night or keep as is
                    target += timedelta(days=1)
                return target, cls.format_display_time(target, ref_now), "exact"

        # Bare "tonight"
        if re.search(r"\btonight\b", expr):
            target = ref_now.replace(hour=22, minute=0, second=0, microsecond=0)
            if target < ref_now:
                target = ref_now + timedelta(hours=2)
            return target, cls.format_display_time(target, ref_now), "inferred"

        # 3. "tomorrow morning" / "tomorrow afternoon" / "tomorrow evening" / "tomorrow night"
        if "tomorrow morning" in expr:
            tomorrow = ref_now + timedelta(days=1)
            target = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            return target, cls.format_display_time(target, ref_now), "inferred"
        if "tomorrow afternoon" in expr:
            tomorrow = ref_now + timedelta(days=1)
            target = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
            return target, cls.format_display_time(target, ref_now), "inferred"
        if "tomorrow evening" in expr:
            tomorrow = ref_now + timedelta(days=1)
            target = tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)
            return target, cls.format_display_time(target, ref_now), "inferred"
        if "tomorrow night" in expr:
            tomorrow = ref_now + timedelta(days=1)
            target = tomorrow.replace(hour=21, minute=0, second=0, microsecond=0)
            return target, cls.format_display_time(target, ref_now), "inferred"

        # "tomorrow at/by X [am/pm]"
        tmrw_match = re.search(
            r"tomorrow\s+(?:at|by|@)?\s*([a-zA-Z0-9]+|\d+)(?::(\d+))?\s*(am|pm)?",
            expr,
        )
        if tmrw_match and tmrw_match.group(1):
            hour_raw = tmrw_match.group(1)
            min_raw = tmrw_match.group(2)
            meridiem = tmrw_match.group(3)
            hour = word_to_int(hour_raw)
            minute = int(min_raw) if min_raw else 0
            if hour is not None:
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
                elif meridiem is None and 1 <= hour <= 7:
                    # e.g., tomorrow at 4 -> 4 PM default
                    hour += 12
                tomorrow = ref_now + timedelta(days=1)
                target = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return target, cls.format_display_time(target, ref_now), "exact"

        # Bare "tomorrow"
        if re.search(r"\btomorrow\b", expr):
            tomorrow = ref_now + timedelta(days=1)
            target = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            return target, cls.format_display_time(target, ref_now), "inferred"

        # 4. Weekdays: "next Friday", "this Friday", "on Friday at 5pm"
        for day_name, day_idx in WEEKDAYS.items():
            if re.search(rf"\b(?:next|this|on)?\s*{day_name}\b", expr):
                current_weekday = ref_now.weekday()
                days_ahead = (day_idx - current_weekday) % 7
                if days_ahead == 0 or "next" in expr:
                    days_ahead += 7
                target_date = ref_now.date() + timedelta(days=days_ahead)

                # Check for time spec
                time_match = re.search(r"(?:at|by|@)\s*(\d+)(?::(\d+))?\s*(am|pm)?", expr)
                if time_match:
                    h = int(time_match.group(1))
                    m = int(time_match.group(2)) if time_match.group(2) else 0
                    mer = time_match.group(3)
                    if mer == "pm" and h < 12:
                        h += 12
                    elif mer == "am" and h == 12:
                        h = 0
                    target = datetime.combine(target_date, time(h, m), tzinfo=tz)
                    conf = "exact"
                else:
                    # Default morning 09:00
                    target = datetime.combine(target_date, time(9, 0), tzinfo=tz)
                    conf = "inferred"
                return target, cls.format_display_time(target, ref_now), conf

        # 5. Date expressions: "3rd January", "January 3rd", "3rd Jan", "Jan 3", "due 3rd Jan"
        date_match = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
            expr,
        )
        if not date_match:
            date_match = re.search(
                r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
                expr,
            )
            if date_match:
                # swap groups to match day, month order
                day_val = date_match.group(2)
                month_val = date_match.group(1)
            else:
                day_val = None
                month_val = None
        else:
            day_val = date_match.group(1)
            month_val = date_match.group(2)

        if day_val and month_val:
            try:
                # Parse month and day
                parsed_partial = date_parser.parse(f"{month_val} {day_val}")
                year = ref_now.year
                target_date = datetime(year, parsed_partial.month, int(day_val)).date()

                # If date is earlier than today, roll to next year (e.g. today is Oct 2026, Jan 3 is 2027)
                if target_date < ref_now.date():
                    target_date = datetime(year + 1, parsed_partial.month, int(day_val)).date()

                # Check if explicit time is mentioned
                time_match = re.search(r"(?:at|by|@)\s*(\d+)(?::(\d+))?\s*(am|pm)?", expr)
                if time_match:
                    h = int(time_match.group(1))
                    m = int(time_match.group(2)) if time_match.group(2) else 0
                    mer = time_match.group(3)
                    if mer == "pm" and h < 12:
                        h += 12
                    elif mer == "am" and h == 12:
                        h = 0
                    target = datetime.combine(target_date, time(h, m), tzinfo=tz)
                    conf = "exact"
                else:
                    # Per PRD Section 13/15: "Jan 3 @ 11:59 PM — Submit Final Project Report"
                    target = datetime.combine(target_date, time(23, 59, 0), tzinfo=tz)
                    conf = "inferred"

                return target, cls.format_display_time(target, ref_now), conf
            except Exception:
                pass

        # 6. Fallback general dateutil parser
        try:
            parsed = date_parser.parse(expr, fuzzy=True, default=ref_now)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tz)
            else:
                parsed = parsed.astimezone(tz)
            if parsed < ref_now:
                # If parsed is past, try rolling by 1 day or 1 year
                if (ref_now - parsed).total_seconds() > 3600:
                    parsed = parsed + timedelta(days=1)
            return parsed, cls.format_display_time(parsed, ref_now), "inferred"
        except Exception:
            return None, None, "inferred"

    @classmethod
    def resolve_vague_window(cls, window: str, ref_now: datetime) -> Tuple[datetime, List[str]]:
        """
        Produce clarify_at boundary datetime and options list for vague expressions.
        """
        tz = ref_now.tzinfo
        window_clean = window.lower().strip()

        if "weekend" in window_clean:
            # PRD Section 12: "Friday 5:00 PM: You said this weekend. When should I remind you? [ Saturday ] [ Sunday ]"
            # Selected date default 09:00 AM
            current_weekday = ref_now.weekday()
            days_until_friday = (4 - current_weekday) % 7
            friday_5pm = ref_now.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(days=days_until_friday)

            # If today is already Friday after 17:00, or Saturday/Sunday, clarify immediately
            if ref_now >= friday_5pm or current_weekday in (4, 5, 6):
                clarify_at = ref_now + timedelta(seconds=1)
            else:
                clarify_at = friday_5pm

            options = ["Saturday 9:00 AM", "Sunday 9:00 AM", "No rush"]
            return clarify_at, options

        elif "week" in window_clean:
            # PRD Section 12: [ Mon ] [ Tue ] [ Wed ] [ Thu ] [ Fri ] [ No rush ]
            # Ping at earliest boundary: e.g. next morning 9 AM or immediate
            clarify_at = ref_now + timedelta(seconds=1)
            options = ["Tomorrow 9:00 AM", "In 2 days 9:00 AM", "Friday 9:00 AM", "No rush"]
            return clarify_at, options

        elif "later" in window_clean or "today" in window_clean:
            # PRD Section 12: "Later today" -> After an appropriate delay (e.g. 2 hours or 17:00)
            later = ref_now + timedelta(hours=2)
            if later.date() != ref_now.date():
                later = ref_now.replace(hour=20, minute=0, second=0, microsecond=0)
            options = ["In 1 hour", "Tonight 9:00 PM", "Tomorrow 9:00 AM", "No rush"]
            return later, options

        else:
            # Generic vague constraint
            clarify_at = ref_now + timedelta(hours=1)
            options = ["Today 6:00 PM", "Tomorrow 9:00 AM", "No rush"]
            return clarify_at, options

    @classmethod
    def validate_and_refine_reminder(
        cls,
        task: str,
        target_timestamp_str: Optional[str],
        raw_expr: Optional[str],
        ref_now: datetime,
    ) -> Tuple[datetime, str, str]:
        """
        Validates target timestamp from LLM or re-resolves using Python deterministic temporal engine.
        Ensures timestamp is timezone-aware and valid.
        """
        tz = ref_now.tzinfo

        # If raw expression is provided, prefer deterministic engine
        if raw_expr:
            resolved_dt, display_time, conf = cls.resolve_expression(raw_expr, ref_now)
            if resolved_dt is not None:
                return resolved_dt, display_time or cls.format_display_time(resolved_dt, ref_now), conf

        # Otherwise parse provided target_timestamp_str
        if target_timestamp_str:
            try:
                parsed = datetime.fromisoformat(target_timestamp_str)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=tz)
                else:
                    parsed = parsed.astimezone(tz)
                
                # If target is in the past, attempt to resolve from task text
                if parsed < ref_now:
                    resolved_dt, display_time, conf = cls.resolve_expression(task, ref_now)
                    if resolved_dt is not None and resolved_dt > ref_now:
                        return resolved_dt, display_time, conf
                    # If still past, push to future
                    parsed = parsed + timedelta(days=1)

                display = cls.format_display_time(parsed, ref_now)
                return parsed, display, "exact"
            except Exception:
                pass

        # Try parsing task string directly for time indicators
        resolved_dt, display_time, conf = cls.resolve_expression(task, ref_now)
        if resolved_dt is not None:
            return resolved_dt, display_time or cls.format_display_time(resolved_dt, ref_now), conf

        # Ultimate fallback: 2 hours from now
        fallback = ref_now + timedelta(hours=2)
        return fallback, cls.format_display_time(fallback, ref_now), "inferred"
