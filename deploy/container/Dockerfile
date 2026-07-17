# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# HELM LIVE API — container image
# ---------------------------------------------------------------------------
# Runs the runtime-truth control-plane API (backend/helm_live_api.py) as a
# reproducible, isolated, restart-on-crash service.
#
# Honest scope: this container serves the FastAPI app on plain HTTP :8770.
# It does NOT terminate TLS (that is a reverse-proxy / host concern — see
# deploy/container/README.md) and it does NOT run the macOS launchd daemons
# (their job is replaced by the compose `restart:` policy + optional loop svc).
#
# Build context MUST be the repo ROOT (needs pyproject.toml, uv.lock,
# dummy_mcp/, backend/). See docker-compose.yml `build.context: ../..`.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

# uv is the resolver the repo already pins with (pyproject.toml + uv.lock,
# including the local path dep `mcp = ./dummy_mcp`). Using it here keeps the
# in-container dependency set byte-identical to the founder's Mac venv.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_CONCURRENCY=2

WORKDIR /app

# Minimal system deps: curl for the HEALTHCHECK, git because some crewai
# tooling shells out to it, sqlite3 for the swarm_ledger.db volume.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl git sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# ---- dependency layer (cached until pyproject/lock change) ----------------
# Copy only the dependency spec + the local path dep first so `docker build`
# reuses this layer across source edits.
COPY pyproject.toml uv.lock ./
COPY dummy_mcp/ ./dummy_mcp/
RUN uv sync --frozen --no-install-project

# ---- application layer ----------------------------------------------------
COPY . .
RUN uv sync --frozen

# ---- non-root hardening ---------------------------------------------------
# Runtime writes to /app/coordination and /app/backend/swarm_ledger.db, which
# are mounted as named volumes in compose; own /app so appuser can write.
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appgroup /app
USER appuser

ENV PYTHONPATH="/app" \
    HELM_VOICE_PORT=8770

EXPOSE 8770

# Liveness: the /api/helm/live endpoint returns real runtime JSON (no auth by
# default; read-auth is mounted-but-off — see README).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS "http://127.0.0.1:8770/api/helm/live" || exit 1

# TLS is intentionally dropped in-container (terminate at a reverse proxy).
# Bind 0.0.0.0 so the container is reachable on its published port; keep the
# published port bound to 127.0.0.1 on the host (see compose).
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "backend.helm_live_api:app", \
     "--host", "0.0.0.0", "--port", "8770"]
