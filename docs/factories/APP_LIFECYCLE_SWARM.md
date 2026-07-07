# App Lifecycle Swarm — reusable per-application team (HASF)

**Purpose.** Every app HASF ships gets its own **lifecycle swarm**: a standing team of agent
roles that carries the app from launch through its entire life — updates, growth, compliance,
support — running on the HAS harness (tier router → verify gate → fail-closed cost cap) under
DOORSTEP + the change-control board. Building the app was a project; keeping it alive and growing
is a *process*. This doc is the template each app instantiates.

Instantiated for: **Epic Fury 2026** (`com.epicfury.dashboard`). Copy per new app.

---

## Roles (the swarm)

| Role | Owns | Autonomy |
|---|---|---|
| **Release Engineer** | build number bump, archive, upload, changelog, phased rollout | SAFE up to upload; **submit = founder-gated** |
| **ASO Analyst** | keyword/title/subtitle iteration, screenshot A/B, category fit | SAFE (drafts); publish = founder review |
| **Content/Intel Curator** | freshness of the app's live data (intel feed, threat meter) | SAFE within source-authority allowlist |
| **Reliability Watch** | crash/ANR triage, OS-version bumps, dependency + CVE patching | SAFE fixes behind verify gate; risky = staged |
| **Growth Analyst** | funnel metrics, trial→paid, churn, pricing experiments | SAFE analysis; price/paywall change = founder |
| **Support Responder** | App Store review replies, support inbox drafts | SAFE drafts; send = founder review |
| **Compliance Sentinel** | privacy manifest, agreement renewals, age-rating drift, export | SAFE monitoring; declarations = founder |

Every role's work flows through the same harness: cheap/local model first, acceptance-gate
verification, escalate only real failures, hard monthly cost cap. Nothing merges without the gate;
nothing legal/financial executes without the founder (DOORSTEP).

---

## Lifecycle phases & recurring tasks

**0. Pre-launch (one-time, mostly founder gates)** — pricing, category, age rating, App Privacy,
content rights, screenshots. *These are the items blocking Epic Fury right now.*

**1. Launch window** — submit build, monitor review status, respond to any rejection, phased
release, day-1 crash watch, ratings prompt tuning.

**2. Steady-state (recurring, autonomous on the loop)**
- Weekly: ASO keyword scan, review-reply drafts, funnel/churn report, crash triage.
- Per iOS release: SDK/dependency bumps, rebuild + TestFlight regression, CVE patch sweep.
- Per content cycle: intel-feed freshness + source-authority audit (app-specific).
- Monthly: pricing/paywall experiment readout, compliance/agreement expiry check.

**3. Growth pushes (event-driven)** — timed to news cycle / demand spikes: feature-flagged
"crisis mode," push-notification campaigns, PR/asset drops staged for founder send.

**4. Sunset (if needed)** — deprecation notice, data-export, store removal — all founder-gated.

---

## How it runs on the existing harness

- **Queue:** `has_live_project_tracker/data/hoch_loop_queue.json` gets the app's recurring tasks,
  each with a machine-checkable `acceptance` spec and a `difficulty` for the tier router.
- **Autonomy:** `scripts/hoch_loop.py` grinds SAFE tasks at ~$0 (local models); founder-gated
  categories (`blocked_release`, `blocked_monetization`, …) are STAGED to
  `founder_handoff_queue.json` and surfaced on the live dashboard (`:3012/brain`).
- **Cadence:** scheduled tasks (weekly/monthly/per-iOS-release) enqueue the recurring items.
- **Governance:** all code changes pass the change-control board (baseline tag + pre-commit
  invariants); cost bounded by `AGENT_MONTHLY_CAP_USD`.

---

## Instantiation checklist (per new app)

1. Copy this template; set bundle id, ASC app id, source-authority allowlist.
2. Add the app's recurring tasks to the loop queue with `acceptance` + `difficulty`.
3. Add release lanes (`asc-preflight.sh`, `appstore-finalize.sh`, auto-increment Fastfile).
4. Register founder gates (submit, pricing, legal declarations) as DOORSTEP items.
5. Point the live dashboard's factory node at the app's telemetry.

The app-build factory (HASF) produces the app once; the **lifecycle swarm keeps it earning** —
which, per the ROI analysis, is where the real return is (retention + ASO + distribution, not
one-time launch).
