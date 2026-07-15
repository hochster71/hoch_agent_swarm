# HELM NIST Control-Coverage Matrix

**Author:** SWARM-3 (parallel build, `swarm/nist-matrix`)
**Grounding:** `backend/helm/nist_matrix.py` — every row below is produced by an
executable assessor that re-derives its verdict from live evidence on disk / in-process
at request time. This document is a snapshot; the live, always-current version is served
at `GET /api/v1/helm/nist` (JSON) and rendered at `GET /nist` (UI panel).

## Doctrine

This matrix follows the same fail-closed discipline as every other HELM truth surface
(`backend/helm_live_api.py`, `backend/security/helm_control_catalog.py`,
`backend/truth/evidence_chain.py`):

| Status | Meaning |
|---|---|
| **COVERED** | The assessor ran and OBSERVED the claimed evidence, fresh, right now. |
| **PARTIAL** | The assessor ran and found REAL evidence of a mechanism, but coverage is incomplete or the evidence is stale — a documented, honest gap, not an absence of effort. |
| **UNVERIFIED** | The assessor could not run, the evidence source is missing/unreadable, or the check raised an exception. Never silently treated as satisfied. |

A control is **never** COVERED because a comment, a design doc, or a past run says so.
If evidence cannot be shown *right now*, the control is PARTIAL or UNVERIFIED. This
mirrors `backend/security/helm_control_catalog.py`'s IMPLEMENTED / NOT_IMPLEMENTED /
UNKNOWN vocabulary — this module reuses several of its assessors directly (SC-7, AC-3,
SI-4, CP-10, RA-5, SR-3) rather than re-deriving the same live check a second time and
risking the two disagreeing.

## Standards in scope

- **NIST CSF 2.0** (Cybersecurity Framework, Feb 2024) — six top-level Functions:
  GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER. GOVERN is new in 2.0 and carries
  organizational context, risk strategy, oversight, and supply-chain risk management.
  Reference: NIST CSWP 29, *The NIST Cybersecurity Framework (CSF) 2.0*, Feb 26, 2024.
- **NIST SP 800-53 Rev 5** — *Security and Privacy Controls for Information Systems and
  Organizations*, Sept 2020 (incl. updates). Twenty control families.
- **NIST SP 800-218 (SSDF)** — *Secure Software Development Framework*, referenced for
  the CM-3/SA-10 secure-SDLC row.

## The matrix (snapshot)

Grouped by CSF 2.0 Function. Each row: HELM mechanism → CSF Category → SP 800-53 Rev 5
control → status → evidence pointer.

### GOVERN

| Mechanism | CSF Category | Control | Status | Evidence pointer |
|---|---|---|---|---|
| Founder decision chain-of-custody (`backend/council/founder_gate.py`) + `HELM_SOURCE_HOLDER` identity binding + monotonic fencing tokens (`backend/mission_control/source_lease.py`) | GV.OV — Oversight | **AU-10** Non-repudiation | **COVERED** | `/api/v1/helm/authority` |
| Tool/model provenance attestation, fail-closed on unattested dispatch (`backend/truth/supply_chain.py`) | GV.SC — Supply Chain Risk Management | **SR-3** Supply Chain Controls and Processes | **PARTIAL** | `/api/v1/helm/wall` |

### IDENTIFY

| Mechanism | CSF Category | Control | Status | Evidence pointer |
|---|---|---|---|---|
| Static verifiers run against the codebase (egress, runtime-truth, tautology scanners under `scripts/verify_*.py`) | ID.RA — Risk Assessment | **RA-5** Vulnerability Monitoring and Scanning | **COVERED** | `/api/v1/helm/wall` |

### PROTECT

| Mechanism | CSF Category | Control | Status | Evidence pointer |
|---|---|---|---|---|
| AU-9 tamper-evident evidence chain: `entry_hash = sha256(canonical(body) + prev_hash)` (`backend/truth/evidence_chain.py`) | PR.DS — Data Security | **AU-9** Protection of Audit Information / Cryptographic Protection | **COVERED** | `/api/v1/helm/chain` |
| `guarded_edit` lease-before-write facade + `.githooks/pre-commit` conflict detector + non-trivial test suite (182 `test_*.py` modules) + commit-bound evidence | PR.PS — Platform Security | **CM-3 / SA-10** Configuration Change Control / Developer Config Mgmt (SSDF 800-218 alignment) | **COVERED**\* | `/api/v1/helm/chain` |
| Founder token gate on writes: fail-closed (no `HELM_FOUNDER_TOKEN` ⇒ no approvals), `hmac.compare_digest`, PROPOSE_ONLY/FOUNDER_ONLY verb separation | PR.AA — Identity Mgmt, Authn and Access Control | **AC-3 / IA-2** Access Enforcement / Identification & Authentication (write path) | **COVERED** | `/api/v1/helm/authority` |
| Read-side (GET) authentication on the live API | PR.AA — Identity Mgmt, Authn and Access Control | **AC-3 / IA-2** (read path) | **PARTIAL** | `backend/security/zero_trust/__init__.py` |
| AST-verified single egress chokepoint for all model dispatch (`scripts/council/gateway.py` + a static egress verifier) | PR.IR — Technology Infrastructure Resilience | **SC-7** Boundary Protection | **COVERED** | `/api/v1/helm/wall` |

\* `CM-3/SA-10` is COVERED only when `core.hooksPath` is configured for the checking
clone (`git config core.hooksPath .githooks`); it is opt-in per clone, not centrally
enforced across every machine that touches this repo. The assessor detects and reports
this distinction live rather than assuming it.

### DETECT

| Mechanism | CSF Category | Control | Status | Evidence pointer |
|---|---|---|---|---|
| A → B → C soak-phase seals + freshness gate (`backend/truth/soak_select.select_soak_package`) | DE.CM — Continuous Monitoring | **CA-7** Continuous Monitoring | **PARTIAL** | `/api/v1/helm/wall` |
| Continuous-monitoring surface with `UNKNOWN` guards and (ideally) zero numeric fallbacks | DE.CM — Continuous Monitoring | **SI-4** System Monitoring | **PARTIAL** | `/api/v1/helm/wall` |

### RESPOND

| Mechanism | CSF Category | Control | Status | Evidence pointer |
|---|---|---|---|---|
| Scoped-state blocking — a finding blocks the specific capability, not the whole lane (`backend/mission_control/scoped_states.py`) | RS.MI — Incident Mitigation | **AC-3** Access Enforcement (least-privilege mitigation) | **COVERED** | `/api/v1/helm/wall` |

### RECOVER

| Mechanism | CSF Category | Control | Status | Evidence pointer |
|---|---|---|---|---|
| SIGKILL restart-recovery proof with a monotonic fencing token (a resurrected/zombie writer cannot write after a real process interruption) | RC.RP — Recovery Planning | **CP-10** System Recovery and Reconstitution | **COVERED**† | `/api/v1/helm/wall` |

† Depends on `coordination/council/restart_recovery_proof.json` recording
`proof_class: LIVE_RUNTIME_PROOF` with a monotonic `fencing_token_before →
fencing_token_after`. If that artifact ages out or is superseded by a structural-only
proof, the live assessor will report PARTIAL/UNVERIFIED instead — this document does not
override the live check.

## Snapshot counts (at the commit this document was written against)

```
COVERED:     8 / 12
PARTIAL:     4 / 12
UNVERIFIED:  0 / 12
```

These counts are a point-in-time snapshot from the sandboxed verification environment
used to build this deliverable (see **Verification environment note** below) — treat
`GET /api/v1/helm/nist` as authoritative, not this document, for current numbers.

## Honest gap list

1. **Read-side authentication (AC-3/IA-2, read path) — PARTIAL.** SWARM-2 built a
   Zero-Trust read-auth layer (`backend/security/zero_trust/`: `HardenedConfig`,
   `ReadAuthMiddleware`, `dev_cert.py`, `bind_audit.py`, `staged_server.py`) but it is
   deliberately **not mounted** into `backend/helm_live_api.py`. Every `GET` endpoint on
   `:8770` is reachable without a token today; the only current boundary is the
   `127.0.0.1` bind + Tailscale network reachability (which is SC-7/PR.IR, not IA-2).
   Cutover requires explicit founder approval per SWARM-2's own doctrine, because
   flipping bind/TLS/read-auth carelessly can break phone access over Tailscale and the
   live Phase-C soak.
2. **CA-7 soak liveness — PARTIAL.** The authoritative soak package selection logic
   (`select_soak_package`) is real and independently verifiable, but at assessment time
   the newest daemon evidence inside the selected package was older than the 1200-second
   freshness budget the same logic enforces elsewhere (`backend/truth/wall_state.py`).
   Historical seals (3 phases sealed PASS at time of writing) are real; *current*
   liveness is what's in question, and the assessor refuses to claim COVERED on stale
   evidence.
3. **SI-4 continuous monitoring — PARTIAL.** The reused `helm_control_catalog`
   assessor found live numeric-fallback patterns (`or 0`, `or []`, `|| 0`) still present
   in `backend/helm_live_api.py`'s monitoring surface at assessment time. A dashboard
   that substitutes a default for a missing fact is fabricating, so this is reported
   honestly rather than rounded up.
4. **SR-3 supply-chain attestation — PARTIAL (environment-dependent).** The live check
   re-verifies the `GROK_CLI` tool binary's sha256 against what's on disk *right now*.
   In the sandboxed verification environment used to build this deliverable, that binary
   does not exist at the expected path, so the assessor reports PARTIAL rather than
   fabricating COVERED. On the host machine where the binary is actually installed, this
   row should independently re-verify as COVERED — re-run `GET /api/v1/helm/nist` there
   to confirm; this document does not assume that result.
5. **CM-3/SA-10 secure SDLC — conditionally COVERED.** The mechanisms exist repo-wide,
   but `core.hooksPath` is a per-clone git config, not a repo-enforced setting. A clone
   that never ran `git config core.hooksPath .githooks` gets no pre-commit conflict
   warning at all (the guard is opt-in by design, per `docs/SOURCE_TREE_COORDINATION_GUARD.md`-style
   history) — the live assessor detects and reports this rather than assuming every
   clone is configured.
6. **No dedicated CSF RESPOND/RECOVER controls beyond the two listed.** This matrix
   intentionally lists only mechanisms that could be grounded in real, inspectable code
   or ledgers. It does not claim broader RS/RC coverage (e.g., IR-4 incident handling,
   CP-9 backups) because no such mechanism was found in the repo at assessment time —
   absence of a row is itself an honest signal, not a hidden gap.

## Live evidence pointers used in this matrix

| Pointer | What it proves |
|---|---|
| `GET /api/v1/helm/chain` | AU-9 hash-chain verification result, most-recent 40 blocks, CONFIRMED_LIVE / CONTRADICTED / UNKNOWN |
| `GET /api/v1/helm/authority` | AU-10 founder decision chain + pending escalations + chain_intact flag |
| `GET /api/v1/helm/wall` | Independently-derived scopes: soak/seal state, scheduler, platform, TRUE_GO gate |
| `GET /api/v1/helm/nist` | This entire matrix, recomputed live |
| `backend/security/zero_trust/__init__.py` | Staged (not mounted) read-auth layer source |

## Verification environment note

This deliverable was built and its assessors were executed from a sandboxed Linux
environment with the repository mounted read/write, **not** from the Mac host that
serves the live `:8770` process (a Phase-C soak was running there and was explicitly
not to be disturbed). `curl http://127.0.0.1:8770/...` from that sandbox returns
connection-refused because the live process is bound in a different network namespace,
not because the route is broken. The route and matrix logic were instead verified by:

1. Running `backend.helm.nist_matrix.build_matrix()` directly against the real,
   on-disk repository state (the same files the live host process reads) — see the
   counts above.
2. Booting a throwaway local instance of `backend.helm_live_api:app` on a private port
   inside the sandbox and confirming `GET /api/v1/helm/nist` and `GET /nist` both return
   HTTP 200 with the matrix / panel, and that `GET /api/v1/helm/chain` (an evidence
   pointer this matrix links to) also returns 200 from the same instance.
3. Confirming the two-line route-registration edit to `backend/helm_live_api.py` is
   syntactically and behaviorally identical in structure to SWARM-1's already-merged
   `health_router` registration, minimizing risk to the shared file.

A qualified reviewer with access to the live host should independently re-run
`curl http://127.0.0.1:8770/api/v1/helm/nist` and `curl http://127.0.0.1:8770/api/v1/helm/chain`
to confirm parity; this document records that the sandboxed reproduction passed and does
not claim the host curl was performed by this agent.
