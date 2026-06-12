# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — builder: compile wheels so the runtime image stays lean.
# python:3.12-slim is multi-arch (works on x86 Fedora and arm64 Raspberry Pi).
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-lock.txt .
RUN pip wheel --wheel-dir /wheels -r requirements-lock.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime: minimal image, non-root user, gunicorn server.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /srv/app

# psycopg[binary] bundles libpq; curl is only needed for the healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 appuser

COPY --from=builder /wheels /wheels
COPY requirements-lock.txt .
RUN pip install --no-cache-dir --no-index --find-links /wheels -r requirements-lock.txt \
    && rm -rf /wheels

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser config.py wsgi.py seed.py ./
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p instance && chown appuser:appuser instance

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/login > /dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", \
     "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-", \
     "wsgi:app"]
