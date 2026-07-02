# HELM Onboarding Evidence

* **Created At**: 2026-07-02T16:34:08-05:00
* **Status**: `active_candidate`
* **Release Authority**: `false`

---

## Why HELM Exists
HELM is introduced as the Navy-coded steering and execution agent for HAS/HASF. It serves as the primary implementation persona for translating Michael Hoch's intent into working code, tests, and evidence. By introducing HELM as the execution persona, we decouple the memory/learning system (Michael AI Model) from the execution layer (HELM), thereby clarifying agent roles and reducing cognitive overhead.

---

## Paths and Configuration
* **Agent Profile JSON**: [helm.agent.json](file:///Users/michaelhoch/hoch_agent_swarm/config/agents/helm.agent.json)
* **Agent Markdown Profile**: [HELM.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/agents/HELM.md)
* **System Prompt**: [helm_system_prompt.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/prompts/helm_system_prompt.md)

---

## Integration Details

### API Endpoint
The status endpoint has been registered:
* `GET /api/v1/helm/status`
It returns details about HELM's current status, role, doctrine, and constraints (e.g. `NO_ACTIVE_RELEASE_GO` is active and `release_authority` is false).

### Michael AI Model
HELM is registered as the default execution agent and available persona in the Michael AI state synthesizer:
* `/api/v1/michael-ai/current-state` returns `"current_execution_agent": "HELM"`.
* `/api/v1/michael-ai/next-prompt` addresses the prompt to HELM via `"**TO**: HELM"` and enforces release blockers.

---

## Test Results
All unit tests passed successfully:
```bash
$ uv run pytest tests/unit/helm -v
tests/unit/helm/test_helm_profile.py::test_helm_profile_exists PASSED
tests/unit/helm/test_helm_profile.py::test_helm_system_prompt_doctrine PASSED
tests/unit/helm/test_helm_status.py::test_helm_api_status_endpoint PASSED
tests/unit/helm/test_helm_status.py::test_michael_ai_helm_integration PASSED
4 passed in 0.44s
```

All `michael_ai` tests passed successfully:
```bash
$ uv run pytest tests/unit/michael_ai -v
6 passed in 0.10s
```

---

## Gate Results
* **final_verifier_gate.sh**: BLOCKED (correct, expected release posture)
* **anti_fake_gate.sh**: PASS
* **scan_host_paths.sh**: PASS
* **scan_hardcoded_status.sh**: PASS

---

## Limitations
* HELM has no release authority.
* Routing remains disabled.
* `NO_ACTIVE_RELEASE_GO` is hardcoded as a blocker and cannot be cleared.

---

## Next Lane
* Canonical Docker verification for Michael AI layer.
