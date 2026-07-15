# Epic Fury 2026 — TestFlight Test Information

Paste these into App Store Connect → your app → **TestFlight → Test Information**
(or apply them with `scripts/goal/asc_write_testinfo.py --apply`, below).

---

## Beta App Description  (testers see this)
Epic Fury 2026 is a dark-mode, military HUD-style tactical intelligence dashboard. Monitor
a real-time tactical feed of intel reports with confidence metrics, a live AI-agent roster
grid (status, logs, telemetry), and an interactive DMO canvas simulation. Built for AI
researchers, simulation operators, and mission planners who want an integrated tactical
command-center UI. This beta validates real-time feed reliability, dashboard performance,
and the subscription flow.

## Feedback Email
michael.b.hoch@gmail.com   *(change to a dedicated support address if you prefer)*

## What to Test  (per build — the "What's New to Test" field)
- **Real-time tactical feed** — intel reports stream in; confidence metrics render correctly.
- **AI Agent Roster Grid** — agent cards update live (logs, telemetry, metrics) without stalls.
- **DMO Canvas Simulation** — the Hormuz Strait scenario map is interactive and smooth.
- **Subscription / paywall** — the paid-access path (Stripe / RevenueCat): purchase, restore,
  and that gated features unlock correctly.
- **General** — dark-mode legibility, layout on your device size + orientation, and
  reconnect behavior after losing network.

## Beta App Review Information  (required before EXTERNAL testing)
- **Contact**: Michael Hoch — michael.b.hoch@gmail.com
- **Demo account**: ⚠️ REQUIRED if the app is login-gated — provide a working test
  username/password so Apple's beta reviewers can reach the gated tactical feed and the
  subscription flow. Add this before you enable external testing.
- **Notes for review**: The DMO simulation depicts a fictional/analytical scenario for
  simulation and research purposes only.

---
*Internal testers (up to 100 on your team) do NOT require Beta App Review — you can start
internal testing as soon as the build is processed. External testing requires the Beta App
Review Information above.*
