# Gap Analysis — Agent Performance & Accountability Visuals

**Date:** 2026-07-14 · **Author:** HELM Council agent · **Evidence base:** live soak `HELM-SOAK-2H-20260714T204715Z` (156 dispatched tasks, hash-chained, `CONFIRMED_LIVE`)

## Method

Before proposing any visual, I inventoried what agent-attributed evidence the runtime **actually captures**. The rule: a dashboard is only allowed to show what the tamper-evident ledgers already prove. A per-agent chart over data we don't record would be exactly the fake-green theater HELM exists to prevent. Every field below was read directly from the live soak's `dispatch_ledger`, `result_envelopes`, and `verification_ledger` (all AU-9 hash-chained).

## What the runtime ALREADY captures (buildable, evidence-backed)

Every one of the 156 tasks carries, per execution, hash-chained:

| Dimension | Field(s) | Live values observed |
|---|---|---|
| **Executing worker** | `worker_id` | 156 distinct (e.g. `worker-62764-02ba`) — one per task |
| **Model/adapter** | `adapter` | `LOCAL_OLLAMA` ×156 (single adapter this run) |
| **Factory lane** | `factory` | HRF 39 · HCF 39 · HSF 39 · HASF 39 |
| **Independent validator** | `validator`, `validator_verdict`, `checks[]`, `failed_checks[]` | `validate_{hrf,hcf,hsf,hasf}` |
| **Verdict** | `verdict` | PASS 152 · **FAIL 4** (97.4% pass) |
| **Latency** | `started_at` → `completed_at` | min 5.1s · median 30.2s · max 171.6s · mean 33.2s |
| **Cost** | `cost_usd`, `cost_state`, `in_chars`, `out_chars` | `0.0` / **OBSERVED** (local = genuinely free, and *measured* not assumed); out 740–2776 chars |
| **Authority custody** | `authority_class`, `authority_decision_id`, `authority_status` | AUTONOMOUS, tied to a live authorization |
| **Scheduler attribution** | `scheduler_instance_id` | `sched-4b865252` (148) + `sched-59650434` (8) — a sequential restart |
| **Output integrity** | `artifact_sha256`, `artifact_chars` | content-addressed; 740–2776 chars |
| **Concurrency safety** | `fencing_token`, `lease_id` | monotonic tokens, per-task leases |

**The 4 failures are the accountability core:** all four are HASF tasks (`SOAK-HASF-2/12/14/25`) failing the *same* named check — `references_subject_module`. That is a specific, repeatable quality signal, and it proves the validators are catching real defects, not rubber-stamping. A HASF pass rate of 35/39 vs. 39/39 elsewhere is a true, defensible accountability finding.

## What is MISSING or would be theater to visualize

1. **Persistent agent identity.** `worker_id` is ephemeral — one per task execution. There is no long-lived "Agent Alice" to rank on a leaderboard over time. Honest accountability here is **per-adapter / per-factory / per-validator / per-scheduler**, not per-named-agent. Any "top agents" leaderboard would be fabricated continuity.
2. **Multi-adapter comparison.** Only `LOCAL_OLLAMA` ran. A grok-vs-gemini-vs-ollama quality/latency/cost comparison is a real capability but would render as a single bar until a mixed-adapter run exists. It must be labeled "1 adapter active this run," never drawn as if empty lanes were losers.
3. **Cost differentiation.** All `cost_usd = 0.0` (local). A cost-per-agent view is honest but flat until a paid adapter executes. Show it as `$0.00 OBSERVED`, never blank.
4. **Retry / recovery lineage.** These ledgers don't thread a failed task to its retry attempt. Whether the 4 HASF failures were retried is not answerable from this stream alone — a "recovery rate" metric would need a cross-referenced retry ledger first.
5. **Founder / human accountability events.** The founder-gate and authorization-decision actions live in a separate stream; this execution ledger only shows the `authority_decision_id` they produced. A full human-in-the-loop accountability timeline needs that second source joined in.
6. **Quality trend over time.** Per-validator, per-check pass rates *over the soak's duration* are computable (timestamps + `checks[]`) but not currently surfaced anywhere.

## The visual gap in the Command Center

Today's four views cover: **WALL** (factory topology), **FLOW** (aggregate KPIs), **CHAIN** (chronological AU-9), **CONTROLS** (NIST). None of them answers the accountability questions the evidence *can* answer:

- Which lane / validator / adapter is failing, and on which named check?
- What is the latency distribution, and who are the slow tails (171.6s max vs 30.2s median)?
- Did scheduler continuity hold (one writer) or hand off (the 148/8 split)?
- For any single task: the full **authority → dispatch → artifact(sha256) → validator verdict** custody chain, end to end.
- Real cost and throughput (in/out chars) per accountable dimension.

## Recommendation (what to build next)

A fifth Command Center view — **AGENTS / ACCOUNTABILITY** — backed by a new `/api/v1/helm/agents` endpoint that aggregates the live ledgers by the *accountable* dimensions only, plus a single-task custody-chain drill-down. Fail-closed: adapter with no runs shows "no runs this window," never a zero-loser bar; cost shows `$0.00 OBSERVED`, never blank; a broken chain forces the whole view to CONTRADICTED.

Specifically:
- **Accountability matrix** — factory × validator with pass/fail counts, the failing check named inline (HASF · `references_subject_module` · 4 fails).
- **Latency distribution** — histogram / p50-p95-max per factory, slow-tail tasks listed with their sha256.
- **Adapter panel** — per-adapter verdict rate, latency, cost, throughput; labeled with active-adapter count so a single-adapter run reads honestly.
- **Scheduler continuity strip** — instances over the run, flagging any handoff, with the AU-9 assurance that no two co-wrote (that's what makes the restart benign vs. split-brain).
- **Custody drill-down** — pick a task, see authority_decision_id → dispatch_digest → artifact_sha256 → validator checks, each a real hash from the chain.

Everything above is drawn from fields that already exist in the tamper-evident ledger. Nothing on the proposed view requires data we don't record — that is the line between an accountability instrument and a decorative one.
