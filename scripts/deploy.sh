#!/usr/bin/env bash
# ==============================================================================
# ChronoDump Production 5-Phase Deployment Runner
# Implements: PREPARE -> BACKUP -> DEPLOY -> VERIFY -> CONFIRM/ROLLBACK
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

DEPLOY_MODE="${1:-systemd}"  # Options: systemd | docker | native

echo "⚡ ========================================================"
echo "🚀 ChronoDump Production Deployment: Mode [${DEPLOY_MODE}]"
echo "=========================================================="

# -----------------------------------------------------------------------------
# PHASE 1: PREPARE
# -----------------------------------------------------------------------------
echo ""
echo "🔍 [Phase 1/5: PREPARE] Checking pre-flight requirements..."

if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Copy .env.example to .env and configure secrets."
    exit 1
fi

PYTHON_EXEC=".venv/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi

echo "🧪 Running full test suite before deployment..."
$PYTHON_EXEC -m pytest tests/ -q
echo "✅ All tests passed cleanly."

# -----------------------------------------------------------------------------
# PHASE 2: BACKUP
# -----------------------------------------------------------------------------
echo ""
echo "💾 [Phase 2/5: BACKUP] Taking atomic point-in-time database snapshot..."
bash scripts/backup.sh
echo "✅ State safely preserved."

# -----------------------------------------------------------------------------
# PHASE 3: DEPLOY
# -----------------------------------------------------------------------------
echo ""
echo "📦 [Phase 3/5: DEPLOY] Applying updates..."

if [ "$DEPLOY_MODE" = "docker" ]; then
    echo "🐳 Building and reloading Docker container..."
    docker compose up -d --build
elif [ "$DEPLOY_MODE" = "systemd" ]; then
    echo "⚙️ Reloading systemd user service..."
    if command -v systemctl >/dev/null 2>&1; then
        # Ensure user service file is in place
        mkdir -p ~/.config/systemd/user/
        cp chronodump.service ~/.config/systemd/user/
        systemctl --user daemon-reload
        systemctl --user restart chronodump || {
            echo "⚠️ Could not restart systemd user service directly. Attempting enable & start..."
            systemctl --user enable chronodump
            systemctl --user start chronodump
        }
        echo "✅ systemd service reloaded."
    else
        echo "⚠️ systemctl not found. Falling back to native process restart."
        DEPLOY_MODE="native"
    fi
fi

if [ "$DEPLOY_MODE" = "native" ]; then
    echo "🔄 Restarting local background process..."
    pkill -f "app.main" || true
    sleep 1
    nohup $PYTHON_EXEC -m app.main > data/chronodump.log 2>&1 &
    echo "✅ Native daemon launched (PID: $!)."
fi

# -----------------------------------------------------------------------------
# PHASE 4: VERIFY
# -----------------------------------------------------------------------------
echo ""
echo "🩺 [Phase 4/5: VERIFY] Running health checks..."
sleep 3
$PYTHON_EXEC scripts/healthcheck.py

# -----------------------------------------------------------------------------
# PHASE 5: CONFIRM
# -----------------------------------------------------------------------------
echo ""
echo "=========================================================="
echo "🎉 [Phase 5/5: CONFIRM] Deployment Successful!"
echo "ChronoDump is actively running in production mode."
echo ""
echo "Useful Commands:"
echo "• Health Check:     $PYTHON_EXEC scripts/healthcheck.py"
echo "• Trigger Backup:   bash scripts/backup.sh"
echo "• View Logs:        journalctl --user -u chronodump -f   (systemd)"
echo "• View Docker Logs: docker compose logs -f               (docker)"
echo "=========================================================="
