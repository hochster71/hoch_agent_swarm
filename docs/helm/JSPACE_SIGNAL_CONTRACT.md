# J-SPACE Signal Contract — the law that keeps the Operations Bridge trustworthy

> **THE LAW (founder, 2026-07-18):** *Nothing on the screen exists unless it comes from the
> runtime.* Every pixel must trace to a real runtime signal — a file, a ledger row, a probe,
> a state object. If a signal does not exist, the layer renders **UNKNOWN**, not a plausible
> guess. This is "no fake green" applied to the interface.

A layer is only built once its signal provenance is one of:
- **REAL-NOW** — a real runtime signal exists today; safe to render.
- **NEEDS-INSTRUMENTATION** — the signal *could* be real but HELM does not emit it yet; we
  must emit it first, then render. Until then the layer shows UNKNOWN / NOT-INSTRUMENTED.
- **OFF-LIMITS** — the signal cannot be obtained truthfully (e.g., a model's internal
  reasoning). Never rendered, by design.

## The critical fact about the current runtime

The soak/executive-loop dispatch path is **prompt-in → text-out** to a local model, plus a
**deterministic validator verdict**. It emits: mission state transitions, dispatch
start/finish timestamps, validator checks, evidence artifacts, spend, cycle heartbeats,
resource samples. It does **NOT** emit: which files a model "read", edit/plan/test phases,
tool invocations per mission, token throughput, or model confidence. That boundary is what
decides each layer below.

## Provenance of every J-SPACE layer

| # | Layer | Status | Real signal source (or what's missing) |
|---|---|---|---|
| 1 | Galactic Map (runtime nodes) | **REAL-NOW** | `factory_registry.json`, capability routing in `soak_snapshot`, loop state in `loop_metrics.json` — already rendered in the cortex |
| 2 | Neural Traffic (pulse types) | **REAL-NOW** (most) | mission pulses ← `dispatch_ledger`/`soak_missions`; heartbeat ← `council_heartbeat.jsonl`; evidence ← `artifacts/factory/*`; waiting ← queue PENDING. *"Large context"* is NEEDS-INSTRUMENTATION (prompt size is knowable at dispatch but not currently logged per pulse) |
| 3 | Live Cognition (files read, edits) | **OFF-LIMITS** for the local-model path (no tool-use emitted). Only the **Claude Builder lane** (`guarded_build`) does real edits+tests — and it is founder-gated and not in the soak. Would be REAL only when that lane runs and emits its actions |
| 4 | Model Personalities (read/plan/edit/test bars) | **NEEDS-INSTRUMENTATION / partly OFF-LIMITS** | a single text-gen call has no phases. Meaningful only for an agentic tool-using lane that emits phase events; the soak has none |
| 5 | Tool Usage (fs/sqlite/git/pytest) | **PARTIAL** | HELM's OWN infra tool use is REAL (collector runs `git`+SQLite; verification runs `pytest`) — renderable. Per-*mission* tool use by local models does **not exist** |
| 6 | Token River (tokens/sec) | **NEEDS-INSTRUMENTATION** | Ollama's API returns `eval_count`/durations, but the subprocess dispatch discards them. Grounded once we capture token counts from the model response |
| 7 | Memory (working/retrieval/knowledge) | **NEEDS-INSTRUMENTATION** | `knowledge_engine` emits `KNOWLEDGE_INGESTED` events but is not exercised by the soak; no per-mission memory signal today |
| 8 | Confidence | **REFRAME** | model "confidence %" is OFF-LIMITS (not emitted, not calibrated). But **validator coverage** = fraction of `factory_validators` checks passed is REAL-NOW — render *coverage*, never invented confidence |
| 9 | Runtime Weather | **REAL-NOW** | flow ← throughput trend; latency ← p95; provider ← Ollama probe; queue ← depth; all from `soak_metrics`. "Context" maps to mem% or renders UNKNOWN |
| 10 | Mission Recorder (black box) | **REAL-NOW** | pure projection of the append-only, timestamped ledgers — the black box already exists |
| 11 | Time Machine (replay) | **REAL-NOW** | ledgers are timestamped + append-only → deterministic replay by timestamp |
| 12 | North Star / Founder Mode | **REAL-NOW** (ETA OFF-LIMITS) | `goal_state.json` + `executive_mission.json`. **ETA has no estimator → renders UNKNOWN**, never a fabricated "1h 42m" |
| ★ | Mission Constellation (moonshot) | **REAL-NOW** | every star = a real mission record; size ← duration, color ← real state (executing/completed/blocked/founder-wait/verified) |

## Build order (grounded first — the trustworthy core before the cognition layers)

1. **North Star strip** (12) — real goal/critical-path/founder-gate; ETA UNKNOWN. *(built)*
2. **Mission Recorder** (10) + **Time Machine** (11) — ledger projection + replay.
3. **Mission Constellation** (★) — the distinctive view; fully grounded.
4. **Runtime Weather** (9) and **Neural Traffic typing** (2).
5. **Validator-coverage** (8, reframed) and **HELM infra Tool Usage** (5).
6. **Token River** (6) — *first* instrument the dispatch to capture Ollama token counts, *then* render.
7. **Live Cognition / Model Personalities** (3,4) — only if/when an agentic tool-using lane
   runs and emits real tool/phase events; never fabricated for the text-gen path.

Anything in tiers 6–7 stays rendered as **NOT-INSTRUMENTED** until its signal is real.

## Addendum — the "six worlds" + navigation + HUD + Swarm Bus (founder, 2026-07-18)

The higher-ceiling spec: *navigable, replayable, evidence-backed; every object addressable,
every relationship traversable, every decision replayable; nothing decorative.*

| Feature | Status | Real signal source (or what's missing) |
|---|---|---|
| World 1 Universe | **REAL-NOW** | runtime nodes (built as the cortex) |
| World 2 Mission Space | **REAL-NOW** | Mission Constellation (built) — real mission records |
| World 3 Model Rooms | **PARTIAL** | mission/dispatch state + validator verdict are REAL; "files changed / current operation / tests" are **OFF-LIMITS** for the local text-gen path (only the Claude builder lane emits those) |
| World 4 Factory Floor | **REAL-NOW** | capability routing (in the side panel; dedicated screen easy) |
| World 5 Knowledge Galaxy | **NEEDS-INSTRUMENTATION** | per-mission retrieval/file-reads are not emitted by the text-gen path |
| World 6 Replay | **REAL-NOW** | append-only timestamped ledgers → deterministic replay/rewind |
| Operator HUD | **REAL-NOW** | dispatch rate, model count, factory count, evidence count, replay state — all real counters |
| Relationship navigation | **REAL for structural edges** | mission↔capability↔model↔evidence↔validator↔goal↔founder-gate are REAL. File-level edges (Claude→builder.py) are OFF-LIMITS (no tool-use telemetry) |
| **Swarm Conversation Bus** | **REAL-NOW** | the ACTUAL emitted events: lease ACQUIRED/DISPATCH_START/RELEASED/RECLAIMED/HELD_AUTHORITY, dispatch COMPLETED, validator PASS/FAIL, council cycle, governed event_bus (with `producer`). Rendered as event type + source — **never invented dialogue** like "Consensus reached" unless the runtime literally emits it |
