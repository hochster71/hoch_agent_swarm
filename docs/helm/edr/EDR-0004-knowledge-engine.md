# EDR-0004 — Knowledge Engine (design spec + v1 implementation)

- **Status:** PROPOSED design → **v1 (Governed Retrieval) IMPLEMENTED by Builder, pending Auditor verification.** The v1 scope below is built as new, non-frozen modules with tests; it does not change the frozen verification target. Independent (Auditor) sign-off and a green test run are still required before this is claimed conformant — see **Implementation status** at the end.
- **Author (Builder):** Claude · **Date:** 2026-07-17
- **Reviewers:** Auditor (Grok)
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` — Article I layer 5 (Knowledge Engine, currently **PLANNED**). This EDR designs that layer; it does not add or change architecture.

## Context
Today HELM's architectural intent still lives partly in conversations. The Constitution fixed the architecture; the **Knowledge Engine fixes organizational memory** so every worker — Claude, ChatGPT, Grok, Ollama, LM Studio — retrieves the **same governed knowledge** instead of depending on prior chats. This is the largest remaining constitutional gap.

## Decision — what the Knowledge Engine is
The authoritative, governed source of durable organizational knowledge. **Knowledge belongs to HELM, never to an individual model.** It is a *runtime projection* for readers and a *governed, evidence-linked store* for writers.

### First responsibility (v1 scope): Governed Retrieval — NOT long-term memory
The Knowledge Engine's first and smallest valuable responsibility is **Governed Retrieval**:
giving every worker a shared, authoritative answer to governance-provenance questions,
so nothing depends on hidden conversation history. v1 must answer:
- **Which Constitution article governs this?**
- **Which EDR changed this behavior?**
- **What verification evidence supports this implementation?**
- **Which factories depend on this subsystem?**
- **What controls map to this runtime component?**

**Explicitly de-scoped from v1:** general "long-term memory," free-form recall, and
conversational history. Those are later increments, not the first deliverable. Starting
with Governed Retrieval keeps the Knowledge Engine small, authoritative, and immediately useful.

### Corpus (authoritative content)
Constitution · EDRs · runbooks · cyber mappings (NIST/RMF/Zero-Trust) · mission history · lessons learned · factory specifications · runtime documentation · verification artifacts.

### Design principles (inherit Constitution Article II)
- **Derived/provenanced, never invented** — every knowledge item traces to a source file + commit/event; no unsourced "facts".
- **Append-with-provenance** — updates are versioned; history is retained (replayable).
- **Retrieval is read-only** — workers query; they do not mutate truth through it.
- **Cross-model neutrality** — one corpus, one retrieval contract; no model's private context is authoritative.
- **No fake green** — a missing or stale document is reported as such, never fabricated.

### Proposed shape (to be implemented under this EDR after verification)
1. **Store** — the existing governed files are the source of record (`docs/`, `coordination/`, EDRs, evidence); the Knowledge Engine **indexes** them, it does not replace them.
2. **Index** — a manifest of documents with metadata (path, kind, version, provenance, freshness). Semantic/embedding index is a **later increment** requiring an embedding provider (local model preferred — founder/credential gate).
3. **Retrieval API** — read-only `GET /api/v1/helm/knowledge?q=…&kind=…` returning ranked documents with provenance + freshness; keyword/manifest retrieval first, semantic second.
4. **Ingestion** — governed: a document enters the corpus via a transaction/event (Event Bus), so the timeline records what knowledge changed and when.
5. **Cross-model access** — every worker's Standard Session Flow step "Load Constitution / Load EDRs" resolves through this API, so all providers read identically.

## Scope boundaries
- **In:** corpus definition, provenance model, retrieval contract, manifest index, ingestion-via-event design.
- **Out (later increments / gated):** embeddings + semantic search (needs an embedding model — local Ollama/LM Studio preferred, founder-gated); write-back automation; UI panel in the Executive Operations Center.

## Acceptance criteria (for the eventual implementation)
- Every returned item carries provenance (source path + version/commit) and freshness.
- Retrieval is read-only; ingestion emits an Event Bus event.
- Absent/stale documents report honestly (UNKNOWN/STALE), never fabricated.
- A worker can retrieve the Constitution + applicable EDRs through one API call.

## Verification
Auditor reviews this design for conformance to Articles I, II, and X before implementation is authorized. Build occurs in Phase B after the Phase D independent audit, per founder sequencing.

## Implementation status (v1 — Governed Retrieval)
Builder has implemented the v1 scope as **new, non-frozen modules** that import only frozen read-surfaces (`governance_engine`, `event_bus`) and index existing governed files. Nothing in the frozen verification target changed.

| Artifact | Path | Role |
|---|---|---|
| Knowledge Engine | `backend/helm_runtime/knowledge_engine.py` | policy-bound manifest + read-only retrieval + governed ingestion (emits `KNOWLEDGE_INGESTED`) |
| Read-only HTTP API | `backend/helm_runtime/knowledge_api.py` | `GET /api/v1/helm/knowledge`, `/knowledge/manifest`, `/knowledge/session-load` |
| Router mount | `backend/helm_live_api.py` | mounts the knowledge router next to the runtime bridge (fail-open on import only) |
| Tests | `tests/helm_runtime/test_knowledge_engine.py` | 16 regression + negative tests (secret denial, read-only-no-events, role rejection, founder-gated Constitution ingestion, honest UNKNOWN/STALE) |

How each acceptance criterion is met:
- **Provenance on every item** — `KnowledgeItem.provenance` carries `source_path` + git `commit` (`None` when untracked, never faked); freshness carries `mtime`/`age`/`status`.
- **Retrieval read-only; ingestion emits an event** — `retrieve`/`build_manifest`/`governed_load_constitution_and_edrs` never write or emit; the sole state-changing path, `ingest`, is governance-checked (role + founder gate) and publishes one Event Bus event. `test_retrieve_is_read_only_no_events` locks this.
- **Absent/stale reported honestly** — missing → `UNKNOWN`, aged past the window → `STALE`; no-match query returns `status="UNKNOWN"` with empty results, never a fabricated answer.
- **Constitution + applicable EDRs in one call** — `governed_load_constitution_and_edrs()` / `GET /api/v1/helm/knowledge/session-load`.
- **Policy fails closed** — `RetrievalPolicy` denies any secret-shaped or out-of-corpus path, so a query can never surface a credential.

**De-scoped from v1 (unchanged):** embeddings / semantic search (needs a founder-gated local embedding model), write-back automation, and the Operations Center UI panel.

**Test-harness remediation (2026-07-17, Builder):** the frozen `event_bus.tail_events` binds `path=EVENTS_PATH` as a def-time default, so the test's `monkeypatch.setattr(eb, "EVENTS_PATH", temp)` redirected event *writes* (`publish_event` reads the global at call-time) but not event *reads* — the three event-assertion tests would have read the real `coordination/events/helm_events.jsonl` instead of the temp bus. Fixed in the **non-frozen test only** (`tests/helm_runtime/test_knowledge_engine.py`) by also pinning `tail_events` to the temp bus via `functools.partial`; the frozen module is untouched. This makes the event assertions read the bus under test.

**Not yet claimed (NO-FAKE-GREEN):** this is Builder work awaiting (1) the Auditor's adversarial pass for conformance to Articles I/II/X, and (2) an evidenced green run of the test suite (`bash scripts/run_knowledge_tests.sh`), which is founder-approval-gated in the current session. Until both land, N5_KNOWLEDGE stays **PARTIAL/PENDING**, not DONE.
