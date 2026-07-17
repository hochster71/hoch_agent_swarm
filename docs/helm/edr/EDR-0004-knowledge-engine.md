# EDR-0004 — Knowledge Engine (design spec; no build)

- **Status:** PROPOSED (design only). Implementation deferred (Phase B, after independent verification).
- **Author (Builder):** Claude · **Date:** 2026-07-17
- **Reviewers:** Auditor (Grok)
- **Governed by:** `HELM_CONSTITUTION_v1.0.md` — Article I layer 5 (Knowledge Engine, currently **PLANNED**). This EDR designs that layer; it does not add or change architecture.

## Context
Today HELM's architectural intent still lives partly in conversations. The Constitution fixed the architecture; the **Knowledge Engine fixes organizational memory** so every worker — Claude, ChatGPT, Grok, Ollama, LM Studio — retrieves the **same governed knowledge** instead of depending on prior chats. This is the largest remaining constitutional gap.

## Decision — what the Knowledge Engine is
The authoritative, governed source of durable organizational knowledge. **Knowledge belongs to HELM, never to an individual model.** It is a *runtime projection* for readers and a *governed, evidence-linked store* for writers.

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
