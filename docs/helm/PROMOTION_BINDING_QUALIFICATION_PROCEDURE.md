# Promotion-binding qualification — isolated-worktree procedure (v1)
**2026-07-20 · council-ratified architecture · PREPARED, execution founder-gated**

The pre-freeze qualification proved unattainable on the live main worktree: three attempts, three
INVALID classifications (external kill; own goal-loop validator pytest ×2), while the suite itself
replicated `1897 passed / 0 failed / 11 skips / rc 0` three times. Those replications are
**engineering observations, not qualification evidence.** The binding run happens where exclusivity
holds by construction: an isolated worktree at the frozen SHA, which no daemon references.

## Ordered gates (each fails closed; none may be skipped)

1. **T10 manifest reviewed** — every entry in `coordination/goal/T10_CURATION_MANIFEST_DRAFT.json`
   carries a founder-approved disposition; no REVIEW entries remain.
2. **Curated candidate committed** — per commit unit, explicit path staging only
   (staged-paths ≡ unit manifest; never `git add -A`); buildable at each unit boundary.
3. **Candidate SHA frozen** — founder act. Requires: launchd writers paused, runtime mutations
   restored, clean porcelain, `git diff --check` clean (council's nine freeze steps).
4. **Isolated worktree from that exact SHA** — `run_promotion_binding_qualification.sh <SHA>`:
   refuses reuse of an existing worktree dir; verifies detached HEAD == frozen SHA and clean status.
5. **Ratified baseline copied + hash-verified** — byte-compare against
   `expected_residue_baseline_sha256_pin` in `burndown_record.json`; mismatch aborts (a re-pin,
   if the T10 outcome changes expectations, must be a new founder-ratified record first).
6. **No daemon writers on the isolated path** — `pgrep -f <worktree>` empty AND no LaunchAgent
   plist references the path. (Daemons are configured against the main repo path only.)
7. **Exclusive qualification executed** — the v2.2 controlled launcher inside the worktree:
   own `.venv` (uv sync --frozen), own TMPDIR (⇒ own sqlite path via conftest derivation), own
   lockfile, logs, and evidence dir; ancestry-aware foreign-pytest monitor; baseline/HEAD/index/
   code-path integrity hashes start→end; `-rs` skip identities; `pytest_return_code` stamped.
8. **Artifacts bound to frozen SHA and tree hash** — `promotion_binding` block written into the
   artifact (frozen sha + `HEAD^{tree}` + worktree path), then repatriated to the main evidence
   chain with the raw log preserved under `originals/`.

## Acceptance (mechanical, `evaluate_full_suite_acceptance.py`)

`PASS_CLEAN_CANDIDATE` requires ALL of: execution controls verified · rc 0 · collection accepted ·
failure-set equality (post-re-pin: empty) · skip count AND identity match · worktree_clean true
(⇒ `promotion_binding_eligible` true). Anything else is REJECTED or
INVALID_ENVIRONMENT_NOT_CONTROLLED — never negotiated upward.

## What this run does NOT do

It does not sign the promotion manifest, does not emit GO (only
`scripts/goal/verify_promotion_manifest.py` may ever emit GO), does not close
N3-VERDICT-BINDING-GAP (that needs the T4 re-verification with a properly bound verdict:
candidate SHA + tree sha embedded, `SCOPE: COMPOSED_RUNTIME` attested, no method disclaimer),
and does not advance any founder gate. It produces exactly one thing: the regression-evidence
artifact the promotion manifest may then cite.

## Review 2 — freeze readiness (definition, council-tightened 2026-07-20)
Review 2 answers exactly one question — "is anything here capable of invalidating the
promotion-binding qualification?" — and may not begin until its INPUTS are frozen:
candidate contents identified (T10 dispositions complete, incl. adjudication of any
out-of-band commits) · candidate manifest finalized · qualification procedure version
identified (this document + launcher version hash) · baseline reference identified
(pinned sha) · review artifacts immutable for the run. Reviewing a moving target is not
review. Review 3 is then explicitly adversarial: attempt to DISPROVE promotion readiness;
inability to produce HOLD evidence is what strengthens the promotion case.

## Candidate Identity Record (council directive, 2026-07-20)
`coordination/goal/CANDIDATE_IDENTITY_RECORD.json` is the canonical definition of what is being
qualified. At freeze it is finalized (frozen SHA + manifest sha + its own sha256 pinned); from
that moment every qualification artifact, N3 verification, review, and the promotion manifest
must cite its identity_record_sha256. An artifact citing no identity record binds to nothing.
