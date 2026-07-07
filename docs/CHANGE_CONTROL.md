# HOCH Change Control — the ONE source of truth

This document is authoritative. If anything else in this repo claims to be a "baseline",
"no-drift policy", "checksum register", "seal", "track lock", or "integrity manifest",
it is a **deprecated observer** — historical evidence only, NOT the source of truth.

## Why this exists
The repo accumulated ~71 drift/baseline/seal artifacts that *observed* drift but never
*enforced* it, so every fix cycled back. Monitoring without enforcement is not change
control. This replaces all of them with one git-anchored, fail-closed board.

## The model (standard configuration management)
- **Baseline** = a git tag. Blob SHAs are the immutable checksum register.
  Current: see `has_live_project_tracker/data/baseline_tag.txt`.
- **Audit trail** = git history. Immutable, dated, already complete. Do not duplicate it
  into JSON that itself drifts.
- **Change board** = `scripts/baseline_guard.py` + the `.git/hooks/pre-commit` gate.
- **Enforcement** = the gate blocks commits that regress an invariant;
  `baseline_guard.py --revert` snaps unapproved code back to the baseline.

## The only three operations
```bash
python scripts/baseline_guard.py            # BOARD: PASS / DRIFT + exact deltas (code + config + runtime)
python scripts/baseline_guard.py --revert   # REJECT unapproved code drift (snap to baseline)
# APPROVE a new baseline (deliberate, human):
git tag hoch-baseline-$(date -u +%Y%m%dT%H%M%SZ) && \
  echo <tag> > has_live_project_tracker/data/baseline_tag.txt
```

## Invariants the board enforces (extend deliberately, keep short)
Config: `execution_posture == DOORSTEP`, `allow_provider_api_calls == false`,
`allow_founder_gated_execution == false`, no fabricated `ACTIVITY_POOLS` fleet theater.
Runtime: exactly one listener on `:8000` (no orphan shadowing launchd), one `ollama serve`.

## Rules
1. Autonomous agents may PROPOSE changes; they may not move the baseline. Only an
   approved re-tag moves "known good".
2. No `--no-verify` commits to guarded paths without a recorded reason.
3. Deprecated observers are not to be treated as truth. Archive, don't consult.
