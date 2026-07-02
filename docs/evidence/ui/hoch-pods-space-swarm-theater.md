# HOCH PODS Space Swarm Theater Evidence Log

This document records the design implementation and verification evidence for the **HOCH PODS Space Swarm Theater**.

## 1. Theater Layout & Components

The interface comprises the following regions:
- `#hoch-space-swarm-theater`: Root theater canvas container.
- `#hoch-space-command-core`: Central hub displaying HAS/HASF readiness and telemetry validation metrics.
- `#hoch-pod-launch-bay`: Grid docking bay for dormant and initializing pods.
- `#hoch-orbital-swarm-field`: Flex orbit overlay positioning active pods.
- `#hoch-agent-profile-drawer`: Live inspector panel displaying selected agent's config, owners, and models.
- `#hoch-pod-scorecard-layer`: Performance scorecard rendering trust scores, security levels, and node status.
- `#hoch-swarm-telemetry-rails`: SVG container rendering dynamic path animations connecting pods to central core.
- `#hoch-stale-quarantine-layer`: Quarantine overlay masking inactive/stale pods.

## 2. State-to-Animation Class Mapping

| Pod Runtime State | CSS Class | Visual Effect |
| :--- | :--- | :--- |
| DORMANT | `pod-docked-dormant` | Deep static glow, anchored |
| SUMMONING | `pod-ignition-summoning` | Orange pulsing energy ring |
| BOOTING | `pod-boot-scan` | Cyan sweep scanner animation |
| POLICY_CHECK | `pod-policy-shield` | Concentric purple/green energy pulse |
| MODEL_BOUND | `pod-model-ring` | Twin concentric orbit circles |
| TOOL_BOUND | `pod-tool-satellites` | Orbiting tool badges |
| EXECUTING | `pod-orbit-executing` | Rapid rotation, orbital path |
| EVIDENCE_WRITING | `pod-evidence-trail` | Pulsing green trail highlights |
| COMPLETE | `pod-mission-complete` | Steady Matrix green glow |
| BLOCKED | `pod-hold-pattern` | Warning alert blink, orbit freeze |
| FAILED | `pod-red-quarantine` | Crimson glow, quarantine chamber overlay |
| STALE | `pod-stale-freeze` | Blue-gray freeze, hover blocked |

## 3. Stale Quarantine Rules

If any of the telemetry files (`hoch_pods_runtime_state`, `hoch_execution_approval_queue`, `hoch_compute_node_health`, `hoch_pod_schedule`) are older than 600 seconds, the dashboard degrades the central core state to `DEGRADED`, breaks/dashes the telemetry rails, and overlays the affected pod capsules with a `STALE DATA QUARANTINE` indicator.
