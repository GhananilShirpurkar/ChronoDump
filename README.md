# ChronoDump ⚡

> **Turn raw audio chaos into structured plans and auto-armed reminders.**

ChronoDump is a local-first autonomous AI agent that lets you dump messy thoughts, tasks, and deadlines through Telegram voice notes or text. It transcribes audio locally, extracts actionable tasks, resolves complex time references deterministically, and automatically arms persistent reminders without requiring manual task creation.

Built with **open-source AI** at its core for the Hacktoberfest "Build for a Friend" challenge.

---

## 🎯 Core Principles

```text
        CHRONODUMP
      AUTONOMOUS
          ├── Understands intent & extracts tasks
          ├── Resolves relative & contextual time
          └── Executes persistent reminders later

        PRIVATE
          ├── Local Whisper speech-to-text (CPU + VAD)
          ├── Local Ollama open-weight LLM inference
          └── Audio cleaned up immediately after transcription

          FREE
          ├── 100% open-weight stack
          ├── Zero paid cloud AI APIs
          └── Deployable on local laptops or free-tier ARM VPS
```

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────────┐
                    │       Telegram User      │
                    │                          │
                    │ Voice Note / Text        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       aiogram 3.x        │
                    │  Single-User Auth Gate   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      Ingestion Layer     │
                    │                          │
                    │ Audio → ffmpeg 16kHz WAV │
                    │ Text → clean/sanitize    │
                    └────────────┬─────────────┘
                                 │
                     Audio       │       Text
                       │         │         │
                       ▼         │         │
             ┌────────────────┐  │         │
             │ faster-whisper │  │         │
             │    base.en     │  │         │
             │ INT8 + VAD     │  │         │
             └───────┬────────┘  │         │
                     │           │         │
                     └─────┬─────┴─────────┘
                           ▼
                ┌────────────────────────┐
                │   Raw Transcript/Text  │
                │                        │
                │ + CURRENT_DATETIME     │
                │ + User Timezone        │
                └───────────┬────────────┘
                            ▼
                ┌────────────────────────┐
                │   Ollama / LLM Layer   │
                │                        │
                │ Qwen2.5 / Qwen3 / 3B   │
                │ Pydantic Validation    │
                └───────────┬────────────┘
                            │
                     Structured JSON
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
   ┌──────────────────┐          ┌────────────────────┐
   │ Summary Engine   │          │ Temporal Engine    │
   │                  │          │ (Python Engine)    │
   │ Clean Notes      │          │                    │
   │ Action Items     │          │ Exact deadlines    │
   └────────┬─────────┘          │ Relative times     │
            │                    │ Vague boundaries   │
            │                    └─────────┬──────────┘
            │                              │
            ▼                              ▼
   ┌──────────────────┐          ┌────────────────────┐
   │ Telegram Card    │          │ APScheduler        │
   │ Response         │          │ + SQLite Jobstore  │
   └──────────────────┘          └─────────┬──────────┘
                                          │
                           ┌──────────────┼──────────────┐
                           ▼              ▼              ▼
                     Hard Reminder   Clarification   Snooze
                           │          Ping             Loop
                           │              │              │
                           └──────────────┴──────────────┘
                                          │
                                          ▼
                               Telegram Interactive UI
                           [ Done ] [ +30 min ] [ Undo ]
```

---

## ⚡ Tech Stack

| Layer | Technology | Description |
|---|---|---|
| **Bot Framework** | Python 3.12+ / aiogram 3 | Async Telegram bot framework |
| **Speech-to-Text** | faster-whisper | CPU-optimized local transcription with Silero VAD |
| **Local LLM** | Ollama (`qwen2.5:3b` / `qwen3:4b`) | Open-weight instruction model for structured parsing |
| **Data Validation** | Pydantic v2 | Strict JSON schema parsing and error repair |
| **Temporal Engine** | Python `datetime` + `zoneinfo` | Deterministic relative/contextual time resolution |
| **Scheduler** | APScheduler 3.x | Persistent scheduler using SQLite jobstore |
| **Database** | SQLite + SQLAlchemy 2 | User settings, brain dumps, and reminder states |
| **Deployment** | Docker Compose / Shell Script | Single-command reproducible setup |

---

## 📁 Repository Structure

```text
chronodump/
├── app/
│   ├── bot/
│   │   ├── handlers.py        # Message & callback handlers (voice, text, actions)
│   │   ├── keyboards.py       # Inline keyboards (timezone, snooze, done, undo, clarify)
│   │   ├── messages.py        # Response card templates matching PRD
│   │   └── middlewares.py     # Single-user security authorization gate
│   ├── ingestion/
│   │   ├── audio.py           # Audio download, ffmpeg normalization, and cleanup
│   │   └── text.py            # Text sanitization
│   ├── intelligence/
│   │   ├── llm.py             # Ollama async client, retry prompt, degraded fallback
│   │   ├── prompts.py         # System, extraction, and repair prompts
│   │   ├── schema.py          # Pydantic v2 ExtractedDump schema
│   │   └── temporal.py        # Deterministic Python temporal engine
│   ├── scheduler/
│   │   ├── jobs.py            # APScheduler service with SQLite jobstore
│   │   └── reminders.py       # Importable execution callbacks for reminders
│   ├── storage/
│   │   ├── database.py        # SQLAlchemy session management and CRUD helpers
│   │   └── models.py          # Models (User, Dump, Reminder, VagueClarification)
│   ├── config.py              # Environment configuration loader
│   └── main.py                # Bot startup and entrypoint
├── scripts/
│   └── setup.sh               # Automated one-command setup script
├── tests/
│   ├── test_handlers.py       # Response card, keyboard, and template tests
│   ├── test_scheduler.py      # Persistence, restart recovery, snooze, complete, undo
│   ├── test_schema.py         # Pydantic schema validation & JSON parser tests
│   └── test_temporal.py       # Relative, absolute, and vague time unit tests
├── .env.example               # Secrets and settings template
├── .env                       # Local secrets configuration
├── Dockerfile                 # Container image specification
├── docker-compose.yml         # Containerized bot + Ollama orchestration
├── requirements.txt           # Python package dependencies
├── pyproject.toml             # Project metadata and configuration
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Linux / macOS / WSL2**
- **Python 3.12+** (or [uv](https://docs.astral.sh/uv/))
- **ffmpeg** (for audio normalization: `sudo apt install ffmpeg`)
- **Ollama** ([ollama.com](https://ollama.com)):
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ollama pull qwen2.5:3b
  ```

### 2. Automated Setup
Run the automated setup script:
```bash
bash scripts/setup.sh
```

### 3. Configure Secrets (`.env`)
Edit `.env` and fill in your secrets:
```env
# Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ

# Your personal Telegram User ID (from @userinfobot or @raw_data_bot)
AUTHORIZED_USER_ID=987654321

# Local Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b

# Whisper settings
WHISPER_MODEL=base.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# Database settings
DATABASE_URL=sqlite:///data/chronodump.db
SCHEDULER_DATABASE_URL=sqlite:///data/chronodump_scheduler.db

# Storage & Default Timezone
DATA_DIR=./data
DEFAULT_TIMEZONE=UTC
LOG_LEVEL=INFO
```

### 4. Run the Bot
```bash
source .venv/bin/activate
python -m app.main
```

---

## 🐳 Docker Deployment

To run ChronoDump with Docker Compose (including Ollama):
```bash
# Ensure .env is configured with your bot token and authorized user ID
docker compose up -d --build

# In the ollama container, pull the model if running for the first time:
docker compose exec ollama ollama pull qwen2.5:3b
```

---

## 🧪 Running Tests

The test suite covers unit and integration tests across all components:
```bash
.venv/bin/pytest -v
```

All 22 test cases pass:
- `test_temporal.py`: Relative minutes, hours, "tonight by 10", "tomorrow morning", "next Friday", "3rd January", vague disambiguation.
- `test_schema.py`: Pydantic model validation, markdown code block stripping, JSON repair.
- `test_scheduler.py`: SQLite persistence across scheduler restarts, reminder snooze, 2-step completion confirmation, and 60-second undo.
- `test_handlers.py`: Telegram response card layout, keyboards, and template formats.

---

## 🎙️ Demo Walkthrough

Try sending this voice note or text message to the bot:

> *"Yo, finish reading chapter 4 tonight by 10. Final report's due 3rd Jan. Remind me to drink water in two minutes. And I gotta pick up laundry sometime this weekend."*

### 1. Telegram Response Card
ChronoDump immediately analyzes the dump and responds with:

```text
⚡ Sorted. Here's your dump:

📋 CLEAN NOTES
• (any contextual insights extracted)

✅ ACTION ITEMS
◻️ (none here — everything had a time!)

⏰ ARMED REMINDERS
🔔 Tonight @ 10:00 PM — Read Chapter 4
🔔 Jan 3 @ 11:59 PM — Submit Final Project Report
🔔 In 2 minutes — Drink water 🚰

🔍 NEEDS A NUDGE
◻️ Pick up laundry
   I'll ask you Friday: Saturday or Sunday?

I'll buzz you right here when it's time. 🫡
```

### 2. Autonomous Action
In 2 minutes, ChronoDump automatically pings you without any manual reminder creation:
```text
⏰ Heads up:

Drink water 🚰

You wanted this done right now.

[ ✅ Done ]  [ ⏳ +30 min ]
```

### 3. Interactive Actions
- **Snooze**: Click `⏳ +30 min` to push the task back 30 minutes (unlimited snoozes supported).
- **Completion Confirmation**: Click `✅ Done` → prompts with `[ Confirm ✅ ]` and `[ Cancel ]`.
- **60-Second Undo**: Upon confirmation, gives an `[ ↩️ Undo ]` button valid for 60 seconds.
- **Vague-Time Disambiguation**: When Friday 5:00 PM arrives, ChronoDump asks when to schedule *"Pick up laundry"* with `[ Saturday 9:00 AM ]`, `[ Sunday 9:00 AM ]`, or `[ No rush ]`.

---

## 🔒 Security & Privacy

1. **Single-User Isolation**: Only the configured `AUTHORIZED_USER_ID` can interact with the bot. Unauthorized users receive an immediate rejection.
2. **Local Audio Cleanup**: All audio files downloaded from Telegram are immediately wiped after transcription.
3. **Local-First Processing**: Voice notes, transcripts, notes, and task data stay inside your local machine or private server. No third-party AI APIs are called.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
