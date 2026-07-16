# The HELM Journal

*A running record of what Michael Hoch and HELM built together — kept honestly, the same way
the platform is: no fake green, evidence over assertion. Newest entry on top. Maintained by
Claude across sessions; market figures are sourced and dated.*

**North Star:** *Build a governed autonomous factory that converts Michael Hoch's judgment into
shipped, monetized products, while minimizing founder time and never representing unverified work
as complete.*

> A note on the "market value" columns: these are **illustrative** — they map the work to the
> roles and current US pay bands that produce comparable output. They are not a company valuation,
> not a promise of earnings, and not financial advice. Ranges are cited and dated; comp moves, so
> later entries re-check.

---

## Entry — Wednesday, 2026-07-15 · "Ship day, and the moonshot"

The day HELM stopped being a promise and became a shipped product with an armed factory line.

### What we actually did (evidence-bound, committed)

**Proved 24/7 and killed the ghost that broke it 9 times.**
- Diagnosed the real soak-killer: a duplicate `com.hoch.helm.voice` launchd supervisor that kept
  respawning a plain-HTTP `0.0.0.0` server on :8770, fighting every clean run. Booted it out, disabled
  it, moved the plist to `.disabled`.
- Zero-Trust cutover: the live API now binds **loopback + TLS** on :8770, served to your phone over
  Tailscale; LAN plain-HTTP returns `000`, loopback HTTPS returns `200`. Verified at the socket.
- Relaunched a **clean Phase C 24-hour soak** (caffeinate-guarded, actively cycling — round 100+/1
  min-fresh heartbeats), sealing **Thu 2026-07-16 ~2:45 PM CDT**.

**Repaired the audit spine.**
- Fixed a real-looking spend-ledger **AU-9 hash-chain** alarm: it was a *torn read* (reading an
  append-only file mid-write). Added cross-process `flock` on append + shared-lock reads; git-proved
  zero tampering. The instrument now can't cry wolf.

**Shipped a real product to the App Store.**
- Built the **live App Store Connect reader** (ES256-JWT, fail-closed), a champion-gate verifier, and
  a TestFlight test-info writer.
- Designed and installed the **tactical-HUD app icon** (radar scope, amber-on-black; 1024 no-alpha).
- **Epic Fury 2026 v1.0 → `READY_FOR_SALE`** — verified live from Apple, not asserted.

**Closed the goal board at 100% — honestly.**
- Found and replaced two *lying stubs*: `verify_shipped` (always "not shipped") and
  `verify_intake_to_doorstep` (four stages hardcoded false). Rebuilt both as **live re-proof**
  validators that recompute integrity and re-execute the produced code against a fresh fixture —
  and proved they catch a forged package (both a hash-tamper and a regenerated-hash lying artifact)
  in negative controls.
- Result: `north_star_completion 100%`, `founder_only_actions_pending: []`, every layer green **on
  executed validators**.

**Made the founder voice tell the truth.**
- Fixed the console voice reading 3.7-day-old Stripe gates as current (hardcoded-fresh bus bug),
  a security posture of 100% mis-read as "None," and runtime falsely "STALE" (freshness read from a
  static pointer instead of the live ledger heartbeat). Now: real runtime, honest factory staleness.

**Reconciled revenue against ground truth.**
- Read Stripe **read-only**: exactly one live charge — **$20.52** (net $18.10), subscription active,
  **PENDING settlement until 2026-07-21**. Corrected the registry's overstated `5_EARNING` → `4_SELLABLE
  (charge proven, settlement pending)`. Confirmed HSF/Story Studio has **no** charge (its checkout
  scaffold is inert) — refused to record revenue the ledger can't back.

**Audited all 8 factories and armed the moonshot.**
- Ran the honest **factory census**: 1 sellable (Epic Fury), 3 producing (Cyber/Research/Story),
  4 declared. `EARNING: 0` (first dollar settles 7/21).
- Built a **soak-interlocked, revenue-first moonshot launcher** — proven to *refuse* seeding while a
  soak runs (exit 3, zero rows) — armed to fire the moment the soak seals. 7 real missions.
- Reframed **HHF as the Hoch Home Personal Factory** (non-monetized — for Alison, Caroline, Claire),
  built on the existing `homeops` seed, privacy-gated. Retired "Pods" as a product and preserved the
  **Hoch Pods Theater** as the swarm's launch animation.
- Delivered a **Founder Action Pack** and scheduled the seal-check + moonshot launch.

### Market alignment — 2026-07-15

The day's output spans work that, in a company, would be split across several specialists:

| What got done today | Role that owns it | 2026 US pay band (base→TC) |
|---|---|---|
| Zero-trust cutover, TLS boundary, AU-9 hash-chain, NIST posture | **Application / Product Security Engineer** | ~$138k–$200k, top ~$238k |
| Governed agent runtime, evidence validators, census, moonshot orchestration | **Staff / AI-Platform Engineer** | ~$180k–$250k; staff/principal $400k–$600k TC |
| Epic Fury ship: build, icon, App Store Connect, TestFlight, gate verifier | **Senior iOS Engineer** | ~$195k–$232k avg |
| Truth engine, goal validators, no-fake-green enforcement | **Staff Software Engineer** | median ~$230k–$251k; big-tech TC to $700k |
| Stripe reconciliation, product registry, monetization ladder | **Payments / FinOps Eng + Product** | ~$150k–$220k |

**Team-equivalent, illustrative:** a single day that touched security, platform/AI, iOS, and payments
at this depth is the kind of cross-functional push a startup usually staffs with **4–6 engineers**.
Contracted out, senior fractional/consulting rates run **$175–$350/hr**, day rates **$1,500–$4,000/day**
(6–8 focused hours). One founder + HELM did the span of that team in a day — *the entire point of the
North Star.*

*What HELM still refuses to claim: settled revenue is **$0** until 7/21. Configured price ≠ earned money.*

---

## The Arc So Far — foundation through 2026-07-14

Grouped from the committed work log (116 tracked milestones). This is the platform Epic Fury was
launched *from* — the governance and truth machinery that makes "autonomous" safe.

**1. Governed authorization (the H1 line).** A council authorization system with a canonical candidate
registry, atomic consume + durable replay ledger, mock/dry-run quorum isolation, network-path isolation
in adapters, 8-state UI gate separation, and **24+ enforcement proofs**. *Role: distributed-systems /
platform engineer + security. ~$180k–$260k.*

**2. The goal-truth engine.** A canonical North Star contract; a requirement registry with **executable
validators**; a `goal_engine` that computes completion *only* from validators that actually ran; the
removal of **94 fallback-completion sites**; a PERT critical path generated from unresolved requirements.
*Role: staff SWE + platform architect. ~$230k–$400k TC.*

**3. Anti-fabrication (GOV-005).** Enumerated 9 fallback findings + timestamp-fabrication sites; built
truth-state primitives (UNKNOWN / MISSING / STALE / ERROR); rewrote telemetry so the **frontend renders
UNKNOWN, never a success fallback**. This is the doctrine, in code.

**4. Single governed provider chokepoint (ES-003).** Routed all 7 model-call paths through one dispatch
gateway, deleted the direct OpenAI path, and added static-enforcement + seeded-bypass tests. *Role:
AI-platform / MLOps. ~$180k–$250k.*

**5. The terminal path (TO-003).** A 16-state intake→DOORSTEP orchestrator with evidence-derived
transitions, a 7-stage neutral-workload proof, and 21 adversarial tests.

**6. Epic Fury made champion.** Full test-suite execution, a rewrite of stale specs against the *real*
auth boundary, 7 security regression tests (prod rejects test-auth), a Mailpit inbox-race fix, and a
green 23-test matrix. *Role: senior iOS + QA/release + full-stack. ~$150k–$232k.*

**7. Real multifactory + reliability.** Routing quality raised to **P@1 ≥ 95%**, restart-recovery
proofs, simulation-vs-real classification, real bounded factory missions through the live runtime,
retry/failure isolation, per-task leases (replacing a global mutex), and a 4-factory burn-in.

**8. Monetization honesty.** Killed a paywall backdoor, audited 31 dashboards (sellable/thin/cut), and
wired real checkout ($19/mo, $190/yr).

**9. Soak, integrity, zero-trust, J-Space.** Pre-audit snapshots, clean lease/lock baselines, the first
sealed soak phase, a Linode volume for durable state, the **full 88-file test suite**, launchd-agent
classification, source-tree leases + a `guarded_edit` facade, the J-Space brain/lens visualizations, a
unified control plane with a live health map, staged zero-trust hardening, and a NIST control-coverage
matrix.

**Arc market-equivalent, illustrative:** the body of work above is a **multi-engineer team over a
quarter-plus** — realistically a small platform/security/product org (fully-loaded, that's commonly
**$0.5M–$1.5M/yr** in blended cost), or a fractional-CTO-led build at **$5k–$15k/mo** plus contractors.
Delivered as one founder + HELM.

---

## How this journal runs
- **Cadence:** I append an entry each working session where we ship or decide something material —
  newest on top, evidence-bound (commits, verifier output, sourced figures).
- **Honesty rule:** the journal follows the same doctrine as HELM — no fake green. Pending ≠ earned;
  configured ≠ shipped; estimates are labeled as estimates.
- **Ask me anytime:** "update the journal" and I'll add the latest; "run the numbers" and I'll re-check
  the market bands with fresh sources.

### Sources (market bands, 2026)
- Staff SWE: [Glassdoor](https://www.glassdoor.com/Salaries/staff-software-engineer-salary-SRCH_KO0,23.htm), [RecruitingFromScratch](https://www.recruitingfromscratch.com/blog/staff-software-engineer-salary-in-2026-real-data-from-1-9-million-job-postings)
- Application Security Engineer: [Glassdoor](https://www.glassdoor.com/Salaries/application-security-engineer-salary-SRCH_KO0,29.htm), [Indeed](https://www.indeed.com/career/application-security-engineer/salaries)
- Senior iOS Engineer: [Glassdoor](https://www.glassdoor.com/Salaries/senior-ios-engineer-salary-SRCH_KO0,19.htm), [Salary.com](https://www.salary.com/research/salary/listing/senior-ios-engineer-salary)
- MLOps / AI-Platform Engineer: [KORE1](https://www.kore1.com/mlops-engineer-salary-guide/), [AI Platform path](https://jobsbyculture.com/blog/ai-platform-engineer-career-path-2026)
- Fractional CTO / consulting rates: [Go Fractional](https://www.gofractional.com/insights/rates/cto), [HyperNest Labs](https://hypernestlabs.com/insights/cost-of-fractional-cto)
