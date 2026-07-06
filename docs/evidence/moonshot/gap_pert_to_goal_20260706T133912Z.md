# GAP ANALYSIS + PERT TO GOAL — HAS / HASF / BRAIN

- Captured (UTC): 2026-07-06 13:39
- Author: Claude (analysis), for operator review
- Repo commit (REVISION): `68a4bf83abe61e17623f68b85764da5d7a238a53`
- Discipline: evidence-sourced; every current-state number cites a repo file. Forward estimates
  labeled **[Claude estimate]** are not repo data.

---

## 0. Which GOAL?

Three overlapping "goal" definitions live in the repo. They are not contradictory but they are not
yet reconciled — that is itself a finding (see Gap G-0).

| # | Source | GOAL as stated |
|---|--------|----------------|
| 1 | `moonshot_control_plane_contract.json` → contract.north_star | "Complete and monetize Hoch Agent Swarm / HASF with verified autonomous execution, live command center, secure relay, evidence ledger, and operator-trusted automation." (goal_id `HAS-HASF-FULL-BUILDOUT`) |
| 2 | `fresh_pert_gap_analysis.json` → terminal node `GOAL` | "App Live on Stores" — the concrete, monetizable terminal deliverable |
| 3 | `HAS_BRAIN_CONVERGENCE_MOONSHOT.md` → North star | A self-improving prompt brain that converges on the provably-best prompt per task class, outcome-bound |

This analysis anchors the **terminal GOAL = "App Live on Stores"** (definition 2, the most concrete),
treats definition 1's 10-point completion list as the **acceptance criteria**, and treats the BRAIN
convergence loop (definition 3) as the **enabling capability track** that must reach outcome-binding
(Phase M2) for the monetized product to optimize against real results rather than a proxy.

---

## 1. Current state (all sourced)

| Metric | Value | Source |
|--------|-------|--------|
| Goal complete | **95%** | control_plane snapshot → metrics.percent_goal_complete |
| Readiness score | **90 / 100** (HIGH confidence) | control_plane → readiness.score |
| Goal state | **DEGRADED_UNTIL_BLOCKERS_CLOSED** | moonshot audit → blocker triage |
| Overall PERT status | **CONDITIONAL_GO** | fresh_pert_gap_analysis.json |
| Tests | **42 passing / 0 failing** | control_plane → metrics |
| Evidence coverage | **100%** | control_plane → metrics |
| Blocked tasks | **4** (all high-risk, approval-gated) | control_plane → approval_queue |
| Fake-status / public-exposure violations | **0 / 0** | control_plane → guardrails |
| BRAIN convergence | gen **440**, mean **75.48**, **CONVERGED** (last_gain 0.0, ε=0.5) | convergence_status.json |
| BRAIN mode | **M0 mechanical** (improver_online, no live LLM) | convergence_status.json + moonshot doc §5 |

**Reading of it:** the infrastructure/command-and-control layer is essentially done and clean (95%,
0 violations, 100% evidence, all infra PERT tasks W1–W4 completed). The remaining 5% and the entire
monetization track are gated by **external / founder actions**, not by more agent engineering.

---

## 2. Gap analysis (current → GOAL)

Severity: **P0** = blocks the critical path now · **P1** = blocks a phase gate · **P2** = quality/risk.

| ID | Capability | GOAL state | Current state | Gap | Sev | Owner |
|----|-----------|-----------|---------------|-----|-----|-------|
| G-0 | Goal definition | One reconciled GOAL + acceptance set | 3 overlapping definitions | Reconcile into one contract; declare terminal node | P1 | Operator |
| G-1 | LLM credentials (K1) | Live keys loaded | `BLOCKED_FOUNDER_ACTION` | Provision OpenAI/Anthropic keys → unblocks Critic seat + Rung-2 + BRAIN M1 | **P0** | **Michael** |
| G-2 | BRAIN live loop | M1: live generate + adversary across mesh | M0 mechanical only, "converged" at proxy | Turn on live generation once K1 lands | P0 | Brain agent (post-K1) |
| G-3 | Outcome binding | M2: fitness bound to real mission outcome | Not started; verifiability = rubric proxy | Wire prompt→execution→result into score | P1 | Brain agent |
| G-4 | Demand validation (G1) | Gate PASS with real signal | PENDING | Run G1 demand checklist (needs real-world data) | P0 | Growth agent + Michael |
| G-5 | Differentiation + packaging (A4) | Store-ready package past diff gate | PENDING | Depends A3 build | P1 | HASF agent |
| G-6 | Store submission (SUB→GOAL) | App live on Apple/Google | PENDING | Depends A6; gated by K2–K4 | P0 | Michael + agent |
| G-7 | Founder external accounts | Apple Dev, App Store Connect, signing, SSH, secrets | K2–K6 BLOCKED_FOUNDER_ACTION | 5 founder setup items, external wall-clock | **P0** | **Michael** |
| G-8 | Working tree clean | Committed + tagged evidence bundle | `GOAL-BLOCKER-GIT-DIRTY` (MEDIUM) | Stage evidence bundle, commit before tag | P1 | Agent (auto-safe) |
| G-9 | High-risk approvals | T3 cleared | 4 items queued (stripe/secret/public_port/deploy) | Michael T3 review | P1 | **Michael** |

**Two immovable roots:** G-1 (K1 keys) and G-7 (Apple/founder accounts). Nothing on the monetization
critical path or the BRAIN live loop moves until these clear. They are wall-clock/external, not agent
compute — this is the crux the repo's minute-based PERT understates (see §3, View B).

---

## 3. PERT analysis to GOAL

Critical path (sourced, `fresh_pert_gap_analysis.json`):

```
K1 → H1 → H2 → G1 → G4 → A2 → A3 → A4 → A6 → SUB → GOAL
 │    ✓PASS ✓PASS  ── all downstream PENDING ──         ▲
 └─ BLOCKED_FOUNDER_ACTION (root)                    App Live on Stores
```

### View A — repo PERT (sourced, agent-compute minutes)
From `fresh_pert_gap_analysis.json` → pert_summary:

| Estimate | Minutes | Hours |
|----------|---------|-------|
| Optimistic (O) | 120 | 2.0 |
| Most likely (ML) | 480 | 8.0 |
| Pessimistic (P) | 1440 | 24.0 |
| **Expected (TE = (O+4ML+P)/6)** | **580** | **9.7** |
| σ = (P−O)/6 | 220 | 3.7 |
| Stated confidence | 95% | — |

95% band ≈ TE ± 1.96σ ≈ **150–1010 min (2.5–16.8 agent-hours)**. This is the *engineering-work*
envelope **assuming founder/external actions are instantaneous** — which they are not.

### View B — wall-clock to a live monetized app [Claude estimate]
The repo model omits external latency. Realistic three-point on the gating externals:

| Gating item | O | ML | P | Nature |
|-------------|---|----|----|--------|
| K1 API keys | 0.5 h | 2 h | 8 h | Founder, self-serve |
| K2 Apple Developer enrollment | 24 h | 48 h | 2 wk | External approval (Apple) |
| K3/K4 App Store Connect + signing | 2 h | 6 h | 24 h | Founder + agent |
| G1 demand validation (real signal) | 1 d | 3 d | 10 d | Needs real-world data, not compute |
| A3 build | 8 h | 24 h | 80 h | Agent |
| App Store review (SUB→GOAL) | 24 h | 48 h | 72 h | External (Apple review) |

Wall-clock TE to "App Live on Stores" ≈ **1.5–3 weeks**, dominated by Apple enrollment + review and
the demand gate — **not** by the ~10 agent-hours in View A. Treat View A as "how much agent work is
left" and View B as "when can it actually ship."

### Slack / non-critical (sourced, control_plane pert_cpm)
Infra tasks carry real slack — W2 slack 5.83 min, W3 slack 66.66 min — and are all `completed`, so
they no longer sit on the path. The path is now entirely the K→G→A→SUB monetization chain.

---

## 4. Anti-gaming flag (from the moonshot's own discipline)

`convergence_status.json` reports **CONVERGED at mean 75.48**, but this is **M0 mechanical** — scored
against the rubric proxy, not real mission outcomes. Per `HAS_BRAIN_CONVERGENCE_MOONSHOT.md` §3.3 and
§4.4, a champion is only GOAL-true once the `verifiability` dimension binds to **real downstream
outcome**. So "converged" today means "stopped improving against the proxy," not "reached the GOAL."
**Do not read 75.48/CONVERGED as goal attainment.** Outcome-binding (G-3 / Phase M2) is what converts
this from a scoreboard into progress toward the monetization GOAL.

---

## 5. Recommended sequence (safe-first)

Sourced next actions (`fresh_pert_gap_analysis.json` → next_3_safe_actions) + founder gates:

1. **[Michael, P0]** K1 — provision OpenAI/Anthropic keys. Unblocks Critic seat, Rung-2 eval, BRAIN M1. Single highest-leverage move.
2. **[Michael, P0]** K2 — start Apple Developer enrollment **today** (longest external wall-clock; start it in parallel with everything else).
3. **[Agent, P1, auto-safe]** G-8 — stage the evidence bundle and commit to clear `GOAL-BLOCKER-GIT-DIRTY`; lifts goal_state out of DEGRADED.
4. **[Michael, P1]** G-9 — T3 review the 4 high-risk approval items (stripe / secret / public_port / deploy).
5. **[Agent+Michael, P0]** G1 demand validation checklist — begin real-signal collection (days of wall-clock; start early).
6. **[Agent, post-K1]** G-2 → G-3 — flip BRAIN to M1 live loop, then wire M2 outcome binding.
7. Build → differentiate/package → release runner → submit (A3→A4→A6→SUB→GOAL).

**One-line takeaway:** the system is 95% built and clean; the GOAL is gated almost entirely by two
founder/external roots — **K1 (keys)** and **K2 (Apple enrollment)** — plus the demand gate. Start
those wall-clocks now; agent work left is only ~2.5–17 hours, but real ship date is ~1.5–3 weeks.

---

## Sources (repo files)

- `docs/moonshot/HAS_BRAIN_CONVERGENCE_MOONSHOT.md` (North star, phases M0–M3, anti-gaming spine)
- `has_live_project_tracker/data/moonshot_control_plane_contract.json` (GOAL contract, completion definition)
- `docs/evidence/moonshot/moonshot_audit_20260702T193448Z.md` (blocker triage + live API snapshot: metrics, guardrails, pert_cpm)
- `has_live_project_tracker/data/fresh_pert_gap_analysis.json` (critical path, pert_summary, blockers, next actions)
- `data/prompt_brain/convergence_status.json` (BRAIN generation, mean_score, CONVERGED state)
- `has_live_project_tracker/data/human_approval_queue.json` (K-track founder credential gates K1–K2+)
- `REVISION` (repo commit)
