#!/usr/bin/env bash
# ==============================================================================
# ChronoDump Production Rollback Script
# Restores previous SQLite databases from data/backups/ and restarts services.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
BACKUP_DIR="${BACKUP_DIR:-$DATA_DIR/backups}"

echo "⏪ ========================================================"
echo "🚨 ChronoDump Emergency Rollback Procedure"
echo "=========================================================="

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ No backup directory found at $BACKUP_DIR"
    exit 1
fi

# Find latest backup file
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/chronodump_*.db.gz 2>/dev/null | head -n 1 || true)
if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No database backup archives found in $BACKUP_DIR"
    exit 1
fi

TIMESTAMP=$(basename "$LATEST_BACKUP" | sed 's/chronodump_//' | sed 's/\.db\.gz//')
echo "📦 Target backup snapshot timestamp: $TIMESTAMP"

echo "🛑 Halting active ChronoDump instances before restoring state..."
pkill -f "app.main" || true
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop chronodump 2>/dev/null || true
fi

echo "🔄 Restoring databases..."
gzip -dc "$BACKUP_DIR/chronodump_${TIMESTAMP}.db.gz" > "$DATA_DIR/chronodump.db"
echo "✅ Restored $DATA_DIR/chronodump.db"

if [ -f "$BACKUP_DIR/chronodump_scheduler_${TIMESTAMP}.db.gz" ]; then
    gzip -dc "$BACKUP_DIR/chronodump_scheduler_${TIMESTAMP}.db.gz" > "$DATA_DIR/chronodump_scheduler.db"
    echo "✅ Restored $DATA_DIR/chronodump_scheduler.db"
fi

echo "🚀 Restarting ChronoDump service..."
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-enabled chronodump >/dev/null 2>&1; then
    systemctl --user start chronodump
    echo "✅ Started via systemd user service."
else
    nohup .venv/bin/python -m app.main > data/chronodump.log 2>&1 &
    echo "✅ Started native daemon (PID: $!)."
fi

sleep 2
echo "🩺 Verifying health after rollback..."
.venv/bin/python scripts/healthcheck.py

echo "=========================================================="
echo "✅ Rollback completed successfully."
echo "=========================================================="
