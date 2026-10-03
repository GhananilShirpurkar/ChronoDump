#!/usr/bin/env bash
# ==============================================================================
# ChronoDump Production SQLite Online Backup Script
# Uses Python's native sqlite3 online backup API for zero-lock, atomic snapshots.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

DATA_DIR="${DATA_DIR:-$ROOT_DIR/data}"
BACKUP_DIR="${BACKUP_DIR:-$DATA_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"

mkdir -p "$BACKUP_DIR"

echo "📦 [$(date +'%Y-%m-%d %H:%M:%S')] Starting ChronoDump database backup..."

PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# Perform safe, atomic online backup using Python sqlite3.backup()
"$PYTHON_BIN" - <<EOF
import sqlite3
import os
from pathlib import Path

data_dir = Path("$DATA_DIR")
backup_dir = Path("$BACKUP_DIR")
ts = "$TIMESTAMP"

databases = [
    ("chronodump.db", f"chronodump_{ts}.db"),
    ("chronodump_scheduler.db", f"chronodump_scheduler_{ts}.db"),
]

for src_name, dst_name in databases:
    src_path = data_dir / src_name
    dst_path = backup_dir / dst_name

    if not src_path.exists():
        print(f"⚠️ Source database {src_path} does not exist yet. Skipping.")
        continue

    src_conn = sqlite3.connect(str(src_path))
    dst_conn = sqlite3.connect(str(dst_path))

    with dst_conn:
        src_conn.backup(dst_conn, pages=100, sleep=0.01)

    src_conn.close()
    dst_conn.close()

    size_kb = round(os.path.getsize(dst_path) / 1024, 2)
    print(f"✅ Backed up {src_name} -> {dst_name} ({size_kb} KB)")
EOF

# Compress the snapshot files
gzip -f "$BACKUP_DIR"/chronodump_"$TIMESTAMP".db 2>/dev/null || true
gzip -f "$BACKUP_DIR"/chronodump_scheduler_"$TIMESTAMP".db 2>/dev/null || true

echo "🔒 Compressing complete."

# Prune older backups according to retention policy
echo "🧹 Pruning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.db.gz" -type f -mtime +"$RETENTION_DAYS" -exec rm -f {} + 2>/dev/null || true

echo "✅ Backup process finished successfully."
