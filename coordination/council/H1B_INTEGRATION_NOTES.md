# H1B — integration notes for AG IDE

## Why two files are not in this commit

`backend/main.py` and `frontend/src/components/helm/topdown/HelmCouncilView.tsx` both
carry **another lane's uncommitted work** in this shared worktree (`main.py` was already
`M` with ~1,360 unstaged insertions when this lane started; `HelmCouncilView.tsx` is still
untracked). Committing either file wholesale would drag that lane's WIP onto the Claude
branch. The edits below are **applied and live in the worktree** — they are simply not
committed here. AG IDE owns their integration.

Everything else (registry, gate, packet generator, tests, evidence artifacts, candidate
reclassification) is committed and self-contained.

---

## P0 DEFECT FIXED — backend resolved the active candidate to a TEST package

`backend/main.py`, `GET /api/v1/helm/council/state` resolved the H1 candidate by
lexicographic sort of a directory listing:

```python
sorted([d for d in os.listdir(...) if d.startswith("HELM-H1-CANDIDATE-")])[-1]
```

`"T" > "2"`, so `HELM-H1-CANDIDATE-TEST-H1-RUN-BCAFCE1E` sorted **last** and won. The
endpoint was therefore publishing a founder decision statement — authorization ID, package
ID, combined SHA-256 — derived from a `NON_EXECUTABLE_TEST_PACKAGE`. A founder signing what
that panel displayed would have been authorizing a test artifact. It also derived the
authorization ID by string-splitting the directory name, yielding `HELM-H1-AUTH-RUN-BCAFCE1E`.

**Fix:** the endpoint now reads `coordination/council/h1b_founder_decision.json` — the
reconciled packet — and never re-derives identity from a directory listing.

```python
# H1B founder-decision packet — single source of truth for candidate identity.
# Regenerate with: python3 scripts/council/generate_h1b_packet.py
h1b_packet = _safe_load("coordination/council/h1b_founder_decision.json")
...
"h1_candidate": h1b_packet.get("h1_candidate", "UNKNOWN"),
"h1_package_id": h1b_packet.get("package_id"),
"h1_authorization_id": h1b_packet.get("authorization_id"),
"h1_combined_authorization_sha256": h1b_packet.get("combined_authorization_sha256"),
"h1_superseded_candidates": h1b_packet.get("superseded_candidates", []),
"h1_non_executable_test_packages": h1b_packet.get("non_executable_test_packages", []),
"package_integrity": h1b_packet.get("package_integrity", "UNKNOWN"),
"credential_matrix": h1b_credential_matrix,
"credential_readiness": h1b_packet.get("credential_readiness", "NOT_PROVISIONED_OR_PRESENT_UNVERIFIED"),
"decision_statement": h1b_packet.get("decision_statement", "H1B_PACKET_UNAVAILABLE"),
```

## SECONDARY DEFECT FIXED — backend read credential VALUES

The endpoint used `os.environ.get("OPENAI_API_KEY")` for its presence check. `.get()`
materializes the secret value into the process; the H1B brief permits an **existence check
only**. Replaced with `in os.environ`, which never touches the value:

```python
_cred_refs = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
}
h1b_credential_matrix = {
    provider: {
        "credential_reference": ref,
        "status": "PRESENT_UNVERIFIED" if ref in os.environ else "NOT_PROVISIONED",
        "value_exposed": False,
    }
    for provider, ref in _cred_refs.items()
}
```

## UI (Phase 7)

`HelmCouncilView.tsx` — the H1 founder decision panel now renders the mandated rows:
FOUNDER AUTHORIZATION, per-provider OPENAI / ANTHROPIC / XAI CREDENTIAL (reference name
only, never a value), EXTERNAL CALLS, FRONTIER LIVE QUORUM, PROMOTION, SAFE TO EXECUTE.
PACKAGE INTEGRITY's color is now **derived from its value** via `getStatusColor()` rather
than hardcoded `#10b981` — a `FAIL` can no longer render green (no fake green).

Frontend build: PASS (1,489 modules transformed).
