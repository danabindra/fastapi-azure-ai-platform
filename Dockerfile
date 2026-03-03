# syntax=docker/dockerfile:1
# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Cache dependencies layer
COPY pyproject.toml ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for ACA security
RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

# Copy venv from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application source
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build-time args injected by CI
ARG GIT_SHA=unknown
ARG BUILD_TIME=""
ENV GIT_SHA=${GIT_SHA} \
    BUILD_TIME=${BUILD_TIME}

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
