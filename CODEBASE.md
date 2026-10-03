# ChronoDump Codebase Map & Developer Guide

## Overview
ChronoDump is a local-first autonomous AI agent that ingests messy voice and text dumps via Telegram, transcribes speech using `faster-whisper`, extracts structured tasks and temporal intents using Ollama (`qwen2.5:3b`), resolves dates deterministically with Python, and arms persistent reminders via APScheduler in SQLite.

---

## Directory Layout & Module Responsibilities

```text
ChronoDump/
├── app/
│   ├── bot/
│   │   ├── design.py          # ChronoDump Design System (dividers, cards, badges)
│   │   ├── handlers.py        # Message, voice, slash command & callback handlers
│   │   ├── keyboards.py       # Inline keyboards (timezone, snooze, done, undo, clarify)
│   │   ├── messages.py        # Response card templates and UI views
│   │   └── middlewares.py     # Single-user security authorization gate
│   ├── ingestion/
│   │   ├── audio.py           # Audio download from Telegram, ffmpeg normalization, and immediate file wiping
│   │   └── text.py            # Text sanitization and preprocessing
│   ├── intelligence/
│   │   ├── llm.py             # Ollama async client, retry logic, and fallback
│   │   ├── prompts.py         # System, multi-task extraction, and repair prompts
│   │   ├── schema.py          # Pydantic v2 ExtractedDump schema
│   │   └── temporal.py        # Deterministic Python temporal engine
│   ├── scheduler/
│   │   ├── jobs.py            # APScheduler service with SQLite jobstore
│   │   └── reminders.py       # Async alert triggers and reminder notifications
│   ├── storage/
│   │   ├── database.py        # SQLAlchemy session engine and CRUD helpers
│   │   └── models.py          # Models (User, Dump, Reminder, VagueClarification)
│   ├── config.py              # Environment configuration loader
│   └── main.py                # Bot startup and lifecycle entrypoint
├── assets/
│   └── logo.png               # Brand neon robot logo
├── docs/
│   ├── ARCHITECTURE.md        # Deep architectural design and data flow specification
│   ├── DEPLOYMENT.md          # 5-phase production operations and deployment guide
│   ├── PRD.md                 # Full Product Requirements Document
│   └── TECHSTACK.md           # Technology stack and responsibility boundaries
├── scripts/
│   ├── backup.sh              # SQLite snapshot and retention management
│   ├── deploy.sh              # 5-phase zero-downtime deployment runner
│   ├── healthcheck.py         # Diagnostics probe (env, db, ollama, telegram)
│   ├── rollback.sh            # Instant 1-step rollback utility
│   └── setup.sh               # Automated one-command developer setup
├── tests/
│   ├── test_commands.py       # Slash commands (/today, /queue, /focus, /notes, /stats)
│   ├── test_handlers.py       # Response cards, keyboards, and template formats
│   ├── test_scheduler.py      # SQLite persistence, restart recovery, snooze, undo
│   ├── test_schema.py         # Pydantic schema validation & JSON parser tests
│   └── test_temporal.py       # Relative, absolute, and vague time unit tests
├── .dockerignore              # Docker build context exclusions
├── .editorconfig              # Editor indentation and formatting standards
├── .env.example               # Secrets template
├── .github/workflows/ci.yml   # Continuous Integration pipeline
├── chronodump.service         # Systemd service unit definition
├── docker-compose.yml         # Containerized bot with host Ollama
├── docker-compose.full.yml    # Full containerized stack with Ollama container
├── Dockerfile                 # Container image specification
├── Makefile                   # Production task runner
├── pyproject.toml             # Project metadata and pytest configuration
├── requirements.txt           # Python runtime dependencies
└── README.md                  # Main project documentation
```

---

## Core Dependencies & Technology Boundaries

1. **`aiogram 3.x`**: Async Telegram bot framework.
   - Entry point: `app/main.py`.
   - Security gate: `app/bot/middlewares.py` enforces `user_id == AUTHORIZED_USER_ID`.
2. **`faster-whisper` + Silero VAD**: Local STT running on CPU with INT8 quantization.
   - Normalizes audio to 16kHz WAV via `ffmpeg`.
   - Deletes temporary audio immediately after transcription (`app/ingestion/audio.py`).
3. **`ollama` (`qwen2.5:3b`)**: Open-weight LLM for entity extraction.
   - Interprets tasks, clean notes, and relative time expressions into JSON (`app/intelligence/llm.py`).
   - Validated through Pydantic v2 schemas (`app/intelligence/schema.py`).
4. **Python Temporal Engine (`app/intelligence/temporal.py`)**:
   - Deterministic arithmetic using Python `datetime` and `zoneinfo`.
   - Converts relative ("in 20m"), contextual ("tonight by 10"), and absolute ("3rd Jan") timestamps into timezone-aware datetimes.
5. **`APScheduler 3.x` + SQLite**:
   - Persists armed triggers into SQLite `chronodump_scheduler.db`.
   - Re-arms jobs automatically across restarts.

---

## Testing & Verification
All tests are located in `tests/` and run with `pytest`:
```bash
make test
# or
.venv/bin/pytest -v
```
Currently 27/27 unit and integration tests passing.
