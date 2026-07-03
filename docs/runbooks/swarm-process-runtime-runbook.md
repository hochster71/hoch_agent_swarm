# Swarm Process Runtime Runbook (Operations Guide)

This runbook outlines standard procedures for operating, accessing, backing up, and troubleshooting the Hoch Agent Swarm control plane.

---

## 🚀 1. Core Services & Port Mappings

The Swarm Control Plane is composed of three interconnected services:

| Service | Port | Directory | Tech Stack |
|:---|:---:|:---|:---|
| **Main Cockpit Dashboard** | `3000` | `frontend/` | Vite Dev Server |
| **Live Project Tracker** | `3001` | `has_live_project_tracker/` | Node.js Server |
| **FastAPI Backend Core** | `8000` | `backend/` | FastAPI / Uvicorn |

---

## 🔒 2. Basic Authentication & Secrets

The Live Project Tracker on port `3001` enforces Basic Authentication.

### Default Credentials
* **Username**: `admin`
* **Password**: `Qn9UFv4yL1OccTxokKRiMg1d63WqzufD7ZEKihub61r4r8zS`

### Credential Overrides
Credentials can be customized by creating a secrets file at:
`~/.hoch-secrets/has-tracker.env`

Add the following environment variables:
```env
TRACKER_USER=admin
TRACKER_PASSWORD=your-secure-password-here
TRACKER_PORT=3001
```

---

## 📁 3. Database Checkpointing & Backups

The SQLite ledger database acts as the source of truth for swarm states, tasks, and audit logs.

### Triggering a Snapshot
1. Navigate to the **Settings** view on port `3001` (`http://localhost:3001/`).
2. Click **📁 Trigger Database Backup Snapshot**.
3. The server will clone the ledger and output a status report:
   `SUCCESS: Backup database checkpoint created at backups/has_ledger_checkpoint_YYYY-MM-DD.db`

---

## 🔄 4. Daemon & Process Control

### Starting the Dev Servers
To spin up all services locally in dev mode:
```bash
# Start backend FastAPI server
uv run uvicorn backend.main:app --port 8000 --reload

# Start frontend dashboard (port 3000)
npm --prefix frontend run dev

# Start project tracker (port 3001)
node has_live_project_tracker/server.js
```

### Viewing Logs
* **FastAPI Backend Logs**: Located at [`logs/has_runtime.log`](file:///Users/michaelhoch/hoch_agent_swarm/logs/has_runtime.log).
* **Project Tracker Logs**: Located at `has_live_project_tracker/tracker.log`.

---

## 🛠️ 5. Troubleshooting Port Collisions
If ports are already in use, run the following commands to locate and terminate the stale processes:
```bash
# Find and terminate port 3000 process
lsof -i :3000
kill -9 <PID>

# Find and terminate port 3001 process
lsof -i :3001
kill -9 <PID>
```
