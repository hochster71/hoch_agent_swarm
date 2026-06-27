# Evidence Policy

The Prompt Control Plane operates on an "Evidence-First" principle. No task, execution loop, or release step is complete without generating verifiable evidence.

## Required Mission Artifacts
Every swarm execution mission must generate a dedicated artifact directory containing:
1. `mission.json`: Contains `mission_id`, `task_id`, timestamp, user input summary, and approval state.
2. `selected_prompts.json`: The exact list of prompts retrieved from the Prompt Library and wrapped by the Universal Contract.
3. `assumptions.md`: Documented assumptions, separated from observed facts, and the tests used to verify them.
4. `risks.md`: The threat model, risk score, and mitigations applied.
5. `actions.md`: The complete trace of actions taken by the agents.
6. `validation.md`: Results of automated tests, compiler runs, and QA checks.
7. `evidence_manifest.json`: A JSON list of all generated files, accompanied by their SHA-256 cryptographic hashes.

## Evidence Freshness
Evidence is only valid for the current execution epoch. If the workspace state changes (e.g. branch checkout, code update, model pull), the validation tests must be re-run and a new evidence manifest generated.

## File Paths
All artifacts must be saved under the designated conversation artifacts directory:
`/Users/michaelhoch/.gemini/antigravity/brain/{conversation_id}/` or in the repository’s `artifacts/pentest/evidence/` for CI/CD checks.

## Audit Traceability
Every database insert in `backend/swarm_ledger.db` must link to a valid `evidence_manifest.json` file path to guarantee that all state changes can be audited and traced back to their source execution loop.

## Release Evidence Package
Before any tag is committed (e.g. `v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY`), a compiled evidence package must be generated, checked with `checksum-evidence-pack.ts`, and verified by the CI validator.
