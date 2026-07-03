# HAS/HASF 24/7 Remote Runtime Requirements

This document specifies the remote runtime and daemonization constraints for services operating on `HOCH-200`.

---

## 1. Process Model & Services
The remote runtime must be managed as systemd service units:
* `helm-runner.service`: Executes the main AI task loop.
* `has-agent-dispatcher.service`: Orchestrates active agent registry and task mapping.
* `hasf-product-factory.service`: Drives the candidate backlog pipeline.
* `has-runtime-watchdog.service`: Monitors process state, performs auto-recovery, and publishes UI telemetry.

---

## 2. Infrastructure Invariants
* **Start on Boot**: All services must configure `WantedBy=multi-user.target` to survive server restarts.
* **Restart on Failure**: Service units must define `Restart=always` with `RestartSec=10` to automatically recover from unhandled runtime exceptions.
* **Uptime Visibility**: Logging must output directly to systemd journald so it is readable via `journalctl`.
* **Port Isolation**: No public ports must be exposed. Communication to control endpoints must run strictly over Tailscale.
* **Founder Release Guard**: Any production promotions or release state changes are locked behind manual founder authorization gates.
