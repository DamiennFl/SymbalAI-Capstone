
FROM python:3.11-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy only dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into .venv (no cache to save space)
RUN uv sync --frozen --no-cache

FROM python:3.11-slim

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
# Force CPU execution for ML models
ENV CUDA_VISIBLE_DEVICES=""
ENV CT2_VERBOSE=0

WORKDIR /app

# Copy the virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy source code (respects .dockerignore)
COPY . /app

# Create non-root user with limited capabilities and switch to it
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Health check for Kubernetes liveness probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/liveness')" || exit 1

CMD ["/app/.venv/bin/granian", "--interface", "asgi", "--log", "--access-log", "--host", "0.0.0.0", "--port", "8000", "--workers-kill-timeout", "120", "--http1-keep-alive","--http2-keep-alive-timeout", "75", "src/main:app"]