# PROMPTQA1 — PromptBrain QA Team, Prompt Evaluation Harness, and Continuous Prompt Improvement

The Prompt QA Forge (PROMPTQA1) is a local governed evaluation, scoring, regression-testing, and rewrite lifecycle harness for the prompts that drive every agent in the HOCH Agent Swarm. It implements quality controls, weakness detection registries, output simulations, routing evaluations, and a structured approval queue to safely iterate and improve prompt definitions without overriding baseline configurations.

## Compliance & Release Boundary Notice

> [!IMPORTANT]
> **PROMPTQA NOTICE & STATUS BOUNDARY**
> 
> *PromptQA provides prompt quality, regression, routing, and improvement evidence. It does not prove full compliance, eliminate risk, or grant ATO. Actual authorization requires review and approval by the appropriate authorizing authority.*
> 
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated, and no claim of absolute security is made.*

---

## 1. Prompt QA Team Roles

The QA Forge consists of 12 distinct specialist roles that perform verification duties:

1. **PROMPTQA-001 Prompt Quality Judge**: Evaluates prompt clarity, specificity, and constraints.
2. **PROMPTQA-002 Prompt Completeness Auditor**: Verifies that required inputs, outputs, and parameters exist.
3. **PROMPTQA-003 Prompt Safety and Boundary Reviewer**: Analyzes prompts for injection risk, overclaiming, and secrets.
4. **PROMPTQA-004 Prompt Regression Test Designer**: Designs assertions and test fixtures for outputs.
5. **PROMPTQA-005 Prompt Rewrite Engineer**: Focuses on formulating refactored template options.
6. **PROMPTQA-006 Prompt Routing Evaluator**: Evaluates prompt matching precision against test tasks.
7. **PROMPTQA-007 Prompt Evidence and Citation Judge**: Evaluates citation constraints and source provenance rules.
8. **PROMPTQA-008 Prompt Coverage Drift Auditor**: Monitors categorization and regulatory mapping drift.
9. **PROMPTQA-009 Agent Output Simulator**: Runs semantic execution checks on outputs.
10. **PROMPTQA-010 Prompt Approval Gatekeeper**: Enforces quality thresholds before candidate promotion.
11. **PROMPTQA-011 Prompt Versioning and Lineage Auditor**: Manages baseline histories, rollbacks, and diffs.
12. **PROMPTQA-012 PromptBrain Continuous Improvement Orchestrator**: Coordinates continuous sweeps and promotion.

---

## 2. Prompt Quality Scoring Model

Each prompt is evaluated across **21 scoring dimensions** on a scale of `0` to `5`:
- `clarity`
- `specificity`
- `role_definition`
- `mission_alignment`
- `input_requirements`
- `output_structure`
- `evidence_requirements`
- `framework_mapping`
- `sector_mapping`
- `risk_handling`
- `gap_analysis_strength`
- `remediation_guidance`
- `validation_tests`
- `machine_readable_output`
- `safety_boundaries`
- `anti_overclaiming_language`
- `citation_requirements`
- `tool_use_boundaries`
- `local_only_constraints`
- `fail_closed_behavior`
- `agent_routing_fit`

### Score Bands
- **0–49**: Poor
- **50–69**: Needs Improvement
- **70–84**: Acceptable
- **85–94**: Strong
- **95–100**: Release Grade

### Acceptance Gates
- **General Prompts**: Minimum score of `85` to release.
- **Critical Prompts (IDs starting with BRAIN-, PROMPT-, GAP-, SWARM-, GOVFRAME-)**: Minimum score of `90` to release.
- **Safety Boundaries & Fail-closed Language**: Must score $\ge 4$ on respective dimensions.

---

## 3. Assertion & Regression Harness

Assertions are evaluated deterministically to enforce engineering practices, including:
- Separating facts from assumptions.
- Structured risk-ranked findings.
- Mandatory remediation actions and closure criteria.
- Prohibited compliance/ATO claims.
- Fail-closed and boundary instruction presence.

---

## 4. Rewrite Candidate Lifecycle & Approval Gate

1. **Detection**: If a prompt scores below its release threshold, a versioned candidate is automatically compiled in `artifacts/promptqa/prompt_rewrite_candidates.json` with state set to `pending_review`.
2. **Review**: The candidate can be inspected in the dashboard detailing the score difference, detected weaknesses, and proposed rewritten body text.
3. **Approval**: Triggers an approval mutation POST request (`/api/v1/promptqa/approve`), checking that the candidate satisfies all quality and safety parameters.
4. **Promotion**: Once approved, the candidate prompt text replaces the active prompt version in `revised_master_prompt_library.json`, and its status changes to `active` in the lineage timeline.

---

## 5. CyberGov / ConMon / ATO Evidence Integration

All PromptQA output files are packaged as ATO-supporting evidence:
- `promptqa/prompt_quality_scores.json`
- `promptqa/prompt_weakness_register.json`
- `promptqa/prompt_assertions.json`
- `promptqa/prompt_regression_results.json`
- `promptqa/prompt_rewrite_candidates.json`
- `routing_eval_results.json`
- `promptqa/prompt_approval_queue.json`
- `promptqa/prompt_lineage.json`

Continuous Monitoring (ConMon) audits PromptQA for:
- Quality or coverage drift.
- Unresolved critical weaknesses count.
- Failed regression test counts.
- Pending approval backlogs.
