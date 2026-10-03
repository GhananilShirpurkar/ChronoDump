"""LLM client interface for local Ollama inference, structured extraction, and repair."""

import json
import logging
import re
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
import ollama

from app.config import settings
from app.intelligence.prompts import EXTRACTION_USER_PROMPT, REPAIR_PROMPT, SYSTEM_PROMPT
from app.intelligence.schema import ExtractedDump, ScheduledReminder, VagueReminder
from app.intelligence.temporal import TemporalEngine

logger = logging.getLogger(__name__)


class LLMClient:
    """Manages asynchronous interaction with local Ollama instance."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.client = ollama.AsyncClient(host=self.base_url)

    async def extract_dump(
        self, user_input: str, user_timezone: ZoneInfo, ref_now: Optional[datetime] = None
    ) -> Tuple[ExtractedDump, bool]:
        """
        Process user brain dump into structured ExtractedDump.
        Returns (ExtractedDump, is_degraded).
        """
        now = ref_now or datetime.now(user_timezone)
        current_dt_str = now.isoformat()

        prompt = EXTRACTION_USER_PROMPT.format(
            current_datetime=current_dt_str,
            user_timezone=str(user_timezone),
            user_input=user_input,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw_response = ""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                format="json",
                options={"temperature": 0.1},
            )
            raw_response = response.get("message", {}).get("content", "")
            dump_data = self._clean_and_parse_json(raw_response)
            extracted = ExtractedDump.model_validate(dump_data)
            logger.info("Successfully extracted structured dump from Ollama on first attempt.")
            return self._refine_with_temporal_engine(extracted, now), False
        except Exception as first_error:
            logger.warning(f"First extraction attempt failed: {first_error}. Attempting repair retry...")

        # Failure 1 — Retry with repair prompt
        try:
            repair_user_prompt = REPAIR_PROMPT.format(
                invalid_json=raw_response,
                error_message=str(first_error),
                current_datetime=current_dt_str,
            )
            repair_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": repair_user_prompt},
            ]
            repair_response = await self.client.chat(
                model=self.model,
                messages=repair_messages,
                format="json",
                options={"temperature": 0.0},
            )
            repaired_text = repair_response.get("message", {}).get("content", "")
            dump_data = self._clean_and_parse_json(repaired_text)
            extracted = ExtractedDump.model_validate(dump_data)
            logger.info("Successfully repaired and extracted structured dump on retry.")
            return self._refine_with_temporal_engine(extracted, now), False
        except Exception as retry_error:
            logger.error(f"Repair retry also failed: {retry_error}. Falling back to degraded extraction.")

        # Failure 2 — Graceful degradation fallback (PRD Section 20)
        degraded = self._create_degraded_fallback(user_input, now)
        return degraded, True

    def _clean_and_parse_json(self, text: str) -> dict:
        """Strip markdown fences and load JSON."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        return json.loads(cleaned.strip())

    def _refine_with_temporal_engine(self, dump: ExtractedDump, ref_now: datetime) -> ExtractedDump:
        """
        Pass all extracted items through deterministic Python temporal engine
        to guarantee mathematical precision, timezone accuracy, and vague rule compliance.
        """
        refined_scheduled: list[ScheduledReminder] = []
        for r in dump.scheduled_reminders:
            target_dt, display_time, conf = TemporalEngine.validate_and_refine_reminder(
                task=r.task,
                target_timestamp_str=r.target_timestamp,
                raw_expr=r.raw_time_expression,
                ref_now=ref_now,
            )
            refined_scheduled.append(
                ScheduledReminder(
                    task=r.task,
                    raw_time_expression=r.raw_time_expression,
                    target_timestamp=target_dt.isoformat(),
                    display_time=display_time,
                    confidence=conf,
                )
            )

        refined_vague: list[VagueReminder] = []
        for v in dump.vague_reminders:
            clarify_at_dt, default_options = TemporalEngine.resolve_vague_window(v.window, ref_now)
            options = v.options if v.options else default_options
            refined_vague.append(
                VagueReminder(
                    task=v.task,
                    window=v.window,
                    clarify_at=clarify_at_dt.isoformat(),
                    options=options,
                )
            )

        dump.scheduled_reminders = refined_scheduled
        dump.vague_reminders = refined_vague
        return dump

    def _create_degraded_fallback(self, user_input: str, ref_now: datetime) -> ExtractedDump:
        """
        Create fallback ExtractedDump when LLM generation fails,
        preserving user's information and attempting deterministic extraction.
        """
        resolved_dt, display_time, conf = TemporalEngine.resolve_expression(user_input, ref_now)
        scheduled = []
        if resolved_dt:
            scheduled.append(
                ScheduledReminder(
                    task=user_input[:80].strip(),
                    raw_time_expression=user_input,
                    target_timestamp=resolved_dt.isoformat(),
                    display_time=display_time,
                    confidence=conf,
                )
            )

        return ExtractedDump(
            summary="Raw input captured (structured parsing degraded)",
            clean_notes=[f"Transcript: {user_input}"],
            action_items=[] if scheduled else [user_input],
            scheduled_reminders=scheduled,
            vague_reminders=[],
        )
