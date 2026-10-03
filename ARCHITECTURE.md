# ChronoDump Architecture Specification

## 1. System Topology

ChronoDump is designed as an autonomous, local-first personal assistant. It avoids third-party cloud APIs, maintaining complete data sovereignty and operating with zero per-request costs.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM UI                               │
│       • Voice note / text input                                        │
│       • Interactive response cards & inline action buttons             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Telegram Bot API (HTTPS / Polling)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        CHRONODUMP RUNTIME (BOT)                        │
│                                                                        │
│   ┌───────────────────────────────┐   ┌────────────────────────────┐   │
│   │ SingleUserAuthMiddleware      │   │ Ingestion Pipeline         │   │
│   │ • Enforces AUTHORIZED_USER_ID │──>│ • ffmpeg audio normalize   │   │
│   │ • Blocks unauthorized callers │   │ • Ephemeral audio cleanup  │   │
│   └───────────────────────────────┘   └─────────────┬──────────────┘   │
│                                                     │                  │
│                                                     ▼                  │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ faster-whisper (Local Speech-to-Text)                          │   │
│   │ • Model: base.en (INT8 Quantized, CPU-optimized)               │   │
│   │ • Silero VAD (Voice Activity Detection)                        │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Text Transcript                    │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Local Ollama Service (Open-Weight LLM)                         │   │
│   │ • Model: Qwen 2.5 3B (qwen2.5:3b)                              │   │
│   │ • Output: Strict Pydantic JSON Schema                          │   │
│   │ • Intent extraction (Notes, Action Items, Time Expressions)    │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Structured Entities                │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Python Deterministic Temporal Engine                           │   │
│   │ • Pure Python datetime + zoneinfo arithmetic                   │   │
│   │ • Zero LLM calculation hallucinations                          │   │
│   │ • Resolves relative offsets, contextual times, vague windows   │   │
│   └───────────────┬────────────────────────────────┬───────────────┘   │
│                   │                                │                   │
│                   ▼                                ▼                   │
│   ┌───────────────────────────────┐   ┌────────────────────────────┐   │
│   │ SQLAlchemy 2 / SQLite Storage │   │ APScheduler Engine         │   │
│   │ • User settings & timezone    │   │ • SQLite persistent store  │   │
│   │ • Historical dumps & notes    │   │ • Survives service restart │   │
│   │ • Task states (active/done)   │   │ • Snooze & Undo handling   │   │
│   └───────────────────────────────┘   └─────────────┬──────────────┘   │
│                                                     │                  │
│                                                     ▼                  │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ ChronoDump Design System (Telegram Presentation Layer)         │   │
│   │ • Visual response cards (Notes, Armed Timers, Needs Nudge)     │   │
│   │ • Urgent action alert pings                                    │   │
│   │ • 2-Step destructive confirmation & 60s undo protection        │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Design & Responsibility Boundaries

### A. Security & Ingestion Layer (`app/bot/middlewares.py`, `app/ingestion/`)
- **Single-User Gate**: The bot operates exclusively for the owner configured in `AUTHORIZED_USER_ID`. All other users receive an immediate rejection.
- **Ephemeral Audio**: Voice notes downloaded from Telegram are converted to 16kHz WAV via `ffmpeg` in a temporary path and immediately unlinked after transcription. No audio lingers on disk.

### B. Speech-to-Text (`app/transcription/whisper.py`)
- Employs `faster-whisper` (`base.en` with INT8 quantization).
- Silero VAD strips non-speech segments, improving CPU transcription performance and preventing transcription hallucinations during silent intervals.

### C. Local Intelligence (`app/intelligence/llm.py`, `prompts.py`, `schema.py`)
- Communicates with Ollama running locally (`qwen2.5:3b`).
- Prompt instructions enforce structured JSON output adhering to Pydantic v2 schemas (`ExtractedDump`).
- **Separation of Concerns**: The LLM is strictly used for linguistic parsing and entity classification. It is **never** relied on for calendar or timezone arithmetic.

### D. Deterministic Temporal Engine (`app/intelligence/temporal.py`)
- Handles temporal resolution with standard Python `datetime` and `zoneinfo`.
- Resolves:
  - **Relative offsets**: "in 5 minutes", "in 2 hours", "in 45m"
  - **Contextual times**: "tonight by 10", "tomorrow morning at 9", "this evening"
  - **Absolute dates**: "3rd January", "Oct 15 at 4pm"
  - **Vague timeframes**: "sometime this weekend", "later this week"
- For vague deadlines, the engine schedules a Friday 5:00 PM clarification check-in with 1-tap resolution options.

### E. Scheduler & Persistence (`app/scheduler/`, `app/storage/`)
- Uses `APScheduler` backed by `SQLAlchemyJobStore` on SQLite (`chronodump_scheduler.db`).
- Jobs survive application crashes, system reboots, and container restarts.
- Manages snooze loops (+30m, +1h), 2-step completion verification, and 60-second undo recovery.

---

## 3. Storage Architecture

```text
SQLite: data/chronodump.db
├── users (id, telegram_id, timezone, created_at)
├── dumps (id, user_id, raw_input, summary, input_type, created_at)
├── reminders (id, user_id, dump_id, task, target_time, display_time, status, snooze_count, created_at)
└── vague_clarifications (id, reminder_id, window, prompt_time, status)

SQLite: data/chronodump_scheduler.db
└── apscheduler_jobs (job_id, next_run_time, job_state)
```

---

## 4. Production Resilience
- **Healthcheck Probe (`scripts/healthcheck.py`)**: Tests environment, SQLite database read/writes, Ollama inference readiness, and Telegram API status.
- **Automated Backups (`scripts/backup.sh`)**: Creates point-in-time timestamped snapshots of database files with automated retention pruning.
- **Zero-Downtime Deployment (`scripts/deploy.sh`)**: Executes a 5-phase rollout (Preflight, Backup, Build/Deps, Test Suite, Service Restart & Verify).
- **Rollback (`scripts/rollback.sh`)**: Reverts to prior backup and restores previous service state if deployment healthchecks fail.
