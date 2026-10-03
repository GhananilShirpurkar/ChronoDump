# ==============================================================================
# ChronoDump Production Container Dockerfile
# ==============================================================================
FROM python:3.12-slim

# Prevent Python buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

# Install runtime system packages: ffmpeg (audio normalization), curl (probes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and scripts
COPY app/ app/
COPY scripts/ scripts/
COPY README.md .

# Create volume mount points and permissions
RUN mkdir -p /app/data/audio /app/data/backups

# Expose volume for persistent SQLite storage and Whisper models
VOLUME ["/app/data"]

# Container health probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python scripts/healthcheck.py || exit 1

# Default runtime command
CMD ["python", "-m", "app.main"]
