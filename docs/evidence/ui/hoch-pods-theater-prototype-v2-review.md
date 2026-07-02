# HOCH PODS Theater Standalone Visual Prototype v2 Review

This document presents the visual review and audit baseline for the **HOCH PODS Theater v2 (Image-Anchored)** prototype, constructed in strict compliance with Founder Michael Hoch's visual authority.

---

## Visual Design Details & Approach

### 1. Locked Cinematic Composition
- **Base Shell**: The prototype renders the exact high-fidelity reference image (`docs/design/assets/hoch-pods-theater-reference.jpeg`) as the base visual layout shell, ensuring pixel-perfect spacing, typography, density, and color composition.
- **Cinematic Stage**: Centered on a full-black page with a target viewport scaling of `1536x1024` with no cropping.
- **Filters**: Ambient CRT-style scanlines and dynamic animated film grain noise are overlaid on top of the container to add motion and depth.

### 2. Transparent Interactive Overlay Regions
The following 17 storyboard panels and sections are mapped via absolute-positioned transparent layers over the base shell:
- **Frames 1 to 11**: The horizontal lifecycle steps at the bottom (`DORMANT`, `SUMMONING`, `BOOTING`, etc.).
- **Frame 12 (DESTINATION LANES ACTIVE)**: Mapped to the connecting lanes/arrows between Model, Runtime, and Tool zones.
- **Frame 13 (POD STATUS OVERVIEW)**: Mapped to the Operator Zone status card.
- **Frame 14 (DATA FLOW VISUALIZATION)**: Mapped to the Management Zone command center.
- **Frame 15 (EVIDENCE ARCHIVE)**: Mapped to the Evidence Zone ledger card.
- **Frame 16 (SYSTEM CONFIRMATION)**: Mapped to the Compliance Mapping panel on the right.
- **Frame 17 (MISSION READY)**: Mapped to the bottom signature/operational seal.
- **Agent Spin Up Variations & Skill Card Animation Flow**: Mapped to the corresponding vertical zones.

### 3. Dynamic Real Data Binding
- Overlays pull and poll status continuously from `/api/pert/data`.
- If telemetry is stale (e.g. elapsed time > 600s), the system activates the quarantine layer, freezes all hover animations, and marks all mapped panels as **STALE** with red/amber pulsing overlays.

---

## Proof & Verification Links

- **Prototype URL**: `http://localhost:8765/hoch-pods-theater-prototype-v2`
- **Design Authority Reference**: [hoch-pods-theater-reference.jpeg](file:///Users/michaelhoch/hoch_agent_swarm/docs/design/assets/hoch-pods-theater-reference.jpeg)
- **Visual Capture**: [hoch-pods-theater-prototype-v2-current.png](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/ui/screenshots/hoch-pods-theater-prototype-v2-current.png)
- **Side-by-Side Review Diagram**: [hoch-pods-theater-reference-vs-current.png](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/ui/screenshots/hoch-pods-theater-reference-vs-current.png)

---

## Safety Confirmation
- **No Commit**: Verified. No git commit commands have been run.
- **No Tag**: Verified. No git tag commands have been run.
- **No Push**: Verified. No git push commands have been run.
