# Multi-stage: the build tools (build-essential and the -dev headers) live only
# in the builder, so the image that actually runs — and processes hostile media
# through ffmpeg — carries none of that extra surface, and runs as a non-root
# user.

FROM python:3.12-slim AS builder

# build-essential + libxml2/libxslt headers: needed to build any dependency
# without a prebuilt wheel (asyncpg, lxml). Confined to this stage.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
# Installs the app and its deps (including dev: the tests-backend service runs
# pytest from this same image) into the venv, which the runtime stage copies.
RUN pip install --no-cache-dir ".[dev]"


FROM python:3.12-slim AS runtime

# Runtime-only libraries — no compilers:
# curl: the Compose healthcheck.
# ffmpeg: yt-dlp uses it to pull and downmix a video's audio for transcription.
# libxml2/libxslt1.1: the shared libs lxml links against at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY . .

# Run as an unprivileged user: a parsing bug in ffmpeg (fed attacker media) or
# any other RCE is then contained to this account, not root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Apply pending migrations before serving traffic, so `docker compose up`
# always ends up with an up-to-date schema without a manual step.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
