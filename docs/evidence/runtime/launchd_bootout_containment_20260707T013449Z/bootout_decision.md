# Launchd Bootout Containment Decision

Problem:
High-risk writer processes respawned even after launchctl disable/stop.

Root chain:
hoch_daemon.sh -> hoch_cadence.sh -> brain_cadence.sh -> recursive_optimizer

Observed parent:
hoch_daemon.sh PPID=1, indicating launchd ownership/reparenting.

Decision:
Bootout exact LaunchAgent plists for the respawning jobs, then kill the running process group.

Exact targets only:
- com.hoch.daemon
- com.hoch.brain.cadence
- com.hoch.phase56.burnin

Do not touch:
- com.hoch.has.pert-server
- com.hoch.ollama.tailscale
- backend API
- canonical UI
- LM Studio
- Ollama
- Apple jobs
- HOCH-200 relay read-only visibility
