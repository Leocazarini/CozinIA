FROM python:3.12-slim

WORKDIR /app

# build-essential + libxml2/libxslt: needed to build asyncpg/lxml (trafilatura dep).
# curl: used by the Docker Compose healthcheck.
# ffmpeg: yt-dlp uses it to pull the audio out of a video for transcription.
# Platforms that only serve a combined stream (Reels, TikTok) have no
# audio-only format to download, and it is also what downmixes the audio to
# 16 kHz mono so the file stays small (see app/services/video_source.py).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        curl \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

EXPOSE 8000

# Apply pending migrations before serving traffic, so `docker compose up`
# always ends up with an up-to-date schema without a manual step.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
