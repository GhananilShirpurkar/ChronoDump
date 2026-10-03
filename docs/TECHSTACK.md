# ChronoDump — Tech Stack

## Overview

ChronoDump is a local-first autonomous AI agent that converts messy Telegram voice/text dumps into structured tasks, resolves temporal intent, and schedules persistent reminders.

## Architecture

```text
Telegram
   ↓
Python + aiogram 3
   ↓
faster-whisper
   ↓
Ollama + Qwen3 4B
   ↓
Pydantic structured output
   ↓
Python temporal engine
   ↓
APScheduler
   ↓
SQLite
   ↓
Telegram
```

## Core Stack

| Layer | Technology | Purpose |
|---|---|---|
| Interface | Telegram Bot | User interaction |
| Backend | Python 3.12+ | Main application |
| Telegram Framework | aiogram 3 | Async bot implementation |
| Speech-to-Text | faster-whisper | Local voice transcription |
| LLM Runtime | Ollama | Local model inference |
| LLM | Qwen3 4B | Intent and temporal-language extraction |
| Data Validation | Pydantic v2 | Strict typed structured output |
| Temporal Logic | Python `datetime` + `zoneinfo` | Deterministic time resolution |
| Scheduler | APScheduler 3.x | Persistent reminder execution |
| Database | SQLite | User, task, and reminder persistence |
| Database Layer | SQLAlchemy 2 | Database abstraction |
| Package Management | uv | Python environment and dependency management |
| Deployment | Docker Compose | Reproducible deployment |

## Responsibility Boundaries

### LLM — Interpretation

The LLM should interpret natural language and extract:

- Tasks
- Notes
- Temporal expressions
- User intent
- Ambiguity

It should **not** be trusted with final timestamp arithmetic.

### Python Temporal Engine — Deterministic Reasoning

Python is responsible for:

- Resolving relative dates/times
- Applying the user's timezone
- Validating timestamps
- Detecting impossible/invalid dates
- Handling vague-time rules
- Producing the final scheduler timestamp

### APScheduler — Execution

APScheduler is responsible for:

- Registering reminders
- Persisting jobs
- Triggering reminders
- Rescheduling snoozed tasks
- Recovering jobs after application restart

### SQLite — Persistence

SQLite stores:

- User configuration
- Timezone
- Tasks
- Reminder state
- Scheduler-related data
- Completion state

## Processing Flow

```text
Voice Message
    ↓
Telegram / aiogram
    ↓
faster-whisper
    ↓
Transcript
    ↓
Qwen3 4B via Ollama
    ↓
Pydantic validation
    ↓
Temporal Engine
    ↓
Final validated task/reminder
    ↓
APScheduler + SQLite
    ↓
Telegram Reminder
```

For text input, the Whisper step is skipped:

```text
Text
  ↓
Qwen3 4B
  ↓
Pydantic
  ↓
Temporal Engine
  ↓
Scheduler
```

## Why This Stack

### Python

Best fit for the local AI/audio ecosystem and keeps the entire backend in one language.

### aiogram 3

Provides an async Telegram bot architecture suitable for voice processing and scheduled interactions.

### faster-whisper

Runs speech recognition locally and is optimized for CPU inference, which fits the project's low-cost deployment target.

### Ollama

Provides a simple local inference layer and keeps the model replaceable.

### Qwen3 4B

Chosen as the initial open-weight model because ChronoDump needs reliable instruction following and structured extraction while remaining practical for local inference.

### Pydantic

Creates a strict boundary between probabilistic LLM output and deterministic application logic.

### Python Temporal Engine

Time interpretation is business-critical. Keeping final timestamp resolution in deterministic Python code reduces hallucinated or incorrect scheduling.

### APScheduler

Provides the execution layer needed for ChronoDump's autonomous behavior.

### SQLite

ChronoDump is single-user in v1, so a server database would add unnecessary operational complexity.

### Docker Compose

Keeps the application reproducible across the development machine and VPS.

## What We Are NOT Using

### LangChain

Not required. The pipeline is simple enough that direct Python components are easier to reason about and debug.

### LangGraph

Not required for v1. ChronoDump has a deterministic processing pipeline rather than a complex multi-agent graph.

### Cloud LLM APIs

Not required. Local inference is a core product requirement.

### PostgreSQL

Not required for the single-user MVP.

### Vector Database

Not required for v1 because semantic history/search is explicitly out of scope.

### React / Web UI

Not required. Telegram is the primary interface.

## Initial Dependencies

```text
aiogram
faster-whisper
ollama
pydantic
apscheduler
sqlalchemy
python-dotenv
```

Development/testing dependencies can be added separately.

## Deployment

Preferred:

```text
Docker Compose
├── ChronoDump Bot
├── Ollama
└── Persistent SQLite/data volume
```

The deployment should be capable of running on:

- Local Linux machine
- 8 GB RAM development laptop
- Free-tier ARM VPS where compatible

## Design Principle

The central architectural rule is:

> **LLM interprets. Python validates and reasons about time. APScheduler executes. SQLite remembers.**

This separation keeps the AI flexible while making the critical reminder system deterministic and reliable.
