# BRAIN3 — Evidence Brain Release Sealing, PromptQA Ingestion, and Closure Dashboard

The Evidence Brain Compliance integration (BRAIN3) provides a unified framework to compile, index, graph, and package HOCH Agent Swarm prompt-quality metrics, security audit files, and continuous monitoring findings as regulatory-compliant evidence.

## Compliance & Release Boundary Notice

> [!IMPORTANT]
> **EVIDENCE BRAIN STATUS & BOUNDARY NOTICE**
> 
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated.*
> 
> *Evidence Brain ingestion, graph relationships, POA&M gap checks, and exported compliance bundles do not represent a claim of absolute security, automatic compliance, or an official Authorization to Operate (ATO). Actual authorization requires review and approval by an official Authorizing Official (AO).*

---

## 1. PromptQA Ingestion & Chunking

The database crawler inside `brain_runtime.py` is updated with a custom parser for JSON files in `artifacts/promptqa/`.
Instead of saving files like `prompt_quality_scores.json` or `prompt_weakness_register.json` as single `#full` documents, they are chunked by prompt ID (e.g. `prompt-BRAIN-001`). This provides:
- Highly granular search indexing.
- Direct linking between individual prompts and their respective QA attributes.

---

## 2. Connected Knowledge Graph

The edge builder in `_build_graph_edges` builds relationships between:
- Prompt nodes (e.g. `prompt-BRAIN-001`) and PromptQA scores, weaknesses, and regression passes (`qa_evidence_for` relationships).
- Prompts and NIST 800-53 / CMMC control families (`applies_to_control`).
- CyberGov and ConMon report findings and respective security control nodes (`gov_security_guidance` and `continuous_monitoring_finding` relationships).

---

## 3. Dynamic POA&M Gap Closures

The gap validation module `validate_gap_closures()` uses PromptQA scorecards to dynamically audit open gaps:
- It checks if a missing prompt has been generated and exists in the revised master library.
- It validates that its PromptQA score meets the release-grade threshold ($\ge 85$, or $\ge 90$ if critical).
- It verifies that the prompt has a passing regression test status.
- Gaps meeting all three criteria are marked as `"RESOLVED"` in the POA&M dashboard, pointing to the specific PromptQA score file as verification evidence.

---

## 4. Compliance Export Center

A new endpoint `GET /api/v1/brain/export` generates a single ZIP bundle `evidence_brain_compliance_bundle.zip` containing:
- The SQLite evidence database `data/brain_evidence.db`.
- The PromptQA scorecards, weakness registry, assertions, regression tests, and version lineages under `artifacts/promptqa/`.
- The PromptBrain catalog files under `artifacts/promptbrain/`.
- Canonical plans, reports, and security audits under `artifacts/reports/` and `artifacts/security_reviews/`.

Users can download this bundle directly via the dashboard button.

---

## 5. Release Sealing Workflow

A dedicated script `scripts/release_seal.py` automates candidate packaging:
1. Runs the test suite via `pytest` to verify correctness.
2. Checks git clean status.
3. Automatically sets a local git tag (e.g. `v0.1.0-rc3`).
4. Invokes the `package_release_candidate` script to freeze active hashes in `release_candidate.json`.
