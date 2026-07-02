# HOCH PODS Space Swarm Theater Design Doctrine

This document establishes the official design guidelines and visual specifications for the **Space Swarm Theater** layout within the HOCH Swarm Cockpit.

## 1. Visual Metaphor & Aesthetic Identity

- **Theme**: Deep Black Space Command Interface (Zero-G Mission HUD).
- **Background**: Starfield, deep charcoal panels (`#05070d`), subtle neon grid overlay, and faint celestial energy rings.
- **Accents**: Neon Cyan (`#22f6ff`), Cyber Purple (`#bd00ff`), Matrix Green (`#39ff14`), Warning Yellow (`#ffd700`), and Alert Red (`#ff2400`).
- **Layout**: 
  - A central **Space Command Core** representing HOCH HAS/HASF.
  - A **Launch Bay** displaying dormant or summonable pods as detailed capsules/cells.
  - An **Orbital Swarm Field** where active pods float in predefined orbit tracks around the central core.

## 2. Pod Capsule vs. Flat Card

Pods must never be rendered as standard grid dashboard cards. They must be rendered as **Launch Capsules / Orbital Agents** with:
- Circular or hexagonal pods featuring glowing neon borders.
- Rotating outer energy rings.
- Real-time status indicators (heartbeat pulse, trust score ring, telemetry connection rail).
- Satellite indicators showing attached Models and Tools.

## 3. State-Driven Cinematic Animations

All animations must correspond to the real-time runtime state of each pod:
- **DORMANT**: Stable, dark glow, docked in the Launch Bay.
- **SUMMONING**: Pulsing orange/plasma ring.
- **BOOTING**: Scanning animation (cyan sweep).
- **POLICY_CHECK**: Translucent glowing hexagonal shield layer.
- **MODEL_BOUND**: Double concentric cyan/green model orbit ring.
- **TOOL_BOUND**: Tiny orbiting satellite icons around the capsule.
- **EXECUTING**: Rapidly spinning neon ring, orbiting the core.
- **EVIDENCE_WRITING**: Green trails pulsing along the telemetry rail.
- **COMPLETE**: Matrix green steady glow, docked or orbiting.
- **BLOCKED**: Blinking alert red shield, holding position.
- **FAILED / QUARANTINED**: Red alert state, frozen in a quarantine chamber overlay.
- **STALE**: Frozen blue-gray state, animation suspended, warning overlay visible.

## 4. Anti-Fake Visual Governance

- **No Stale Animation**: Stale/degraded data must visually freeze the pod (suspend keyframes) and hide active orbits.
- **No Fake Green**: Active state is only green if the live telemetry actually indicates `COMPLETE`/`PASS`.
- **No Decorative Activity**: Idle pods must stay docked in the Launch Bay. Only pods with active schedules or executions may be in orbit.
