# Evidence Traceability Matrix

> [!WARNING]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated.*

---

## 1. Compliance Mapping Table

| Subsystem Track | Cockpit View / Tab | API Endpoint / Route | Output Artifact File | Screenshot Evidence | Verification Proof (Tests) | Release Candidate Packaging |
|---|---|---|---|---|---|---|
| **PROMPTBRAIN1** (Prompt Registry) | **Prompt Brain** (`#page-promptbrain`) | `/api/v1/promptbrain/prompts` | [normalized_prompt_registry.json](file:///Users/michaelhoch/hoch_agent_swarm/artifacts/promptbrain/normalized_prompt_registry.json) | `promptbrain.png` | `tests/test_promptbrain.py` | `v0.1.0-rc9` |
| **BRAIN2** (Evidence Index) | **Evidence Brain** (`#page-evidencebrain`) | `/api/v1/brain/query` | `data/brain_evidence.db` | `evidencebrain.png` | `tests/test_brain_runtime.py` | `v0.1.0-rc9` |
| **PROMPTQA1** (Prompt Quality Gate) | **Prompt QA Forge** (`#page-promptqa`) | `/api/v1/promptqa/eval` | [prompt_regression_results.json](file:///Users/michaelhoch/hoch_agent_swarm/artifacts/promptqa/prompt_regression_results.json) | `promptqa.png` | `tests/test_quality_gate.py`, `tests/test_promptqa.py` | `v0.1.0-rc9` |
| **BRAIN3** (Sealing & POAM) | **Evidence Brain** (`#page-evidencebrain`) | `/api/v1/brain/validation-status` | `artifacts/release_candidates/` | `evidencebrain.png` | `tests/test_release_candidate.py`, `tests/test_rc_inspector.py` | `v0.1.0-rc9` |
| **OPERATOR1** (Operator Cockpit) | **Operator Cockpit** (`#page-operator`) | `/api/v1/operator/health` | `/api/v1/operator/health` (JSON) | `operator.png` | `tests/test_operator_launcher.py` | `v0.1.0-rc9` |
| **RC7** (Launcher & Checks) | **Operator Cockpit** (`#page-operator`) | `/` | [operator_launcher.py](file:///Users/michaelhoch/hoch_agent_swarm/src/hoch_agent_swarm/operator_launcher.py) | `operator.png` | `tests/test_operator_launcher.py` | `v0.1.0-rc9` |
| **DOCKER1 & DOCKER2** (Docker Setup & Live Screens) | **Overview** (`#page-overview`) | `/api/v1/operator/health` | [manifest.json](file:///Users/michaelhoch/hoch_agent_swarm/artifacts/live_screenshots/manifest.json) | `overview.png`, `promptbrain.png`, `promptqa.png`, `evidencebrain.png`, `hochtv.png`, `operator.png` | `tests/test_docker_files.py`, `tests/test_live_screenshot_manifest.py` | `v0.1.0-rc9` |
| **REVIEW1** (Reviewer Packet) | **Overview** (`#page-overview`) | N/A | [final_reviewer_packet.md](file:///Users/michaelhoch/hoch_agent_swarm/artifacts/reports/final_reviewer_packet.md) | `overview.png` | `tests/test_artifact_validation.py` | `v0.1.0-rc10` |

---

## 2. Verification Proof Index

- **Host Tests Execution**: 551 test cases successfully passed.
- **Docker Tests Execution**: 550 test cases successfully passed inside a Linux container environment.
- **Evidence Integrity Verification**: Checked via local pytests verifying absolute hashes and manifest metadata constraints of Chromium captured screens.
- **Database Integrity Verification**: Checked via `tests/test_brain_runtime.py` validating TF-IDF word vectors, git extraction subprocess commands, and SQLite transactional table writes.
