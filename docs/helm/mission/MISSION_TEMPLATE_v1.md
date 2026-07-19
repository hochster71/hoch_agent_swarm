# HELM Mission Contract v1

> HELM-GOV | adopted by: `docs/helm/edr/EDR-0007-mission-contract-v1.md` | enforced by: `backend/helm_runtime/mission_contract.py` | governed by: `HELM_CONSTITUTION_v1.0.md` (frozen, not amended)

The **execution contract** every HELM mission is issued under, regardless of which
role runs it or which provider is bound to that role at the time.

## Why this exists

HELM has permanent role doctrines (`coordination/governance/role_overlays/ROLE_*.md`)
and runtime provider bindings (`coordination/governance/role_bindings.json`). It did
**not** have a common shape for the third layer — the mission itself. Missions were
seeded ad hoc (`seeded_missions.json`, `soak_missions.jsonl`, `executive_mission.json`),
each with a different shape, so there was no single place to state what an agent may
touch, where it must stop, and what would count as proof.

Three layers, smallest on top:

```
Mission          (changes constantly — this contract)
   ↓
Role doctrine    (rarely changes — ROLE_*.md)
   ↓
Provider binding (replaceable — role_bindings.json)
```

The doctrine stays tiny because the mission carries the specifics. Adding a factory
means adding missions, not rewriting governance.

## The contract

```yaml
MISSION_ID:            # M-<FACTORY>-<SLUG>-<NNN>, unique, stable
TITLE:                 # one line, imperative
OWNER:                 # founder | orchestrator
ROLE:                  # orchestrator | builder | auditor | research | security
OBJECTIVE:             # the observable end state, not the activity
SUCCESS_CRITERIA:      # list; each item must be checkable by someone who wasn't here
INPUTS:                # list of paths / URLs / prior evidence packs
EXPECTED_OUTPUTS:      # list of artifacts this mission must produce
SCOPE:                 # paths/subsystems this mission MAY write to
TOOLS_ALLOWED:         # list; omitted tool = not permitted
CONSTRAINTS:           # list; guardrails specific to this mission
EDR_REQUIRED:          # YES | NO — YES for any architectural change
FOUNDER_GATES:         # list of the founder-only actions this mission may approach
STOP_CONDITIONS:       # list; conditions that end the mission without completion
EVIDENCE_REQUIRED:     # list; what must be in the evidence pack
TRUTH_SOURCE:          # see below — the mechanism that will produce the evidence
EXECUTION_CONTEXT:     # optional; execution fingerprint (see below)
RETURN:                # DONE | PARTIAL | BLOCKED + evidence paths
```

`SCOPE` is an allowlist, and `TOOLS_ALLOWED` is an allowlist. Anything not named is
denied. This is what lets a Builder mission and an Architect mission use the *same*
doctrine while differing only in what they may touch — no separate permanent doctrine
per specialization.

## TRUTH_SOURCE — provenance, projected onto the ratified truth classification

HELM already has a founder-ratified truth classification enforced in code
(`backend/security/proof_contract.py`): **OBSERVED / DERIVED / CACHED / ASSERTED /
UNKNOWN**, where only `OBSERVED` and `DERIVED` may advance a critical node
(`ADVANCING`).

`TRUTH_SOURCE` does **not** replace it and must never become a second truth
vocabulary. It names the *mechanism* that will produce the evidence, and each
mechanism projects onto exactly one ratified truth class:

| TRUTH_SOURCE            | projects to | advances state? | meaning |
|-------------------------|-------------|-----------------|---------|
| `LIVE_RUNTIME`          | OBSERVED    | yes | a real running system was observed |
| `TEST_EXECUTION`        | OBSERVED    | yes | tests were actually executed and their output captured |
| `DETERMINISTIC_SCRIPT`  | DERIVED     | yes | mechanically computed from OBSERVED evidence |
| `STATIC_ANALYSIS`       | ASSERTED    | **no** | computed from source, not from behavior |
| `HUMAN_INPUT`           | ASSERTED    | **no** | founder or operator statement, independently unproven |
| `UNKNOWN`               | UNKNOWN     | **no** | no reliable evidence exists |

Two consequences worth stating plainly, because they are policy, not plumbing:

1. **A clean linter or a passing type-check cannot advance a critical node.**
   `STATIC_ANALYSIS` reads source; it is not evidence that the system behaves. This
   is NO-FAKE-GREEN applied to the difference between *code that looks right* and
   *code that ran*.
2. **Founder attestation cannot advance a critical node either.** `HUMAN_INPUT` maps
   to ASSERTED by design — the same rule that keeps a model's claim from advancing
   state keeps a human's claim from advancing it. Founder authority governs *gates*
   (spend, release, submit); it does not manufacture evidence.

A mission whose `TRUTH_SOURCE` is non-advancing may still be perfectly valid — it
simply cannot close a critical-path node on its own, and the validator says so.


## EXECUTION_CONTEXT — the execution fingerprint

Optional but recommended; auto-capturable via
`mission_contract.capture_execution_context()`.

```yaml
EXECUTION_CONTEXT:
  correlation_id:          # the INCUMBENT identifier — never a new run_id
  commit_sha:              # HEAD at issue time, or UNKNOWN
  dirty:                   # uncommitted changes present?
  runtime_version:
  doctrine_version:
  mission_schema_version:
```

**Why `correlation_id` and not `run_id`.** `backend/helm_runtime/transaction.py`
already mints a `correlation_id` (uuid4) for every mission commit. Adding a parallel
`run_id` would recreate precisely the dual-vocabulary drift that `TRUTH_SOURCE` was
designed to avoid. One identifier, one meaning.

`transaction_id` and `mission_version` are deliberately **not** declared here — they
have a different lifecycle. EXECUTION_CONTEXT is captured when a mission is *issued*
and fingerprints the code and doctrine it runs against; `transaction_id` and
`mission_version` are minted at *write* time by `MissionTransaction`.

**Honesty rule.** Any field that cannot be determined is recorded as `UNKNOWN`. It is
never guessed, defaulted, or back-filled. Outside a git repository, `commit_sha` is
`UNKNOWN` — the capture does not invent one.

**Reproducibility.** An `UNKNOWN` commit or a dirty working tree means evidence
produced under this context cannot be reproduced from the repository alone.
`reproducibility(ctx)` reports this; it does **not** block. A working tree is
routinely dirty during active development, and a blocking rule would halt every
mission — governance theatre rather than governance. The Auditor decides what a
non-reproducible context is worth.

## Founder gates are declared, not discovered

`FOUNDER_GATES` names the founder-only actions the mission may come near:

```
SPEND · KEYS · RELEASE · SUBMISSION · MONEY · PRODUCTION_DEPLOY · CREDENTIAL_CREATION · EXTERNAL_IRREVERSIBLE
```

Declaring a gate does **not** authorize it. It requires the corresponding stop
condition, so an agent that reaches the gate ends the mission there instead of
improvising past it. The validator enforces that pairing.

## Return

```
RETURN: DONE | PARTIAL | BLOCKED
  evidence: <paths>
  truth: <the ratified class actually achieved>
  unmet: <success criteria not met, if PARTIAL/BLOCKED>
```

`DONE` claimed with a non-advancing truth class is a contract violation, not a
completion. There is no fourth value; "basically done" is `PARTIAL`.

## Minimal example

```yaml
MISSION_ID: M-HFF-RECURRING-DEPLOY-001
TITLE: Take Recurring Charge Finder from code-complete to live checkout
OWNER: founder
ROLE: builder
OBJECTIVE: A stranger can reach a working $9 checkout for hff-recurring-charges.
SUCCESS_CRITERIA:
  - POST /api/create-checkout-session returns a real Stripe URL
  - a signed webhook grant unlocks the delivery page
INPUTS:
  - products/hff-recurring-charges/README.md
EXPECTED_OUTPUTS:
  - docs/evidence/runtime/<ts>_recurring_checkout_verify.md
SCOPE:
  - products/hff-recurring-charges/
TOOLS_ALLOWED: [bash, git]
CONSTRAINTS:
  - no secrets written to the repo or printed
EDR_REQUIRED: NO
FOUNDER_GATES: [KEYS, SPEND, PRODUCTION_DEPLOY]
STOP_CONDITIONS:
  - founder gate encountered
  - missing evidence
  - policy violation
  - unknown runtime state
EVIDENCE_REQUIRED: [logs, tests]
TRUTH_SOURCE: LIVE_RUNTIME
RETURN: DONE | PARTIAL | BLOCKED + evidence paths
```
