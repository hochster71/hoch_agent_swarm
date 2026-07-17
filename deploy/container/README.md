# HELM LIVE — Containerization (honest edition)

**Answering the founder's question — "why isn't `hoch_agent_swarm` in a container?"**

It mostly *can* be, and this directory makes that real for the part that matters
most: the **HELM LIVE control-plane API** (`backend/helm_live_api.py`). What
follows is the truthful split — what containerizes cleanly, what stays
Mac-host-native, and exactly why. No fake green.

---

## TL;DR — run it

```bash
cd deploy/container
cp .env.example .env          # fill in real values at deploy time (never commit .env)
docker compose up --build     # builds from repo root, serves HELM LIVE on 127.0.0.1:8770
```

Health: `curl http://127.0.0.1:8770/api/helm/live`
UI: `http://127.0.0.1:8770/helm`

Optional background loop service (standby placeholder, see below):
```bash
docker compose --profile loop up --build
```

---

## What runs IN the container (clean)

| Component | Notes |
|---|---|
| **HELM LIVE FastAPI app** | `uvicorn backend.helm_live_api:app --host 0.0.0.0 --port 8770`. Uses `ROOT = Path(__file__).parents[1]` — **relative pathing**, so it's container-native. |
| **Product / control-plane routers** | voice, council/instrument-integrity, health registry, NIST matrix, mission-control (scheduler, adapters, scoped-states) — all pure-Python, imported by the API, no macOS deps on the import path (verified). |
| **Python dependency set** | Pinned by `pyproject.toml` + `uv.lock` (incl. the local path dep `mcp = ./dummy_mcp`). Installed with `uv sync --frozen` so the image matches the Mac venv byte-for-byte. `python-dotenv` is present transitively, so `.env` loading still works. |
| **State: `coordination/`** | Leases and council live-proof packages — read/written by **relative path**, mounted as the `helm-coordination` named volume so restarts don't wipe it. |

Runs as **non-root** (`appuser`, uid 10001), `cap_drop: ALL`,
`no-new-privileges`, published to **loopback only**.

## What stays Mac-host-native (and why)

| Mac-host thing | Why it can't/shouldn't move as-is | Container replacement |
|---|---|---|
| **launchd daemons** (`com.hoch.helm.voice`, `com.hoch.agent.swarm.runtime`, autoloop) — the KeepAlive supervisors | launchd is macOS-only; there is no `launchctl` in a Linux container | `restart: unless-stopped` (compose) IS the KeepAlive. The autoloop supervisor becomes the optional `helm-loop` sibling service. |
| **macOS Keychain** secrets | Keychain is an OS service; not reachable from a Linux container | Inject via `.env` / env vars (`env_file`) or a real secret manager. Placeholders in `.env.example`. |
| **Local dev TLS cert** | The founder's dev cert is macOS-issued; both launchers actually run **plain HTTP** on 8770 already (`scripts/run_helm_live_foreground.sh`, `scripts/start_helm_voice.sh`) | **TLS is dropped in-container by design.** Terminate TLS at a reverse proxy (Caddy/nginx/Traefik) or the host/VPS load balancer in front of :8770. |
| **Founder desktop notifications** (`backend/council/notify_founder.py` → `osascript`) | `osascript` / Notification Center are macOS-only | Notifications degrade gracefully; route to Slack/webhook when running headless. Not on the API import path, so it never blocks the build. |
| **launchd-state readers** (`cluster_manager.py`, `runtime_truth/collector.py` → `launchctl list`) | No `launchctl` in-container | They already **fail closed to an honest empty list** (their own comments say so) — no crash, they just report "no launchd jobs here." |

## Known blockers to a *clean* build / true HA (found by grep — reported honestly)

1. **Hardcoded absolute path** — `backend/agent_router.py:38`:
   `Path("/Users/michaelhoch/hoch_agent_swarm_prompt_library/deprecated/aliases.yaml")`.
   Absolute `/Users/...` path that won't exist in-container. **Not** imported by
   the HELM LIVE API at module load, so it does **not** block *this* image — but
   it will break `agent_router` if that subsystem is containerized. Fix:
   parametrize via env (e.g. `HOCH_PROMPT_LIBRARY_DIR`).
2. **SQLite ledger path is hardcoded** — the API reads
   `ROOT/backend/swarm_ledger.db` with no env override. In this image the DB is a
   **build-time snapshot baked into the layer**; writes are ephemeral unless you
   bind-mount the file (commented option in `docker-compose.yml`). For real HA,
   parametrize the DB path via env and move to a mounted volume **or an external
   Postgres** — a single-writer SQLite file on a shared volume is not HA.
3. **`backend/main.py:5231`** shells `sudo launchctl load … com.apple.syslogd` —
   macOS-only, and `sudo` won't exist for the non-root user. `backend/main.py`
   is a *different* app (the `has-api` on :8000), not the HELM LIVE API, so it's
   out of scope here — flagged so it isn't containerized blind.
4. **Docstring-only path** — `backend/truth/supply_chain.py:6` mentions
   `/Users/michaelhoch/.local/bin/grok` in prose only. **Not a code blocker.**

Good news from the grep: **no `pyobjc` / `Foundation` / `AppKit` / `EventKit`
imports anywhere in `backend/`** — the heavy macOS-native trap is absent, which
is why the API layer containerizes cleanly.

## Resilience wins (the actual answer to "why containerize")

- **Reproducible** — `uv.lock`-pinned deps; no "works on my Mac" drift.
- **Portable** — lift-and-shift from the MacBook to a Linux VPS or k8s node.
- **Isolated** — no reliance on the host's global Python, `.venv`, or PATH.
- **Self-healing** — `restart: unless-stopped` + `HEALTHCHECK` restarts on crash
  (replaces the launchd KeepAlive with a platform-neutral mechanism).
- **Hardened** — non-root, `cap_drop: ALL`, `no-new-privileges`, loopback-only
  publish, secrets via env/secret-manager instead of Keychain.

## Files here

| File | Purpose |
|---|---|
| `Dockerfile` | Python 3.11-slim, uv-installed pinned deps, non-root, serves HELM LIVE on :8770 (plain HTTP). |
| `docker-compose.yml` | `helm-api` service (:8770, coordination volume, healthcheck) + optional `helm-loop` (profile `loop`). |
| `.dockerignore` | Trims build context; excludes `.venv`, `node_modules`, `.git`, `data/backups`, `_quarantine`, `*.db`, all `.env*` (keeps `.env.example`), secrets. |
| `.env.example` | Placeholder env — **no real secrets**. Copy to `.env` at deploy. |

**Build context is the repo ROOT** (compose sets `context: ../..`) because the
image needs `pyproject.toml`, `uv.lock`, `dummy_mcp/`, and `backend/`.

> Not validated with a live `docker build` in this environment (Docker not
> available here). The compose file is confirmed to parse and the Dockerfile is
> syntactically sane; the dependency install mirrors the repo's already-working
> `Dockerfile` / `Dockerfile.api`, adapted to 3.11-slim + the HELM LIVE entry.
