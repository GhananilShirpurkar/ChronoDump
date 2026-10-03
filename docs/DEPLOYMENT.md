# 🚀 ChronoDump Production Deployment Guide

This guide details the deployment, monitoring, backup, and rollback procedures for ChronoDump across **Linux systemd** and **Docker Compose** environments.

---

## 🏗️ Architecture Overview

```text
                                 ┌─────────────────────────────────┐
                                 │   Telegram Cloud Servers        │
                                 └───────────────▲─────────────────┘
                                                 │ Long Polling (HTTPS)
                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Host Machine (Linux / Server)                                          │
│                                                                        │
│   ┌────────────────────────────────┐    ┌──────────────────────────┐  │
│   │ ChronoDump Service             │    │ Local Ollama Service     │  │
│   │ (systemd unit / Docker)        │───►│ (http://localhost:11434) │  │
│   │                                │    │ Model: qwen2.5:3b        │  │
│   │  • faster-whisper (CPU int8)   │    └──────────────────────────┘  │
│   │  • Silero VAD                  │                                  │
│   │  • APScheduler Engine          │    ┌──────────────────────────┐  │
│   │  • SQLite Storage Engine       │───►│ data/chronodump.db       │  │
│   └────────────────────────────────┘    │ data/chronodump_sched.db │  │
│                   │                     └──────────────────────────┘  │
│                   ▼                                                   │
│   ┌────────────────────────────────┐    ┌──────────────────────────┐  │
│   │ Automated Backup Engine        │───►│ data/backups/*.db.gz     │  │
│   │ (Atomic online snapshots)      │    │ (7-day retention)        │  │
│   └────────────────────────────────┘    └──────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Deployment Methods

| Feature | Option 1: systemd (Recommended) | Option 2: Docker Compose |
|---|---|---|
| **Best For** | Local-first machine, dedicated server, lowest overhead | Isolated environments, cloud VPS |
| **Ollama Access** | Direct localhost socket | Via `host.docker.internal` or bundled |
| **Performance** | Native CPU throughput | Minor virtualization overhead |
| **Persistence** | Direct `./data` directory | Docker named or bind volumes |
| **Auto-restart** | `systemd` supervisor (`Restart=always`) | Docker `restart: unless-stopped` |

---

## 🛠️ Option 1: Linux systemd Service (Recommended)

Running ChronoDump as a `systemd` user service provides 24/7 background persistence, automatic recovery on unexpected crashes, and start-on-boot capability without needing root privileges.

### Step 1: Copy Service File
```bash
mkdir -p ~/.config/systemd/user/
cp chronodump.service ~/.config/systemd/user/
```

### Step 2: Reload and Enable
```bash
systemctl --user daemon-reload
systemctl --user enable chronodump
systemctl --user start chronodump
```

### Step 3: Keep Running Across Reboots (Without Login)
By default, user services stop when you log out. Enable **lingering** so your bot runs continuously even when logged out:
```bash
loginctl enable-linger $USER
```

### Step 4: Check Status and Logs
```bash
# Check service status
systemctl --user status chronodump

# Stream real-time logs
journalctl --user -u chronodump -f
```

---

## 🐳 Option 2: Docker Compose

ChronoDump provides two Docker Compose configurations:

### Mode A: Connect to Host Ollama (Default)
Uses your existing host machine's Ollama installation (saves memory and avoids duplicating models):
```bash
# Start container in background
docker compose up -d --build

# View logs
docker compose logs -f

# Check health
docker compose ps
```

### Mode B: Self-Contained Full Stack (Bundled Ollama)
Spins up both ChronoDump and a dedicated Ollama container:
```bash
# Start full cluster
docker compose -f docker-compose.full.yml up -d --build

# Pull model inside the container on first run
docker exec -it chronodump-ollama ollama pull qwen2.5:3b
```

---

## 🩺 Health Checks & Verification

ChronoDump includes an automated health probe script located at [`scripts/healthcheck.py`](file:///home/koanoir/Desktop/Projects/04_hackathons/ChronoDump/scripts/healthcheck.py).

### Run CLI Health Check
```bash
.venv/bin/python scripts/healthcheck.py
```
**Output:**
```text
⚡ ChronoDump Health Probe
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Environment: Configured (User: 1775065634, Timezone: UTC)
✅ Databases: Connected (App: 48.0 KB, Sched: 16.0 KB)
✅ Ollama LLM: Connected to http://localhost:11434 (Model: qwen2.5:3b ready)
✅ Telegram API: Connected as @chrono_dump_bot (ID: 8813593732)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 ALL SYSTEMS OPERATIONAL
```

### Run JSON Output (for Monitoring / Uptime Kuma)
```bash
.venv/bin/python scripts/healthcheck.py --json
```

---

## 💾 Automated Database Backups

ChronoDump stores all memory, context notes, user preferences, and scheduled jobs in SQLite. 

### Manual Backup
```bash
bash scripts/backup.sh
```
Uses Python's native `sqlite3.backup()` API to capture consistent, zero-lock point-in-time snapshots in `data/backups/`, compressed with gzip.

### Setting Up a Daily Backup Cron Job
To automatically back up every night at 3:00 AM:
```bash
crontab -e
```
Add the following entry:
```text
0 3 * * * /bin/bash /home/koanoir/Desktop/Projects/04_hackathons/ChronoDump/scripts/backup.sh >> /home/koanoir/Desktop/Projects/04_hackathons/ChronoDump/data/backup.log 2>&1
```

---

## 🚨 Emergency Rollback

If a bad migration or data corruption occurs, run the automated rollback script:
```bash
bash scripts/rollback.sh
```
This will:
1. Stop the active bot instance safely.
2. Locate the most recent valid snapshot in `data/backups/`.
3. Restore `data/chronodump.db` and `data/chronodump_scheduler.db`.
4. Restart the bot service.
5. Execute `scripts/healthcheck.py` to confirm full recovery.

---

## 🚢 Automated 5-Phase Deployment Script

Deploy updates safely with one command:
```bash
# Deploy with systemd (Default)
bash scripts/deploy.sh systemd

# Deploy with Docker
bash scripts/deploy.sh docker
```

The script executes the 5-phase deployment workflow:
1. **PREPARE**: Validates environment variables and runs the test suite (`pytest tests/`).
2. **BACKUP**: Automatically triggers `backup.sh` before applying updates.
3. **DEPLOY**: Rebuilds Docker image or restarts the systemd unit.
4. **VERIFY**: Runs `healthcheck.py` against the updated service.
5. **CONFIRM**: Outputs operational status and journal commands.
