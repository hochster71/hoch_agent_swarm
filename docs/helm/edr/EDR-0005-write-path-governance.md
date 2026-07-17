# EDR-0005 — Write-Path Governance (single-writer commits; Git records, not coordinates)

- **Status:** PROPOSED (policy). Implementation of the Git service deferred to Runtime phase (after independent verification).
- **Author (Builder):** Claude · **Date:** 2026-07-17
- **Reviewers:** Auditor (Grok)
- **Governed by:** `HELM_CONSTITUTION_v1.0.md`. Operational governance of the write path; adds no architectural layer.

## Context
This session repeatedly hit `.git/HEAD.lock` / `.git/index.lock` contention. Root
cause is structural, not incidental: **multiple actors (Builder, Auditor,
Orchestrator, background daemons) were writing to one `.git` concurrently**, and Git
was drifting toward being the *coordination bus* between agents. Both are anti-patterns
for an operating system. Founder direction (2026-07-17): establish single-writer
discipline and keep runtime coordination out of version control.

## Decision

### 1. Single-writer commit discipline
**Exactly one process is authorized to perform Git write operations** (`add`, `commit`,
`rebase`, ref updates). All other actors — Builder, Auditor, Orchestrator, and every
daemon — **produce proposals, artifacts, and evidence; they do not commit.** The
authorized committer is the **Mission Runtime** (or a designated Git service it owns).

### 2. Git records approved changes; it does not coordinate agents
```
Mission Runtime  →  Evidence Store  →  Verification  →  Git Commit
```
Coordination happens over the **Event Bus + Mission Runtime** (proposals, OCC, events).
Git is the **append-only record of approved changes** — never the synchronization
mechanism between models. A worker never `git commit`s to signal another worker; it
emits an event / submits a proposal.

### 3. Operational rules (in force immediately, before the Git service exists)
- Only one terminal/agent performs commits at a time. Close parallel agent terminals
  (the ChatGPT/Grok CLIs) before committing; do not run concurrent `git add`/`commit`.
- Daemons that mutate state (liveness/refresher/producers) **emit events or write
  evidence files — they must not create commits.** Audit any daemon that commits and
  convert it to event/evidence output.
- **Manual lock removal is an EXCEPTION, fail-closed — never routine.** Before deleting
  `.git/HEAD.lock` or `.git/index.lock`, verify (a) no live `git` process AND (b) **no
  process owns either lock file** (`lsof <lock>`). If either is held, do NOT delete —
  investigate. Recovery is the guarded `scripts/fix_git_governance_commit.sh`, not an
  ad-hoc habit. Once the authorized Git writer exists, stale locks should not occur and
  manual deletion should approach zero.

## Consequences
- **Positive:** lock contention disappears (one writer); Git history becomes a clean
  approved-change log; coordination lives where it belongs (runtime), making the system
  replayable and auditable.
- **Work implied:** a small **Git service** owned by the Mission Runtime that serializes
  commits from validated proposals (Runtime-phase implementation, after verification).
- **Interim cost:** until that service exists, the discipline is enforced by convention +
  the recovery script.

## Acceptance criteria (for the eventual Git service)
- Concurrent commit attempts from non-authorized processes are refused, not raced.
- Every commit corresponds to an approved proposal + evidence (traceable).
- No daemon creates commits; daemons emit events/evidence only.

## Verification
Auditor confirms the write path: single authorized committer, Git-as-record (not bus),
no daemon commits, clean lock behavior. Implementation follows the independent audit.
