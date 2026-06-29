# Gordon Docker Debug Playbook — Hoch Agent Swarm

This playbook outlines instructions and prompt patterns for operators and the Ask Gordon agent to resolve Docker runtime drift, daemon unresponsiveness, and telemetry regressions.

---

## 1. Docker Daemon Unresponsive

### Symptom
`docker ps` or `docker info` hangs, times out, or returns a 500 socket error.

### Remediation Protocol
Run the following commands on the host:
```bash
# 1. Force quit Docker Desktop
osascript -e 'quit app "Docker"' 2>/dev/null || true
pkill -f "Docker" 2>/dev/null || true
pkill -f "com.docker" 2>/dev/null || true

# 2. Clear corrupted settings store backup if present
rm -f ~/Library/Group\ Containers/group.com.docker/settings-store.json.backup 2>/dev/null || true

# 3. Launch Docker Desktop fresh
open -a Docker
sleep 20

# 4. Confirm daemon responsiveness
docker info
docker ps
```

### Gordon Query
> Gordon, the local Docker Desktop daemon is throwing 500 socket errors or is completely unresponsive. Analyze the host systems `/var/run/docker.sock` and output helper state to diagnose if there is a VM memory overrun or lock leak. Propose a safe cleanup plan.

---

## 2. Stale UI Bundle

### Symptom
UI shows stale values like `100%`, `GO FOR SWARM`, or `LAUNCH_READY` while the API verdict is `BLOCKED`.

### Remediation Protocol
Clear Docker and browser cache, rebuild and redeploy:
```bash
# Force fresh webpack/vite compile and container layer recreation
docker compose down
docker compose build --no-cache has-ui
docker compose up -d has-ui
```

### Gordon Query
> Gordon, the served index.html bundle in the Nginx has-ui container contains stale strings such as 'GO FOR SWARM' or 'Readiness Score: 100%'. Inspect the builder container build context and default.conf configuration to ensure Vite output is not cached or shadowed by old host directory layers.

---

## 3. API/UI Truth Mismatch

### Symptom
Container API `/api/v1/final-verifier/verdict` reports `BLOCKED`, but UI top-bar displays `VERIFIED`.

### Remediation Protocol
Run `scripts/docker_truth_check.sh` on the host to pinpoint which exact string is leaking. Check Nginx reverse proxy routing:
```bash
curl -sS http://localhost:8080/api/v1/final-verifier/verdict
```
If `/api/` requests are returning 404 or bypassing `has-api`, verify the `has-net` docker network and default Nginx config.

### Gordon Query
> Gordon, audit the Nginx api proxy routing inside default.conf. Ensure that served UI requests to /api/ are correctly routed to the active has-api container rather than matching host fallback endpoints.

---

## 4. DB Volume/Path Drift

### Symptom
`sqlite3.OperationalError` or database lock errors indicating that host-native processes and container processes are competing for `swarm_ledger.db`.

### Remediation Protocol
Avoid host-native `uvicorn` and `ReadinessDaemon` runs. Force Compose-only supervisions. For local development testing, override database paths using:
```bash
export HOCHSTER_DB_PATH="/tmp/test_swarm_ledger.db"
```

### Gordon Query
> Gordon, analyze the volumes configuration in docker-compose.yml. Identify any host directory bind-mounts that could lead to concurrent locking conflicts on the SQLite swarm_ledger.db between the host and containers.

---

## 5. Container Healthcheck Failure

### Symptom
`docker compose ps` shows `has-api` or `has-worker` as `unhealthy`.

### Remediation Protocol
Inspect container logs:
```bash
docker compose logs has-api
docker compose logs has-worker
```
Verify the healthcheck cmd runs successfully inside the container:
```bash
docker compose exec has-api curl -f http://localhost:8000/api/v1/runtime-truth/state
```

### Gordon Query
> Gordon, the has-worker container healthcheck (pgrep -f ReadinessDaemon) is failing. Inspect the worker logs and container process trees to verify if the python daemon has exited or crashed due to db lock exhaustion.

---

## 6. Root Container Hardening

### Symptom
Security scanner flags containers running as root (UID 0).

### Remediation Protocol
Ensure all Dockerfiles include group/user creation for GID/UID 10001 and set `USER appuser` as the final directive.

### Gordon Query
> Gordon, scan Dockerfiles for has-api, has-worker, and has-tools. Verify that they do not run as root (UID 0) and enforce non-root security boundaries with UID 10001.
