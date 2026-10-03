# Product Requirement Document (PRD)
## ChronoDump — Final v1

**Version:** 1.0  
**Status:** Build-ready  
**Hacktoberfest Challenge:** Build for a Friend  
**Product Type:** Local-first autonomous AI agent  
**Primary Interface:** Telegram Bot

---

# 1. Product Overview

## 1.1 Product Name

**ChronoDump**

## 1.2 Tagline

> **Turn raw audio chaos into structured plans and auto-armed reminders.**

## 1.3 One-Line Description

ChronoDump is a local AI agent that lets a user dump messy thoughts, tasks, and deadlines through Telegram voice notes or text, automatically organizes them, understands the time references, and schedules reminders without requiring the user to manually create tasks.

## 1.4 Core Pitch

> **ChronoDump doesn't just understand what you said. It remembers when you need to act on it — and acts without being asked again.**

The primary judging angle is **autonomous action**.

The user sends one rambling voice note containing multiple thoughts and deadlines.

ChronoDump:

1. Transcribes it locally.
2. Extracts useful information.
3. Separates notes from actionable tasks.
4. Resolves temporal expressions against the real current time.
5. Schedules reminders.
6. Asks for clarification when the time is genuinely ambiguous.
7. Sends the reminder later without requiring another prompt.
8. Allows the user to complete or snooze the task.

The existing PRD defines this autonomous, time-aware behavior as the central product idea.

---

# 2. Hacktoberfest Challenge Fit

## Challenge

**Build for a Friend**

Build something with open-source AI at its core that solves a real problem for a specific friend or person you care about.

## ChronoDump's interpretation

ChronoDump is built around a real behavioral pattern:

> A friend has thoughts, tasks, deadlines, and small obligations throughout the day, but doesn't want to stop what they're doing to open a task manager, select dates, enter times, categorize tasks, and maintain another productivity system.

Instead, they naturally dump everything into a voice note.

The problem isn't that the person is incapable of organizing their life.

The problem is **friction**.

ChronoDump removes that friction.

### The intended story

> “I built ChronoDump for a friend who naturally uses voice notes as a scratchpad. The problem was that important tasks and deadlines were buried inside those recordings. So I built an AI agent that listens to the dump, extracts the tasks, understands when they need to happen, and actually reminds them later.”

The final submission should replace the generic persona with the **actual friend who uses the system** and include their reaction after using it.

---

# 3. Why Open Innovation Matters

Open-source AI is not decorative in ChronoDump.

The system is intentionally designed around local, replaceable AI components.

## 3.1 Privacy

Voice notes may contain:

- Personal thoughts
- Academic information
- Project information
- Deadlines
- Personal plans
- Conversations
- Sensitive context

Raw audio and extracted thoughts should not need to leave the user's controlled environment.

ChronoDump processes these locally.

> **Your brain dump stays in your box.**

---

## 3.2 Model Freedom

The LLM is not hardcoded into a proprietary API.

The architecture uses Ollama as the local inference layer, allowing the underlying open-weight model to be swapped.

The initial model is:

```text
llama3.2:3b-instruct
Q4_K_M
CPU inference
```

The system should treat the model as an interchangeable component rather than the product itself.

---

## 3.3 Zero API Cost

ChronoDump does not require:

- OpenAI API
- Anthropic API
- Gemini API
- Cloud transcription API
- Paid vector database
- Paid scheduler
- Proprietary task-management API

The complete stack can run locally.

Production can additionally run on a free-tier ARM VPS.

---

## 3.4 Reproducibility

The intended setup is:

```text
./setup.sh
```

which installs/configures:

- Python environment
- Bot dependencies
- Whisper
- Ollama
- Model weights
- SQLite
- Scheduler
- Configuration
- Bot startup

The goal is to make the project reproducible on another machine rather than tied to the developer's environment.

---

# 4. Problem Statement

## 4.1 Existing Behavior

People often capture thoughts through voice notes because speaking is faster than typing.

A single voice note can contain:

> “I need to finish chapter four tonight, the final report is due January 3rd, remind me to drink water in two minutes, and I need to pick up my laundry sometime this weekend.”

The problem is that the voice note itself doesn't become an actionable system.

The user must manually:

1. Listen to the recording again.
2. Identify tasks.
3. Identify deadlines.
4. Determine exact dates.
5. Create reminders.
6. Remember to check them later.

This creates friction.

---

# 5. Product Solution

ChronoDump turns:

```text
Raw thought
    ↓
Voice/Text dump
    ↓
Local transcription
    ↓
Local AI understanding
    ↓
Structured information
    ↓
Temporal reasoning
    ↓
Persistent scheduled action
    ↓
Reminder
```

The user doesn't need to manually construct the task.

---

# 6. Target User

## Primary Persona

A student/developer who:

- Has multiple concurrent responsibilities.
- Frequently thinks of tasks while doing something else.
- Uses Telegram regularly.
- Naturally sends voice notes.
- Doesn't enjoy maintaining elaborate productivity systems.
- Has deadlines mixed together with ordinary thoughts.
- Wants minimal interaction.

## Core Behavioral Insight

The product should adapt to the user's existing behavior rather than forcing the user to adopt another workflow.

**Input should feel like talking to yourself.**

---

# 7. Product Principles

ChronoDump follows six principles.

### 1. Zero friction

The user should be able to dump thoughts without formatting them.

### 2. Local by default

Private thoughts and audio should remain local.

### 3. Don't hallucinate time

If the temporal intent is unclear, ask.

### 4. Autonomous action

Once the user gives sufficient information, the system acts without another prompt.

### 5. Graceful failure

A model failure should never destroy the user's original information.

### 6. Minimal interface

Telegram is the interface.

No dashboard is required for v1.

---

# 8. Product Architecture

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
                    │      Telegram Bot        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      Ingestion Layer     │
                    │                          │
                    │ Audio → OGG/WAV          │
                    │ Text → direct processing │
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
                │ llama3.2:3b-instruct   │
                │ Q4_K_M                 │
                └───────────┬────────────┘
                            │
                     Structured JSON
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
   ┌──────────────────┐          ┌────────────────────┐
   │ Summary Engine   │          │ Temporal Task      │
   │                  │          │ Engine             │
   │ Clean Notes      │          │                    │
   │ Action Items     │          │ Exact deadlines    │
   └────────┬─────────┘          │ Relative times     │
            │                    │ Vague times        │
            │                    └─────────┬──────────┘
            │                              │
            ▼                              ▼
   ┌──────────────────┐          ┌────────────────────┐
   │ Telegram Card    │          │ APScheduler        │
   │                  │          │ + SQLite Jobstore  │
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
                               Telegram Inline Buttons
```

---

# 9. Deployment Architecture

## Development

Developer machine:

```text
Intel i3
8 GB RAM
Integrated GPU
Ubuntu/Linux
```

The initial target is CPU inference.

## Production

Preferred deployment:

```text
Oracle Cloud Always Free ARM VPS
4 ARM cores
24 GB RAM
```

The production node hosts:

```text
Telegram Bot
    +
faster-whisper
    +
Ollama
    +
LLM
    +
APScheduler
    +
SQLite
```

This allows the project to maintain its intended **zero operating cost** claim.

## Fallback

If the free VPS cannot be obtained:

```text
Local laptop
+
phone hotspot
```

can be used for demonstration.

The $5 VPS fallback should **not** be presented as zero-cost infrastructure.

---

# 10. Functional Requirements

# 10.1 Telegram Authentication

ChronoDump is a **single-user system in v1**.

At startup:

```text
/start
```

the bot checks whether the Telegram user is authorized.

Only the configured:

```text
USER_ID
```

can use the system.

All other chats are ignored or receive no meaningful interaction.

---

# 10.2 Timezone Setup

Telegram does not provide the user's timezone automatically.

Therefore `/start` asks for timezone once.

Example:

```text
🌍 What timezone are you in?

[ UTC+5:30 — India ]
[ UTC+0 ]
[ UTC-5 — ET ]
[ UTC+1 ]
[ UTC+8 ]
[ Other / Type offset ]
```

The selected timezone is persisted in SQLite.

Users can change it with:

```text
/timezone
```

---

# 10.3 Voice Input

Supported:

- Telegram voice messages
- Telegram audio files
- Forwarded voice messages

Processing pipeline:

```text
Telegram OGG
    ↓
Audio normalization
    ↓
faster-whisper
    ↓
Transcript
```

Model:

```text
faster-whisper base.en
INT8
CPU
Silero VAD
```

Fallback:

```text
tiny.en
```

if latency becomes unacceptable.

---

# 10.4 Text Input

Plain text messages are also accepted.

Text bypasses Whisper:

```text
Text
 ↓
LLM
 ↓
Structured output
```

This provides a deterministic fallback and demonstrates that the intelligence is not dependent on speech recognition.

---

# 10.5 Language Support

v1 supports:

> **English only**

If non-English audio is detected or cannot reasonably be processed:

> “I only speak English for now 🤙 — send me an English note.”

---

# 11. AI Processing

## 11.1 Current Date Injection

The system injects:

```text
CURRENT_DATETIME
```

into the LLM context at inference time.

Example:

```text
CURRENT_DATETIME:
2026-10-02T18:30:00+05:30
```

This allows the model to reason about relative temporal expressions.

---

# 11.2 Temporal Resolution

The system should resolve expressions such as:

```text
tonight by 10
```

→ same day at 22:00

```text
in an hour
```

→ current time + 60 minutes

```text
tomorrow morning
```

→ tomorrow's appropriate morning boundary

```text
3rd January
```

→ next applicable January 3rd

The final timestamp must contain the timezone offset.

---

# 11.3 Important Rule: Never Guess Ambiguous Time

If a user says:

> “Pick up laundry sometime this weekend.”

ChronoDump must **not** silently select Saturday.

Instead:

```text
Needs clarification

Pick up laundry

When?

[ Saturday 9 AM ]
[ Sunday 9 AM ]
[ No rush ]
```

This is one of the core intelligence behaviors of the product.

---

# 12. Vague-Time Disambiguation

## “This weekend”

At the earliest reasonable boundary:

```text
Friday 5:00 PM
```

send:

> “You said this weekend. When should I remind you?”

```text
[ Saturday ]
[ Sunday ]
```

Selected date:

```text
09:00 AM
```

---

## “Sometime this week”

The bot asks at the appropriate boundary:

```text
[ Mon ]
[ Tue ]
[ Wed ]
[ Thu ]
[ Fri ]
[ No rush ]
```

Selecting **No rush** moves the task into Clean Notes rather than scheduling it.

---

## “Later today”

After an appropriate delay:

```text
[ Arm it ]
[ Skip ]
```

The system should never silently convert vague language into a false precision.

---

# 13. Structured LLM Output

Ollama structured-output mode should enforce a JSON schema.

The model output must conform to:

```json
{
  "summary": "One-line digest",
  "clean_notes": [
    "Context point"
  ],
  "action_items": [
    "Task with no time constraint"
  ],
  "scheduled_reminders": [
    {
      "task": "Submit project report",
      "target_timestamp": "2027-01-03T23:59:00+05:30",
      "display_time": "Jan 3 at 11:59 PM",
      "confidence": "exact"
    }
  ],
  "vague_reminders": [
    {
      "task": "Pick up laundry",
      "window": "this_weekend",
      "clarify_at": "2026-10-02T17:00:00+05:30",
      "options": [
        "Saturday 9:00 AM",
        "Sunday 9:00 AM"
      ]
    }
  ]
}
```

### Constraints

`target_timestamp`:

- Must be ISO-8601.
- Must contain a timezone offset.

`confidence`:

```text
exact
inferred
```

---

# 14. Dual-Mode Idea Optimizer

ChronoDump transforms the raw dump into two primary buckets.

## 14.1 Clean Notes

Contains:

- Context
- Insights
- Information
- Non-actionable thoughts

Example:

```text
📋 CLEAN NOTES

• Final report is for the database systems project.
• Chapter 4 contains the material needed for tomorrow's discussion.
```

---

## 14.2 Action Items

Contains tasks that have no fixed time.

Example:

```text
✅ ACTION ITEMS

◻️ Buy printer paper
◻️ Review GitHub PR
◻️ Ask professor about project topic
```

Tasks with valid deadlines are instead placed into Scheduled Reminders.

---

# 15. Telegram Response Card

Example user input:

> “Yo, finish reading chapter 4 tonight by 10. Final report's due 3rd Jan. Remind me to drink water in two minutes. And I gotta pick up laundry sometime this weekend.”

ChronoDump responds:

```text
⚡ Sorted. Here's your dump:

📋 CLEAN NOTES
• (anything contextual)

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

---

# 16. Autonomous Scheduler

The scheduler is one of the core components of ChronoDump.

Technology:

```text
APScheduler
+
SQLite Jobstore
```

The scheduler must persist jobs across bot restarts.

Example:

```text
User creates reminder
       ↓
SQLite stores job
       ↓
Bot crashes
       ↓
Bot restarts
       ↓
Scheduler reloads job
       ↓
Reminder still fires
```

This persistence is essential.

A reminder system that only exists in RAM is not acceptable for the final implementation.

---

# 17. Reminder System

At the target timestamp:

```text
⏰ Heads up:

Read Chapter 4

You wanted this done right now.
```

Buttons:

```text
[ ✅ Done ]
[ ⏳ +30 min ]
```

---

# 18. Completion Flow

Clicking:

```text
✅ Done
```

does not immediately delete the task.

First:

```text
Mark this task as complete?

[ Confirm ✅ ]
[ Cancel ]
```

After confirmation:

```text
✅ Done.

Read Chapter 4 marked complete.
```

The completion message contains:

```text
[ ↩️ Undo ]
```

The Undo button remains valid for:

```text
60 seconds
```

After that, it expires.

---

# 19. Snooze System

Clicking:

```text
⏳ +30 min
```

rearms the task for:

```text
current reminder time + 30 minutes
```

There is intentionally:

> **No maximum snooze count.**

The task can be snoozed indefinitely.

Every snooze creates another persistent scheduler event.

---

# 20. Failure Handling

ChronoDump must degrade gracefully.

## Failure 1 — Invalid JSON

Attempt:

```text
LLM → invalid JSON
```

Then automatically retry once with a repair prompt.

---

## Failure 2 — JSON Still Invalid

Return:

- Cleaned transcript
- Notes
- Detected deadlines as plain text

Then show:

```text
[ 🔔 Arm these ]
[ ✏️ Ignore ]
```

The user's information must never disappear because structured generation failed.

---

## Failure 3 — Poor Whisper Transcription

If Whisper confidence/output quality is too poor:

> “I couldn't make that out — mind re-recording? 🎙️”

Do not attempt to confidently schedule potentially incorrect tasks.

---

## Failure 4 — No Tasks

If the message contains no actionable deadline:

```text
⚡ Sorted.

📋 CLEAN NOTES
...

No deadlines heard.
```

The system should still return value instead of treating the message as a failure.

---

# 21. Security and Privacy

## Single-user isolation

Only the configured Telegram `USER_ID` can invoke the bot.

## Local processing

The following should remain inside the deployment environment:

- Raw audio
- Transcripts
- LLM prompts
- LLM outputs
- Reminder data
- User timezone
- Scheduled tasks

No external AI API is required.

## Secrets

Telegram bot token and other secrets must be stored in environment variables.

Example:

```env
TELEGRAM_BOT_TOKEN=
AUTHORIZED_USER_ID=
```

Never commit secrets to Git.

---

# 22. Non-Goals — v1

The following are explicitly out of scope:

- Multi-user support
- Group chats
- Recurring reminders
- Web dashboard
- Mobile application
- Calendar synchronization
- Google Calendar integration
- Task history search
- Editing old dumps
- Full conversation memory
- Non-English language support
- Cloud AI APIs
- Complex task management
- User accounts/authentication beyond Telegram authorization

These features may be considered for future versions but should not distract from the weekend MVP.

---

# 23. Future Possibilities

Potential v2 features:

### Memory

> “What did I dump about my project this week?”

### Recurring tasks

> “Remind me every Monday at 9.”

### Calendar integration

> “I have a meeting tomorrow at 4.”

### Multilingual support

Including Hindi/Hinglish.

### Semantic history

Search previous dumps using embeddings.

### Multi-user support

Allow family/friend groups.

### Adaptive reminders

Learn when the user usually completes tasks.

These are explicitly **not required for v1**.

---

# 24. Demo Script

## Total duration

Approximately **5 minutes**

---

## 0:00 — Problem

Show:

```text
Voice notes go to die.
```

Explain:

> “People naturally dump thoughts into voice notes, but those notes don't turn into actions.”

Keep this section under 20 seconds.

---

## 0:20 — The Dump

Send the scripted voice note:

> “Yo, finish reading chapter 4 tonight by 10. Final report's due 3rd Jan. Remind me to drink water in two minutes. And I gotta pick up laundry sometime this weekend.”

The recording should intentionally contain:

- Filler words
- Multiple tasks
- Multiple temporal expressions
- Exact deadlines
- Relative deadlines
- Vague deadlines

---

## 1:10 — Processing

While ChronoDump processes the message, explain:

```text
Whisper
   ↓
Local transcript
   ↓
3B open-weight model
   ↓
Structured JSON
   ↓
Temporal engine
   ↓
Persistent scheduler
```

Key line:

> “Nothing here requires a cloud AI API.”

---

# 25. The Demo Moment

## 2:30 — Autonomous Reminder

Continue talking.

The system fires:

```text
⏰ Heads up:

Drink water 🚰

You wanted this done right now.
```

Show:

```text
[ ✅ Done ]
[ ⏳ +30 min ]
```

Click:

```text
⏳ +30 min
```

Then demonstrate:

```text
✅ Done
```

→

```text
[ Confirm ✅ ]
[ Cancel ]
```

Confirm.

Then show:

```text
[ ↩️ Undo ]
```

This is the key demonstration of autonomous behavior.

---

# 26. Vague Deadline Demonstration

Show a prepared screenshot/video of:

```text
🔍 NEEDS A NUDGE

Pick up laundry

When?

[ Saturday ]
[ Sunday ]
```

Explain:

> “The model doesn't invent a date when the user didn't give one.”

This demonstrates controlled uncertainty.

---

# 27. Text Mode

Send a normal text message containing a similarly messy dump.

Demonstrate that the same reasoning pipeline works without voice transcription.

---

# 28. Closing Message

End on:

```text
AUTONOMOUS
PRIVATE
FREE
```

Then explain:

> “ChronoDump isn't another chatbot that waits for another prompt. It turns an unstructured thought into a scheduled action.”

---

# 29. Performance Targets

The MVP should target:

| Component | Target |
|---|---:|
| Telegram message reception | < 1 sec |
| Whisper transcription | Ideally < 20 sec |
| LLM processing | Ideally < 20 sec |
| Total voice-note processing | Target < 45 sec |
| Text processing | Ideally < 10 sec |
| Reminder trigger accuracy | Exact scheduled timestamp |
| Scheduler persistence | Survives restart |
| JSON validity | ≥ 99% after retry |
| Reminder loss after restart | 0 |

These are engineering targets rather than guaranteed benchmarks.

The actual Whisper + LLM latency must be measured on the final deployment hardware before the demo.

---

# 30. Technical Stack

## Bot

```text
Python
aiogram 3.x
```

## Speech-to-Text

```text
faster-whisper
base.en
INT8
Silero VAD
```

Fallback:

```text
tiny.en
```

## LLM

```text
Ollama
llama3.2:3b-instruct
Q4_K_M
```

## Scheduling

```text
APScheduler
```

## Persistence

```text
SQLite
```

## Deployment

```text
Linux
Oracle Cloud Always Free ARM VPS
```

Fallback:

```text
Local laptop
```

---

# 31. Suggested Project Structure

```text
chronodump/
│
├── app/
│   ├── bot/
│   │   ├── handlers.py
│   │   ├── keyboards.py
│   │   └── messages.py
│   │
│   ├── ingestion/
│   │   ├── audio.py
│   │   └── text.py
│   │
│   ├── transcription/
│   │   └── whisper.py
│   │
│   ├── intelligence/
│   │   ├── llm.py
│   │   ├── prompts.py
│   │   ├── schema.py
│   │   └── temporal.py
│   │
│   ├── scheduler/
│   │   ├── jobs.py
│   │   └── reminders.py
│   │
│   ├── storage/
│   │   ├── database.py
│   │   └── models.py
│   │
│   └── config.py
│
├── tests/
│   ├── test_temporal.py
│   ├── test_scheduler.py
│   ├── test_schema.py
│   └── test_handlers.py
│
├── scripts/
│   └── setup.sh
│
├── .env.example
├── requirements.txt
├── README.md
└── LICENSE
```

The exact structure can change during implementation, but responsibilities should remain separated.

---

# 32. Core Engineering Constraints

### Constraint 1

The system must function without a cloud LLM API.

### Constraint 2

Voice processing must work on CPU.

### Constraint 3

The LLM must produce structured output.

### Constraint 4

The scheduler must persist jobs.

### Constraint 5

The system must not fabricate precise timestamps from genuinely vague language.

### Constraint 6

A failed AI step must not destroy the user's original input.

### Constraint 7

The v1 interface remains Telegram.

### Constraint 8

The system remains single-user.

---

# 33. MVP Acceptance Criteria

ChronoDump is considered MVP-complete when all of the following work:

### Input

- [ ] `/start`
- [ ] Timezone selection
- [ ] Voice message
- [ ] Text message
- [ ] Unauthorized user rejection

### Speech

- [ ] OGG download
- [ ] Whisper transcription
- [ ] VAD
- [ ] Low-quality transcription handling

### Intelligence

- [ ] Summary generation
- [ ] Clean notes extraction
- [ ] Action item extraction
- [ ] Exact deadline extraction
- [ ] Relative-time resolution
- [ ] Vague-time classification
- [ ] Structured JSON validation

### Scheduling

- [ ] Exact reminder creation
- [ ] SQLite persistence
- [ ] Restart recovery
- [ ] Reminder execution
- [ ] Snooze
- [ ] Completion confirmation
- [ ] Undo

### Clarification

- [ ] Vague-time queue
- [ ] Inline-button clarification
- [ ] Correct scheduling after clarification
- [ ] “No rush” behavior

### Reliability

- [ ] JSON repair retry
- [ ] Structured-output fallback
- [ ] Whisper failure response
- [ ] No-task response

### Demo

- [ ] 2-minute reminder fires reliably
- [ ] Snooze works
- [ ] Done flow works
- [ ] Undo works
- [ ] Vague deadline demo works
- [ ] Text mode works

---

# 34. Testing Strategy

## Unit Tests

Test temporal expressions independently.

Examples:

```text
"in 2 minutes"
"tomorrow"
"tonight at 10"
"tomorrow morning"
"next Friday"
"3rd January"
"this weekend"
"sometime this week"
"later today"
```

---

## Integration Tests

Test:

```text
Telegram input
→ transcription
→ LLM
→ schema
→ scheduler
→ database
→ reminder
```

---

## Failure Tests

Intentionally provide:

- Invalid LLM JSON
- Empty LLM response
- Garbage transcript
- Missing deadline
- Ambiguous deadline
- Bot restart with pending jobs
- Unauthorized Telegram user

---

# 35. Observability

For development, log:

```text
Request ID
Input type
Transcription latency
LLM latency
Scheduler latency
JSON validation result
Reminder creation
Reminder execution
User interaction
```

Do **not** log raw private voice content unnecessarily.

The final product should prioritize useful operational logs without turning observability into another privacy risk.

---

# 36. Product Metrics

The primary success metric is not the number of AI tokens generated.

The system should be evaluated on:

### Extraction accuracy

Did it identify the correct tasks?

### Temporal accuracy

Did it interpret the user's intended time correctly?

### False scheduling rate

How often did it create a reminder that the user didn't actually intend?

### Clarification accuracy

Did it ask for clarification when it should?

### Reminder reliability

Did scheduled reminders actually fire?

### End-to-end latency

How long does a voice dump take to become an actionable result?

### User friction

How many interactions were required to go from thought → scheduled action?

Ideal:

```text
1 dump
→ 0 manual task creation
```

---

# 37. Known Risks

## Risk 1 — Small LLM misunderstanding temporal language

Mitigation:

- Explicit current datetime
- Strict schema
- Temporal validation
- Vague-time queue
- No guessing

---

## Risk 2 — CPU inference latency

Mitigation:

- Quantized model
- 3B model
- faster-whisper INT8
- VAD
- Short demo input
- Measure actual VPS latency

---

## Risk 3 — Whisper transcription errors

Mitigation:

- VAD
- Confidence/error handling
- Re-record prompt
- Text fallback

---

## Risk 4 — Scheduler failure

Mitigation:

- SQLite jobstore
- Persistent jobs
- Restart testing
- Integration tests

---

## Risk 5 — Demo failure

Mitigation:

- Pre-test exact script
- Keep a backup screen recording
- Have text mode available
- Have a manually prepared screenshot of vague-time clarification

The live reminder should still be the primary demo.

---

# 38. Open Items Before Submission

These should be resolved during implementation:

### 1. Benchmark actual latency

Measure:

```text
Whisper
+
LLM
+
JSON validation
+
scheduler
```

on the final deployment environment.

### 2. Finalize “No Rush”

Current proposed behavior:

```text
No rush
→ remove from reminder queue
→ retain in Clean Notes
```

### 3. Confirm VPS availability

Verify the Oracle Cloud free-tier environment can actually run:

```text
Ollama
+
Whisper
+
Bot
+
SQLite
```

simultaneously.

### 4. Test restart recovery

Create a reminder.

Restart the entire application.

Verify that it still fires.

---

# 39. Hacktoberfest Submission Narrative

## The Problem

> Voice notes are great for capturing thoughts, but terrible at turning those thoughts into actions. Important deadlines can disappear inside a 30-second recording.

## The Build

> I built ChronoDump, a Telegram-based local AI agent that listens to messy voice notes, extracts tasks and deadlines, understands relative time, and automatically schedules reminders.

## The Open-Source Angle

> ChronoDump uses local open-weight AI for both speech and reasoning. The user's audio and thoughts don't need to be sent to a proprietary AI API. The model can be replaced, modified, and run locally.

## The Interesting Part

> The system doesn't just answer the user. It takes action later.

If someone says:

> “Remind me to drink water in two minutes.”

ChronoDump actually waits two minutes and sends the reminder.

## The Privacy Angle

> Your brain dump can contain deeply personal information. ChronoDump is designed so that the raw audio, transcript, and reasoning pipeline can stay inside infrastructure controlled by the user.

## The Cost Angle

> The intended deployment can run on free infrastructure or a local machine without paid AI APIs.

---

# 40. Final Product Positioning

### Short pitch

> **ChronoDump is a local AI agent that turns messy voice notes into structured tasks and actually reminds you when it's time to act.**

### Longer pitch

> **ChronoDump lets you dump whatever is in your head through Telegram. A local open-weight AI model cleans up the chaos, extracts tasks and deadlines, resolves relative time, asks when you're vague, and automatically arms persistent reminders. No cloud AI API. No complicated task manager. Just talk, and ChronoDump handles the rest.**

### Three product pillars

```text
        CHRONODUMP

      AUTONOMOUS
          │
          ├── Understands intent
          ├── Resolves time
          └── Acts later

        PRIVATE
          │
          ├── Local transcription
          ├── Local inference
          └── Local data

          FREE
          │
          ├── Open-weight AI
          ├── No API fees
          └── Free/local deployment
```

---

# 41. Final Definition of Done

ChronoDump is ready for the Hacktoberfest submission when:

> A real friend can open Telegram, send a completely unstructured voice note containing multiple thoughts and deadlines, receive a useful structured response, and later receive at least one correctly timed reminder **without manually creating that reminder**.

And the entire flow can run using:

```text
Open-source/local AI
+
Local application logic
+
Persistent scheduler
+
Telegram
```

without requiring a proprietary AI API.

---

# 42. The Core Idea

ChronoDump is ultimately not a:

> **voice-to-text app**

and not a:

> **task manager**

and not merely a:

> **RAG/LLM chatbot.**

It is:

> **A small autonomous agent that converts unstructured human intent into scheduled real-world action.**

That is the behavior the product should optimize for.
