# ChronoDump Implementation Plan

## 1. Project Scaffolding & Dependencies
- Create `pyproject.toml`, `requirements.txt`, `.env.example`, `.env` with all configuration parameters.
- Initialize `uv` virtual environment and install core dependencies (`aiogram`, `faster-whisper`, `ollama`, `pydantic`, `apscheduler`, `sqlalchemy`, `python-dotenv`, `pytest`, `pytest-asyncio`).

## 2. Database Models & Persistence Layer (`app/storage/`)
- Implement SQLite / SQLAlchemy 2 async/sync models: `User` (timezone, auth), `Dump` (raw content, summary), `Reminder` (task text, target time, status, snooze count, vague metadata).
- Implement database session management and repository functions for user settings, dumps, reminders, and transaction safety.

## 3. Python Temporal Engine & Schemas (`app/intelligence/`)
- Define strict Pydantic v2 schemas matching PRD Section 13 (`ExtractedDump`, `ScheduledReminder`, `VagueReminder`).
- Build deterministic Python temporal engine (`app/intelligence/temporal.py`) handling relative offsets ("in 2 minutes", "in an hour"), contextual periods ("tonight by 10", "tomorrow morning"), absolute dates ("3rd January"), and vague disambiguation windows ("this weekend", "sometime this week", "later today").

## 4. Local AI & Transcription Layer (`app/intelligence/`, `app/transcription/`, `app/ingestion/`)
- Implement faster-whisper transcription with INT8, CPU, Silero VAD, error detection, and audio normalization (`app/transcription/whisper.py`).
- Implement Ollama client with structured JSON parsing, retry & JSON repair prompt, and graceful fallback when generation is malformed (`app/intelligence/llm.py`).

## 5. Persistent Scheduler & Reminder Lifecycle (`app/scheduler/`)
- Implement APScheduler with SQLite jobstore to ensure persistent reminder dispatch across application restarts.
- Implement reminder actions: firing notification, snooze (+30m with indefinite repetitions), 2-step completion confirmation (`Confirm` / `Cancel`), and 60-second Undo window.

## 6. Telegram Bot & Conversational UI (`app/bot/`)
- Implement aiogram 3 router with strict single-user authentication middleware (`AUTHORIZED_USER_ID`).
- Implement `/start` and `/timezone` flows with interactive timezone picker and custom offset support.
- Implement message handlers for Voice/Audio dumps and Text dumps.
- Implement response card formatting matching PRD Section 15 and callback query handlers for Reminder actions, Snooze, Done, Undo, and Vague-Time clarification.

## 7. Verification & Testing Suite (`tests/`)
- Unit tests: `test_temporal.py` for all relative/absolute/vague datetime expressions.
- Unit tests: `test_schema.py` for Pydantic validation and JSON repair.
- Integration tests: `test_scheduler.py` for APScheduler persistence, snooze, complete, undo.
- Integration tests: `test_handlers.py` for authorization gate, timezone routing, response formatting.

## 8. Setup Scripts & Deployment Artifacts
- Create `scripts/setup.sh` for one-command automated setup and dependency installation.
- Create `Dockerfile` and `docker-compose.yml` for containerized deployment with persistent volume.
- Create comprehensive `README.md` covering architecture, setup, demo walkthrough, and secrets guide.
