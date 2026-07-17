# HELM Executive Operating System — Visual Design Moonshot
### "Truth in Motion" — Design Authority Doctrine
> Founder vision (Michael Hoch, 2026-07-17). Status: FUTURE VISION — bake in when feasible (Phase 2/3 of the Command Center roadmap). This is the design authority for all HELM visualization work; it does not authorize decorative rebuilds now.

## The one defining principle: TRUTH IN MOTION
HELM is a living executive operating system, not a dashboard/website/sci-fi HUD. Every animation, glow, pulse, and transition MUST originate from actual runtime state. No decorative animation. No fake green. No meaningless motion. This is the visual expression of HELM's existing NO-FAKE-GREEN doctrine.

## The acceptance rule (permanent — apply to EVERY new visualization)
Before any visualization ships, it must answer:
1. **What operational question does this help the user answer?**
2. **What authoritative runtime event or evidence source drives it?**
3. **If the underlying event stopped occurring, would the visualization also stop?**

If #3 is "no" → redesign or remove. A visualization must be an honest representation of actual state, never an attractive approximation.

## Aesthetic north star
Feels like: Fleet Command · NORAD · NASA Mission Control · modern Cyber Operations Center · AI executive brain · mission-assurance platform.
NOT: consumer SaaS · gaming HUD · neon wallpaper · generic SOC dashboard.
Original identity — do NOT imitate Palantir / Iron Man / Star Trek / Marvel. HELM should be recognizable from one screenshot. Standing inside the OS, not looking at it.

## Digital Nervous System (the architecture behind the motion)
Every subsystem (Voice, Cyber, ConMon, Mission, Factories, Evidence, Agents, Research, Finance, Zero Trust, AI) PUBLISHES runtime events. Visualization SUBSCRIBES. Animation is therefore a consequence of reality, never decoration.

Canonical runtime events → visual consequences:
- TaskStarted / TaskCompleted → mission timeline + brain pathways
- AgentSpawned → swarm particle forms into a team
- EvidenceCollected / EvidenceVerified → Evidence River advances
- ThreatDetected / ThreatResolved → Cyber Terrain risk propagation
- MissionBlocked / MissionResumed → timeline halts / resumes
- FounderApprovalPending → golden executive beacon
- ModelRouted → AI Cognition routing pulse
- VoiceActivated → Executive Brain awakens, waveform emerges
- TelemetryUpdated → sparklines advance
- Runtime stale → brain regions DIM; Failed → FRACTURE; Unknown → stays DARK; Verified → illuminates

## 12 visual systems to design (per the brief)
1. Executive Brain (living neural cortex; subsystems branch from it)
2. Mission Command Bridge (holographic executive center, not flat dashboards)
3. Cyber Operations Center (identity/zero-trust/containers/apps/threat→mission-impact terrain)
4. Runtime Truth Engine (evidence powers the brain; unknown dark, stale fades, failed fractures, verified illuminates)
5. Evidence River (collection→validation→hash→verification→approval→archive, visibly flowing)
6. Mission Timeline (past fades, present glows, future translucent, founder gates gold, blocked red)
7. Agent Swarm (agents as particles forming teams: builder/research/cyber/QA/planner/auditor/reviewer)
8. Factory Galaxy (factories orbit HELM; live execution traffic + runtime health)
9. Knowledge Galaxy (research as stars/constellations; unknown space stays dark)
10. Zero Trust Sphere (identity→policy→evidence→authorization→execution decisions)
11. Mission Assurance Shield (layered: mission/cyber/AI/identity/supply-chain/evidence/runtime) — this is the HMAI, already built
12. Voice HELM (activation lights the brain + executive core + waveform)

## Deliverables (when Phase 2/3 begins)
Visual design system · motion language · animation rules · color system · typography · lighting · iconography · runtime-visualization framework · interaction framework · executive UX standards · redesigns (Cyber Command, Mission Bridge, Voice viz, Factory, Agent, Runtime Truth, Evidence) · executive design guide · component library · runtime-animation storyboard.

## Recommended implementation stack (for later)
React + WebGL + Three.js + React Three Fiber + Framer Motion + shaders, GPU-accelerated where appropriate. Every recommendation must improve executive understanding, operational clarity, and mission assurance. Never sacrifice truth for aesthetics.

## What already satisfies this doctrine TODAY (built, evidence-driven)
- `/executive` + HMAI (`backend/truth/hmai.py`) = Mission Assurance Shield #11, colored strictly by real pillar state (UNKNOWN stays dark/uncounted).
- Runtime Truth endpoints (`backend/truth/*`) = the evidence source the whole nervous system will subscribe to.
- Freshness system = the "stale fades" mechanic, real (`scripts/runtime_refresher.py` + liveness producer).
The foundation is already honest-by-construction; the moonshot is the visual layer on top of it.

## Message the visual identity must communicate
**Truth. Evidence. Governance. Mission.** Everything else is secondary.
