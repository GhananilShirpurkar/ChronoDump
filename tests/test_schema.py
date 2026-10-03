"""Unit tests for Pydantic schema validation and JSON parsing."""

import json
import pytest
from pydantic import ValidationError

from app.intelligence.llm import LLMClient
from app.intelligence.schema import ExtractedDump, ScheduledReminder, VagueReminder


def test_extracted_dump_valid_schema() -> None:
    data = {
        "summary": "Chapter 4, final report, water, and laundry",
        "clean_notes": ["Final report is for database systems"],
        "action_items": ["Review notes"],
        "scheduled_reminders": [
            {
                "task": "Read Chapter 4",
                "raw_time_expression": "tonight by 10",
                "target_timestamp": "2026-10-02T22:00:00+05:30",
                "display_time": "Tonight @ 10:00 PM",
                "confidence": "exact",
            }
        ],
        "vague_reminders": [
            {
                "task": "Pick up laundry",
                "window": "this_weekend",
                "clarify_at": "2026-10-02T17:00:00+05:30",
                "options": ["Saturday 9:00 AM", "Sunday 9:00 AM", "No rush"],
            }
        ],
    }
    dump = ExtractedDump.model_validate(data)
    assert dump.summary == "Chapter 4, final report, water, and laundry"
    assert len(dump.clean_notes) == 1
    assert len(dump.action_items) == 1
    assert len(dump.scheduled_reminders) == 1
    assert dump.scheduled_reminders[0].task == "Read Chapter 4"
    assert len(dump.vague_reminders) == 1


def test_clean_and_parse_json_with_codeblock() -> None:
    client = LLMClient()
    raw = """```json
    {
      "summary": "Test dump",
      "clean_notes": [],
      "action_items": [],
      "scheduled_reminders": [],
      "vague_reminders": []
    }
    ```"""
    parsed = client._clean_and_parse_json(raw)
    assert parsed["summary"] == "Test dump"


def test_clean_and_parse_json_raw_string() -> None:
    client = LLMClient()
    raw = '{"summary": "Simple test", "clean_notes": ["Note 1"]}'
    parsed = client._clean_and_parse_json(raw)
    assert parsed["summary"] == "Simple test"
    assert parsed["clean_notes"] == ["Note 1"]
