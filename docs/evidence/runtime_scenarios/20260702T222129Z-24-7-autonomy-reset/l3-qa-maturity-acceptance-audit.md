# L3 QA Maturity Acceptance Audit

This audit documents verification proof of L3 QA Maturity for the HAS/HASF/HELM 24/7 remote autonomy runtime.

---

## 1. Golden Dataset Audit
* **Number of cases per agent**: 10 cases for `hasf_scoring_agent`, 10 cases for `evidence_agent` (total 20 cases).
* **Schema validity**: Fully compliant with nested deterministic checking keys (`required_fields`, `score_ranges`, `must_flag`, `forbidden_content_patterns`).
* **Founder review status distribution**:
  * `Batch 1` (Cases 1-5 for both agents): `APPROVED` (5 cases per agent).
  * `Batch 2` (Cases 6-10 for both agents): `PENDING` (5 cases per agent).
* **Negative/adversarial cases present**: Yes, evaluating duplicates, misaligned business profiles ( betting app, screen time max tools), and invalid schemas.
* **Planted-secret case present**: Yes, `case-ev-008` validates response containing high-entropy credential leakage detection.
* **Required fields present**: Yes, schema validated successfully.

---

## 2. Eval Result Audit
* **Deterministic pass rate**: 100.0% across all 20 evaluated cases.
* **Judge mean score**: `4.03 / 5.0` (exceeding the `3.5 / 5.0` threshold).
* **Consistency score**: `100.0%` (simulated agreement, exceeding the `80%` threshold).
* **Failed case IDs**: `None`.
* **Model/backend used for judge**: `google/gemma-4-12b-qat` on high-capacity tunnel port 1234.
* **Qwen2.5:1.5b exclusion**: Excluded from judge duties; only used for R0/R1 planning inference on port 11434.

---

## 3. Policy Enforcement Audit
* **Forbidden action blocked**: Verified. Attempts to invoke unauthorized adapter endpoints fail policy checks.
* **Force push main denied**: Probed in `helm_policy_engine.py` (git_push_force_main blocked under `github` contract).
* **Founder-gated actions**: Blocked by default unless `founder_approved: true` is set in context.
* **Evidence structure**: Log file includes `agent_id`, `task_id`, `adapter_id`, `attempted_action`, and `disposition`.

---

## 4. Gate Failure Proof Audit
* Planted failure proofs are logged inside [phase1-gate-failure-proofs.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/phase1-gate-failure-proofs.md).
* Covers:
  - Stale heartbeat
  - Stale adapter probe
  - Completed task missing evidence
  - Fake token
  - Fake Authorization bearer header
  - Fake bypass URL

---

## 5. Chaos 1-5 Audit
The following chaos reports exist and verify system resilience:
1. [chaos-01-model-endpoint-unavailable.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/chaos-01-model-endpoint-unavailable.md)
2. [chaos-02-ollama-container-killed.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/chaos-02-ollama-container-killed.md)
3. [chaos-03-lmstudio-tunnel-dropped.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/chaos-03-lmstudio-tunnel-dropped.md)
4. [chaos-04-malformed-model-output.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/chaos-04-malformed-model-output.md)
5. [chaos-05-corrupted-task-queue.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/chaos-05-corrupted-task-queue.md)

---

## 6. Remote Gate Battery
Executed successfully on `HOCH-200` VPS with passing outputs:
* `verify_has_hasf_end_goals.py`: **🟢 PASS**
* `verify_helm_autonomy_layer.py`: **🟢 PASS**
* `verify_24_7_remote_runtime.py`: **🟢 PASS**
* `verify_model_adapter_health.py`: **🟢 PASS**
* `verify_runtime_truth_freshness.py`: **🟢 PASS**
* `verify_no_secret_leakage.py`: **🟢 PASS**
* `verify_agent_output_quality.py`: **🟢 PASS**

---

## 7. Product 002 Guardrail
* **Vetting Gated Lock**: Verified in [HASF_PRODUCT_002_FOUNDER_REVIEW.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/products/cyberqrg-ai/HASF_PRODUCT_002_FOUNDER_REVIEW.md).
* **Build / Release / Monetization status**: Locked to planning only. High-risk build actions (R2+) and public deployment actions (R3/R4) are blocked.
* **Founder approval override**: Mandatory for all R2+ build transitions.
