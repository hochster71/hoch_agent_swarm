# HOCH PODS THEATER V6 Visual Baseline

* **Status**: `ACCEPTED VISUAL BASELINE`
* **Surface**: Moonshot UI
* **Canonical Local UI**: `http://127.0.0.1:8765/ui-moonshot`
* **Canonical Remote Private UI**: `http://100.87.18.15:8765/ui-moonshot`

---

## Executive Summary
This document defines and locks the visual baseline for the remote HAS/HASF operator cockpit: **HOCH PODS THEATER V6**. The layout and storyboard-driven execution model are accepted as the standard cockpit architecture.

---

## Layout and Core Zones
1. **Header**: HOCH PODS THEATER V6 command title and status pills.
2. **Central Storyboard Theater**: Interactive storyboard showing the cinematic agent spin-up and pod return cycles.
3. **Timeline Rail**: Movie-clip style timelines representing execution states.
4. **Live PERT Sidebar**: Dependency-driven workflow representation showing expected durations and critical paths.
5. **Mission Authority Panel**: Explicit state details (GO/NO-GO posture, active blockers, scorecard).
6. **Agent Queue**: Backlog of queued tasks and agents ready for intake.
7. **Evidence Console**: Live feed of generated evidence logs and trace references.
8. **Stale/Watchdog Panel**: Indicator flags for stale data, heartbeats, or connection states.

---

## Guidelines for Future Work
* **Preserve the visual style**: Maintain the dark xAI/cyber aesthetic with vibrant neon highlights.
* **No regression**: The old `8080` and `3012` surfaces are deprecated. Future UI modifications must build upon the `8765/ui-moonshot` codebase.
* **First-class representation**: Keep HELM (as primary execution brain) and Michael AI Model (as memory layer) highly visible in the cockpit.
* **Privacy boundaries**: Ensure public access remains blocked (`PASS_PUBLIC_BLOCKED`).
