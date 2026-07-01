# HOCH PODS Visual Design Authority

This document defines the visual layout, aesthetics, token system, and interaction guidelines for the HOCH PODS command surface. It acts as the visual spec and design authority for HOCH compute environments.

## 1. Design Principles & Aesthetics
- **Cinematic Cyber Command Surface**: The layout takes visual inspiration from SpaceX launch dashboards and modern industrial telemetry screens (xAI, Tesla).
- **Glassmorphism**: Dark semitransparent panels layered on top of an ultra-dark background with subtle neon grid overlays.
- **Local-First & Zero-Trust Posture**: Clear distinction between trust levels, zones, and security postures. Default deny boundaries must be visually apparent via protective borders and glowing containment indicators.
- **No Fake Green**: Telemetry truth must be absolute. Stale, degraded, offline, or unverified states must render in amber, orange, or red. Never map stale data to a healthy green state.

## 2. Palette and Color Tokens
- **Core Background (`--hoch-bg`)**: `#05070d` (Midnight black)
- **Panel Primary (`--hoch-panel`)**: `rgba(8, 13, 26, 0.92)`
- **Panel Secondary (`--hoch-panel-2`)**: `rgba(10, 18, 34, 0.86)`
- **Cyber Cyan (`--hoch-cyan`)**: `#22f6ff` (Primary focus / active compute indicator)
- **Tech Blue (`--hoch-blue`)**: `#2b7cff` (Verified information / local secure nodes)
- **Smoke Purple (`--hoch-purple`)**: `#a855f7` (Summoning / model state routing)
- **Safety Green (`--hoch-green`)**: `#39ff88` (Fully compliant / verified operations)
- **Warning Amber (`--hoch-amber`)**: `#ffb020` (Degraded / policy check queue)
- **Critical Red (`--hoch-red`)**: `#ff3b5c` (Blocked / quarantined compute)
- **Muted Slate (`--hoch-muted`)**: `#8b9bb4`
- **Focus Border (`--hoch-border`)**: `rgba(34, 246, 255, 0.26)`

## 3. Pod Capsule Lifecycle States & Animations
Every pod in the pod theater is rendered as a 3D-feeling capsule with a glowing core and state-specific ambient aura:

| State | CSS Class | Animation Behavior |
|-------|-----------|--------------------|
| **DORMANT** | `pod-state-dormant` | Low pulse, sleeping grey/blue core |
| **SUMMONING** | `pod-state-summoning` | Purple particle plume rise effect |
| **BOOTING** | `pod-state-booting` | Vertical cyan scanline & concentric rings |
| **POLICY_CHECK** | `pod-state-policy-check` | Golden lock symbol pulse |
| **MODEL_BOUND** | `pod-state-model-bound` | Orbiting neural pathway circles |
| **TOOL_BOUND** | `pod-state-tool-bound` | Orbiting utility dot satellites |
| **EXECUTING** | `pod-state-executing` | Cyan active compute pulse |
| **EVIDENCE_WRITING** | `pod-state-evidence-writing` | Document flow cascade stream |
| **COMPLETE** | `pod-state-complete` | Steady green glow aura |
| **BLOCKED** | `pod-state-blocked` | Red/amber flashing containment bounds |
| **FAILED** | `pod-state-failed` | Slow red breathing quarantine glow |

## 4. Cockpit Layout Zones
The HOCH PODS area must be structured using the following semantic elements:
1. **Header Rail (`#hoch-pods-header-rail`)**: System status, global authority stats, and freshness timers.
2. **Compute Rail (`#hoch-pods-compute-rail`)**: High-performance local node matrix.
3. **Topology Map (`#hoch-pods-topology-map`)**: Visual zero-trust flow of telemetry nodes.
4. **Pod Theater (`#hoch-pods-theater-panel`)**: Interactive capsule control grid.
5. **Hardening Guide (`#hoch-pods-hardening-panel`)**: Mandatory operations rules.
6. **Compliance Mapping (`#hoch-pods-compliance-panel`)**: Zero trust control matrix.
7. **Scheduler (`#hoch-pod-scheduler-panel`)**: Workload planner table & scheduling rationale.
