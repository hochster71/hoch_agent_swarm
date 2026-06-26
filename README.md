# Hoch Agent Swarm

A bounded multi-agent AI system built with [CrewAI](https://crewai.com), designed as
a local execution adapter for the
[Google Antigravity](https://antigravity.dev) agentic development cockpit.

Antigravity handles planning, code editing, and artifact review.  
CrewAI executes deterministic sequential crews locally via [Ollama](https://ollama.ai).

See [`docs/antigravity_integration_doctrine.md`](docs/antigravity_integration_doctrine.md)
for the full architectural contract.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | `>=3.10, <3.14` |
| [uv](https://docs.astral.sh/uv/) | latest |
| [Ollama](https://ollama.ai) | running locally at `http://localhost:11434` |
| Model | `ollama pull llama3.1:8b` |

---

## Installation

```bash
# Install dependencies
uv sync

# Verify environment
uv run python -c "import crewai, mcp; print('crewai', crewai.__version__); print('mcp stub', getattr(mcp, '__version__', 'no version'))"
```

> **Note**: `mcp` resolves to a local stub package. See
> [`docs/mcp_stub.md`](docs/mcp_stub.md) for details.

---

## Configuration

Copy `.env` and set your model endpoint:

```bash
MODEL=ollama/llama3.1:8b
API_BASE=http://localhost:11434
```

No OpenAI API key is required for local Ollama runs.

Agent definitions → [`src/hoch_agent_swarm/config/agents.yaml`](src/hoch_agent_swarm/config/agents.yaml)  
Task definitions → [`src/hoch_agent_swarm/config/tasks.yaml`](src/hoch_agent_swarm/config/tasks.yaml)  
Crew wiring → [`src/hoch_agent_swarm/crew.py`](src/hoch_agent_swarm/crew.py)

---

## Running the Crew

```bash
uv run run_crew
```

After the run completes, artifacts are validated automatically.  
If either artifact fails validation, the command exits with a non-zero status.

**Output artifacts:**

| Artifact | Path |
|---|---|
| Security audit report | `artifacts/security_reviews/security_audit_report.md` |
| Antigravity execution plan | `artifacts/antigravity/antigravity_execution_plan.md` |

Prior artifacts are archived to `artifacts/crew_runs/<timestamp>/` before each run.

---

## Running with an External Trigger

```bash
uv run run_with_trigger '{"topic": "swarm orchestration", "current_year": "2026"}'
```

Missing payload fields default to safe values — `topic` and `current_year` are
never passed as empty strings.

---

## Testing

```bash
uv run pytest -q
```

The test suite covers:

- Crew instantiation (7 agents, 7 tasks, context wiring, delegation bounds)
- Artifact validation logic (garbage patterns, required headings, length checks)
- Real artifact quality (fails explicitly if canonical artifacts are missing or invalid)
- Entry-point input defaults and payload parsing

---

## Quality Gate

A single command validates the full project locally without any cloud dependency:

```bash
uv run quality_gate
```

Runs in order, without short-circuit:

| Step | What it checks |
|---|---|
| `import_check` | Package imports cleanly |
| `preflight` | `.env`, `MODEL`, `API_BASE`, Ollama reachable, model pulled |
| `pytest` | Full test suite (264 tests) |

Exit 0 = PASS. Exit 1 = FAIL with per-step detail.

Optional flags:
```bash
uv run quality_gate --live    # also runs the crew end-to-end (adds ~minutes)
uv run quality_gate --json    # machine-readable JSON output
```

Run this before committing, before a trial worktree run, and after any
dependency or environment change.

---

## Project Structure

```
hoch_agent_swarm/
├── src/hoch_agent_swarm/
│   ├── config/
│   │   ├── agents.yaml           # Agent definitions (role, goal, backstory, bounds)
│   │   └── tasks.yaml            # Task definitions (description, expected_output, context)
│   ├── tools/
│   │   └── custom_tool.py        # Custom tool stub (not yet implemented)
│   ├── artifact_validation.py    # Post-run artifact quality enforcement
│   ├── crew.py                   # Crew orchestration with explicit context wiring
│   └── main.py                   # Entry points: run, train, replay, test, run_with_trigger
├── artifacts/
│   ├── agent_manifests/          # Hyper-agent archetype manifest
│   ├── antigravity/              # Antigravity execution plan (canonical, committed)
│   ├── crew_runs/                # Per-run archives (gitignored)
│   └── security_reviews/        # Security audit reports (committed)
├── docs/
│   ├── antigravity_integration_doctrine.md
│   └── mcp_stub.md               # Why dummy_mcp/ exists and how to replace it
├── dummy_mcp/                    # Local MCP stub — see docs/mcp_stub.md
├── knowledge/
│   └── user_preference.txt       # Operator identity context for knowledge-aware agents
└── tests/
    ├── test_artifact_validation.py
    └── test_crew_smoke.py
```

---

## Architecture

See [`docs/antigravity_integration_doctrine.md`](docs/antigravity_integration_doctrine.md)
for the full separation-of-concerns contract between Antigravity and CrewAI.

```
Antigravity (cockpit)
  → plans, edits code/YAML, reviews artifacts
  → CrewAI (bounded local runtime)
      → executes 7 sequential agents via Ollama
      → validates and archives output artifacts
      → Hoch Agent Swarm governance ledger
```

## Local MCP Stub

This project uses a local `dummy_mcp/` stub instead of the real MCP SDK.
See [`docs/mcp_stub.md`](docs/mcp_stub.md) for the rationale, boundaries,
and instructions to restore the real package when needed.
