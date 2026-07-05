# HAS — Goal Definition + PERT-to-Goal Analysis (North-Star Planning)

* **Status**: Analysis for operator review. Grounded in repo artifacts; modeling assumptions labeled.
* **Captured (UTC)**: 2026-07-05
* **Sources**: `config/hoch_northstar_controls.json`, `config/hoch_pert_workstreams.json`,
  `config/goal_completion_contract.json`, `docs/mission/HAS_HASF_END_GOALS_LOCK.md`,
  live runtime-truth state store (`backend/swarm_ledger.db`).

---

## 1. What is the goal of HAS?

There are two complementary goal statements in the repo. They are not in conflict — one is
the *true north* (invariant direction), the other is the *measurable finish line*.

**True north (sealed 2026-06-26, `hoch_northstar_controls.json`):**
> Build a local-first, ephemeral, cybersecurity-hardened AI swarm cluster that can execute
> life, work, cyber, research, and humanity tasks while preserving operator control,
> evidence, approval gates, and full auditability.

Held up by 7 principles: Local-First (NS-01), Ephemeral Execution (NS-02), Operator Control
(NS-03), Full Auditability (NS-04), Evidence-First (NS-05), Cybersecurity-Hardened (NS-06),
Zero-Trust-within-Cluster (NS-07).

**Measurable finish line (`goal_completion_contract.json`, `HAS-HASF-FULL-BUILDOUT`):**
> Complete and monetize HAS/HASF with verified autonomous execution, live command center,
> secure relay, evidence ledger, and operator-trusted automation.

Its 10 completion criteria include: local runtime starts reliably; PERT dashboard shows
current truth; agents have owners/RACI; critical path visible; tests prove backend/relay/
doctrine/mission/UI/sustainment; no public 3012 exposure; no fake PASS/ONLINE; high-risk
actions gated; metrics show progress; Michael no longer copy/pastes routine commands.

**Architecture (`HAS_HASF_END_GOALS_LOCK.md`):** Michael (founder/approver) → **HAS**
(24/7 command-control) governs **HASF** (product factory) → **HELM** (autonomy runner) →
**AG** (execution adapters) → **Evidence Ledger**. Release + monetization stay
human-in-the-loop by lock.

So: *the goal of HAS is a 24/7 autonomous, operator-governed, evidence-disciplined swarm
that runs real work locally and can be trusted enough to monetize — where "trusted" is
defined by passing the evidence/approval gates, not by model confidence.*

---

## 2. PERT network (from `hoch_pert_workstreams.json`)

| ID | Activity | Dep | m (h) | Repo status | Controls-file reality |
|----|----------|-----|-------|-------------|-----------------------|
| P1 | Seal Ephemeral Swarm Doctrine | — | 2 | IN_PROGRESS | doctrine sealed; runtime enforcement → P2 |
| P2 | Skill Registry Runtime Gate | P1 | 4 | PENDING | SKILL-GATE-001 / RUNTIME-001 PENDING |
| P3 | Asset Trust Registry | P1 | 3 | PENDING* | **COMPLETE** (ASSET-TRUST-001, ZTA-001; commit d8004b3) |
| P4 | Port Hardening + LAN Gate | P3 | 3 | IN_PROGRESS | PARTIAL — 7 LAN ports + 5 unknown procs, no host firewall |
| P5 | QA Evidence Matrix | P1 | 2 | PENDING | QA-MATRIX-001 PENDING |
| P6 | PERT Dashboard UI | P5 | 3 | IN_PROGRESS | — |
| P7 | Google Drive Storage Policy | P3 | 2 | PENDING | STORAGE-001 PENDING |
| P8 | Cluster Worker Profiles | P3 | 3 | PENDING* | **COMPLETE** (CLUSTER-001; commit d8004b3) |
| P9 | End-to-End Audit + Go/No-Go | P2,P3,P4,P5,P6,P7,P8 | 4 | PENDING | E2E-AUDIT-001 / GO-NOGO-001 PENDING |

`*` **Contradiction found:** the PERT file marks P3 and P8 PENDING, but
`hoch_northstar_controls.json` marks their controls COMPLETE with commit evidence. The PERT
workstream statuses are stale. Per evidence discipline this is flagged, not silently
resolved — reconcile the two files.

---

## 3. Critical Path Method (corrected)

**Finding: the documented critical path `P1→P3→P4→P8→P9` is not a valid path.** P4 and P8
each depend only on P3; neither depends on the other, so they run in **parallel**. The naive
15h figure sums parallel branches. Correct CPM below (durations = repo point estimates).

Forward/backward pass (hours):

| ID | Dur | ES | EF | LS | LF | Slack | Critical |
|----|-----|----|----|----|----|-------|----------|
| P1 | 2 | 0 | 2 | 0 | 2 | 0 | ● |
| P3 | 3 | 2 | 5 | 2 | 5 | 0 | ● |
| P4 | 3 | 5 | 8 | 5 | 8 | 0 | ● |
| P8 | 3 | 5 | 8 | 5 | 8 | 0 | ● (co-critical) |
| P2 | 4 | 2 | 6 | 4 | 8 | 2 | |
| P5 | 2 | 2 | 4 | 3 | 5 | 1 | |
| P6 | 3 | 4 | 7 | 5 | 8 | 1 | |
| P7 | 2 | 5 | 7 | 6 | 8 | 1 | |
| P9 | 4 | 8 | 12 | 8 | 12 | 0 | ● |

**Project duration (CPM): 12h engineering-effort**, not 15h. Two co-critical branches:
`P1 → P3 → P4 → P9` and `P1 → P3 → P8 → P9`. Float: P2 = 2h, P5/P6/P7 = 1h each.

Network:
```
                 ┌── P2 (slack2) ─────────────┐
                 │                             ▼
P1 ─► P3 ─┬─► P4 ─────────────────────────► P9  (terminal = Go/No-Go)
  │       ├─► P8 ─────────────────────────►  ▲
  │       └─► P7 (slack1) ──────────────────┤
  └─► P5 (slack1) ─► P6 (slack1) ───────────┘
```

---

## 4. PERT probabilistic overlay (three-point, beta model)

Repo gives single point estimates; classic PERT uses te = (o + 4m + p)/6 with variance
σ² = ((p − o)/6)². **Modeling assumption (labeled, not from repo):** optimistic o = 0.7·m,
pessimistic p = 2.0·m (typical software padding for a solo/part-time operator).

Critical branch `P1→P3→P4→P9` (P8 branch identical duration):

| Act | m | te | σ² |
|-----|---|----|----|
| P1 | 2 | 2.23 | 0.188 |
| P3 | 3 | 3.35 | 0.423 |
| P4 | 3 | 3.35 | 0.423 |
| P9 | 4 | 4.47 | 0.751 |
| **Σ** | 12 | **13.4h** | **1.784** (σ = 1.34h) |

**Expected time-to-terminal ≈ 13.4 effort-hours, σ ≈ 1.34h.** ~84% confidence within ~14.7h;
~95% within ~15.6h. This is *effort*, not calendar — single part-time operator makes wall-clock
longer and adds the human approval waits that dominate P9.

Because P3 and P8 read as already COMPLETE in the controls file, the *remaining* critical
effort is smaller: finish **P4** (the real open security work) and feed **P9**. Adjusted
remaining critical effort ≈ P4(3.35) + P9(4.47) ≈ **~8 effort-hours**, plus P2/P5/P6/P7 which
must exist before P9 can run.

---

## 5. Reconciling PERT with live runtime-truth (the operational overlay)

The PERT above measures the **security-hardening build**. The live readiness gate measures
**operational truth**. They meet at P9.

Current live state (`FinalVerdict`): `BLOCKED`, readiness **50**, one binding cap:
`No active release GO source`. That GO source **is** PERT node **P9 (GO-NOGO-001)** — the
terminal audit gate. So:

> The single thing pinning readiness at 50 is the terminal PERT node. You cannot legitimately
> flip the GO until P9's predecessors (P2, P4, P5, P6, P7 — P3/P8 already done) carry evidence.

This is why manufacturing a `production_go_status=GO` signal is forbidden: it would fake the
terminal node without its predecessors, violating NS-05 (Evidence-First) and the committed
Evidence Discipline Baseline.

---

## 6. North-star planning: lead measures to move the terminal node

Treating the completion contract as the lag measure and the PERT feeders as lead measures,
the highest-leverage sequence to a *legitimate* GO:

1. **P4 — close port hardening (critical, real security debt).** Identify the 7 LAN-exposed
   ports + 5 unknown Python processes; configure the macOS host firewall; write
   `artifacts/qa/port_hardening_report.md`. Clears NS-06.
2. **P2 / P5 / P6 / P7 — feed P9.** Skill-registry runtime gate (P2, off critical but a P9
   predecessor), QA evidence matrix (P5), PERT dashboard truth (P6, also a contract item),
   storage policy (P7).
3. **Reconcile stale PERT statuses** (P3/P8) so the dashboard shows real truth — itself a
   completion-contract item ("PERT dashboard shows current project truth").
4. **P9 — run the end-to-end audit**, attach evidence, and only then take the operator GO
   decision through the release-authority path.
5. **Git hygiene** (separate 90-cap) per `GIT_HYGIENE_PLAN_clean_status_gate.md`.

Already banked this session (removes prior blockers on the path to P9): evidence-discipline
contract + fake-green guard (`8b0b649`), and the live heartbeat fix that cleared the 44h
stale-runtime blocker (`fc78bb3`) — satisfying the "local runtime starts reliably" contract
item.

---

## 7. One-line answer

**Goal of HAS:** a local-first, evidence-disciplined, operator-governed 24/7 AI swarm that
runs real work and earns enough trust — via passed audit gates, not model confidence — to be
monetized. **Distance to the terminal gate (P9 / release GO):** ~8 remaining critical
effort-hours of security + audit work (P4 → P9), gated behind a human GO decision, currently
the sole thing holding readiness at 50.
