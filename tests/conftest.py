"""
tests/conftest.py — shared fixtures for the hoch_agent_swarm test suite.
"""

import pytest

# Prevent pytest from crawling into src/ and collecting main.py's `test()`
# function as a top-level test item.
collect_ignore_glob = ["../src/**"]


# ---------------------------------------------------------------------------
# Known-good markdown fixtures shared across test files
# ---------------------------------------------------------------------------

@pytest.fixture
def good_security_audit_content() -> str:
    return """\
# Security Audit Report

## Scope
This audit covers all seven assembled agent configurations.

## Agent Configuration Review
All agents have allow_delegation set to false and max_iter set to 3.
No agent is configured to spawn additional subagents dynamically.

## Tool Access Verification
Each agent operates within the tool access tier defined in the manifest.
The security operator has admin_gated access; all others are read_only or write_gated.

## Secret Scrubbing Status
No environment variable values or API keys appear in any task output or log.

## Replay Protection Status
Each crew run is uniquely identified by timestamp stored in artifacts/crew_runs/.

## Findings
No violations detected. All agents respect capability boundaries.

## Verdict
PASS. Configuration meets all requirements in the Hoch Agent Swarm manifest v1.0.0.
"""


@pytest.fixture
def good_antigravity_plan_content() -> str:
    return """\
# Hoch Agent Swarm Antigravity Execution Plan

## Mission
The Hoch Agent Swarm integrates Google Antigravity with CrewAI as the bounded runtime.

## Inputs Reviewed
- topic: AI LLMs
- antigravity_role: Agentic development cockpit.
- crewai_role: Local bounded multi-agent runtime.
- integration_mode: Antigravity plans; CrewAI executes.

## Crew Output Chain
Seven tasks execute sequentially with explicit context wiring from asset mapping
through to the final Antigravity integration report.

## Security Audit Summary
The security audit confirmed all delegation bounds and tool access limits are met.
No secrets were exposed in task outputs or logs.

## Antigravity Integration Steps
Antigravity reads the project structure and plans all implementation steps before
any code changes are applied. CrewAI executes the bounded crew deterministically.

## Local-Only Constraints
All runs use Ollama at localhost with no external network calls permitted.
File writes are restricted to the project root and its artifacts/ subdirectories.

## Validation Checklist
- Both artifact files exist and are non-empty.
- No garbage patterns detected in either artifact.
- All required headings present in both artifacts.

## Next Actions
Review output and promote to Hoch Agent Swarm governance ledger.
"""


@pytest.fixture
def garbage_content() -> str:
    return """\
Here's a simplified version of the code with comments:

```python
import json
import random

executable_tasks = '''
[{"execution_time": random.uniform(1000,2000)}]
'''
manifest = {"cef": evidence_file["audit_report"]}
print(json.dumps(manifest, indent=4))
```

Feel free to ask for any further refinement!
"""
