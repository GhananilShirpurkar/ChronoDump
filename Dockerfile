# ==============================================================================
# ChronoDump Dockerfile
# ==============================================================================
FROM python:3.12-slim

# Prevent Python from buffering stdout/stderr and writing pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies: ffmpeg for audio normalization, curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python package dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ app/
COPY scripts/ scripts/
COPY README.md .

# Ensure data directory exists
RUN mkdir -p data/audio

# Expose data volume
VOLUME ["/app/data"]

# Default entrypoint
CMD ["python", "-m", "app.main"]
