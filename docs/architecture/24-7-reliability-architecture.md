# Architecture: 24/7 Reliability Control Plane

## 1. Overview
The Hoch Agent Swarm 24/7 Reliability Architecture is designed around a **hybrid high-availability (HA-lite)** model. By utilizing a local primary host and a low-cost virtual private server (VPS) as a backup control plane, the system ensures maximum availability and zero queued task loss under a strict **$100/month budget**.

```
                         ┌──────────────────────────┐
                         │ Cloudflare Tunnel / DNS  │
                         │ secure access + routing  │
                         └────────────┬─────────────┘
                                      │
             ┌────────────────────────┴────────────────────────┐
             │                                                 │
┌────────────▼─────────────┐                    ┌──────────────▼──────────────┐
│ PRIMARY LOCAL HOST        │                    │ SECONDARY VPS FAILOVER       │
│ Mac / Dell / mini server   │                    │ $25-$60/mo, no GPU           │
│ Docker Compose            │                    │ Docker Compose               │
│ API + UI + Queue + DB      │◄────sync/backup────│ API + UI + Queue + DB        │
│ Local Model Gateway        │                    │ Degraded Mode / Control      │
│ Worker Pool               │                    │ Health Monitor               │
└────────────┬─────────────┘                    └──────────────┬──────────────┘
             │                                                 │
             └───────────────────┬─────────────────────────────┘
                                 │
                     ┌───────────▼───────────┐
                     │ Hoch Agent Swarm UI    │
                     │ Runtime Reliability Tab│
                     │ Finance / QA / PERT    │
                     └───────────────────────┘
```

---

## 2. Core Components

### A. Primary Host (Local Lab)
- **Role**: Active main node handling all LLM inference and agent tasks.
- **Compute**: Local GPU-enabled hardware for running Ollama/llama3.1.
- **Services**: Full UI/API web server, LiteLLM router gateway, Redis queue, and local worker pool.

### B. Secondary Host (VPS Failover)
- **Role**: Passive standby node hosting fallback services.
- **Compute**: Small, low-cost CPU-only VPS instance.
- **Services**: Light UI, failover routing control, and health monitor heartbeats.

### C. Persistent Queue (`hoch-queue`)
- **Role**: Redis container running with `appendonly yes` config.
- **Benefit**: Ensures tasks are written to disk, preventing task loss on container restart.

---

## 3. Self-Healing & Promotion Mechanisms
- **Watchdog Daemon (`watchdog_24_7.sh`)**: Runs on both hosts to verify API health every 15s. Triggers `docker compose restart` on failures.
- **Failover Heartbeat (`failover_check.sh`)**: VPS checks primary host health. If down for > 120s, updates status registry to promote the VPS to active control mode.
- **Cloudflare Tunnel Routing**: Outbound-only tunneling mitigates ISP issues, routing traffic dynamically without public port exposure.
