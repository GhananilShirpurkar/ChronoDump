#!/usr/bin/env bash
# ==============================================================================
# ChronoDump Setup Script
# ==============================================================================

set -e

echo "=========================================================="
echo "⚡ Starting ChronoDump Automated Setup"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# 1. Check for ffmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ ffmpeg detected: $(which ffmpeg)"
else
    echo "⚠️ ffmpeg not detected. We recommend installing ffmpeg for optimal audio normalization (e.g. sudo apt install ffmpeg)."
fi

# 2. Check for Ollama
if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama detected: $(which ollama)"
    # Check if Ollama server is responding
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama daemon is running."
        echo "📥 Ensuring recommended local model is downloaded (qwen2.5:3b)..."
        ollama pull qwen2.5:3b || echo "⚠️ Could not pull qwen2.5:3b automatically. You can pull it manually with: ollama pull qwen2.5:3b"
    else
        echo "⚠️ Ollama is installed but not running. Start it with: ollama serve"
    fi
else
    echo "⚠️ Ollama is not installed. Please install Ollama from https://ollama.com to enable local open-weight inference."
fi

# 3. Setup Python Virtual Environment using uv or python3
if command -v uv >/dev/null 2>&1; then
    echo "✅ uv package manager detected."
    if [ ! -d ".venv" ]; then
        echo "📦 Creating virtual environment with uv (Python 3.12)..."
        uv venv --python 3.12 .venv || uv venv .venv
    fi
    echo "📦 Installing Python dependencies with uv..."
    uv pip install -r requirements.txt
    PYTHON_EXEC=".venv/bin/python"
else
    echo "📦 Creating standard Python virtual environment..."
    python3 -m venv .venv
    echo "📦 Installing Python dependencies with pip..."
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    PYTHON_EXEC=".venv/bin/python"
fi

# 4. Environment and Secrets configuration
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️ Created .env file. Please edit .env with your TELEGRAM_BOT_TOKEN and AUTHORIZED_USER_ID."
else
    echo "✅ .env file found."
fi

# 5. Initialize Storage & Database
echo "🗄️ Initializing SQLite database and directories..."
mkdir -p data/audio
$PYTHON_EXEC -c "from app.storage.database import init_db; init_db()"

echo ""
echo "=========================================================="
echo "🎉 ChronoDump setup complete!"
echo ""
echo "Next Steps:"
echo "1. Edit .env and set your secrets:"
echo "   TELEGRAM_BOT_TOKEN=<your_telegram_bot_token>"
echo "   AUTHORIZED_USER_ID=<your_telegram_user_id>"
echo ""
echo "2. Start the bot:"
echo "   source .venv/bin/activate"
echo "   python -m app.main"
echo "=========================================================="
