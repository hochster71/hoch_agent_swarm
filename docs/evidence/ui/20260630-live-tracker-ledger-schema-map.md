# HAS/HASF Live Tracker Ledger Schema Map — 2026-06-30

This document defines the schema mappings between the database tables in `backend/swarm_ledger.db` and the logical models used by the HAS/HASF Live Project Tracker cockpit dashboard.

## Databases Discovered
1. `backend/swarm_ledger.db` (Primary Immutable Ledger)
2. `backend/db/swarm_ledger.db` (Secondary / Temporary Run Data)
3. `backend/runtime_truth/state.db` (Empty SQLite container)
4. `hoch_skill_audit.db` (Offline agent skill audits)
5. `cybersecurity_diagrams.db` (System flow diagrams)
6. `data/brain_evidence.db` (Semantic graph linkages)

---

## Schema Mappings

### 1. Agents: `swarm_agents`
| Target Field | Source DB Column (or mapping rule) | Details |
|---|---|---|
| `name` | `display_name` | Public display name of the agent |
| `role` | `title` | Domain expertise role |
| `status` | `status` | Maps to `Running` or `Queued` / `Idle` |
| `current_task_id` | Derived | Resolved from active running tasks |
| `runtime_hours` | Derived | Computed from log timestamps |
| `model_used` | Derived | Inferred from `agent_model_policies` or standard defaults |
| `confidence` | `stats_json` | Parsed from reliability scores in stats JSON |
| `blocker` | Derived | Found in `incidents` / task status blockers |
| `next_action` | `catchphrase` | Or fallback recommendation |
| `last_update` | Derived | Last recorded heartbeat or run |
| `health` | `status` / Derived | Matches status values |
| `risk_level` | `tier` / Derived | Map tier level to risk values |
| `qa_verdict` | Derived | Inferred from `hochster_validation_evidence` |
| `data_source` | Literal | `SQLITE_LEDGER_TRUTH` |

### 2. Tasks: `swarm_tasks`
| Target Field | Source DB Column (or mapping rule) | Details |
|---|---|---|
| `id` | `task_id` | Dynamic task identifier |
| `name` | `title` | Public title |
| `domain` | Derived | Grouping domain (e.g. Planning, Code, Test) |
| `status` | `status` | Maps `pending` -> `Queued`, `completed` -> `Done`, etc. |
| `assigned_agent` | `owner_agent_id` | Owning agent ID |
| `dependencies` | `dependencies_json` | Parsed array of dependency IDs |
| `started_at` | Derived | From run start timestamps |
| `completed_at` | Derived | From task completion logs |
| `expected_hours` | `priority` / Derived | Priority-based estimation fallback |
| `actual_runtime_hours` | Derived | Calculated variance |
| `progress` | Derived | `100%` if done, otherwise computed percentage |
| `blocker` | Derived | Linked active blockers |
| `done_definition` | `acceptance_criteria` | Target definition of done |
| `downstream_unlocks` | Derived | Computed downstream nodes count |
| `critical_path_reason` | Derived | Description of PERT bottleneck |

### 3. Builds: `qa_runs`
| Target Field | Source DB Column (or mapping rule) | Details |
|---|---|---|
| `name` | `run_id` | Dynamic run name |
| `status` | `exit_code` | `Running` / `Done` / `Failed` based on exit status |
| `command` | `command` | The CLI string run |
| `exit_code` | `exit_code` | System return code |
| `log_path` | Derived | Link to standard build logs |
| `qa_verdict` | `output` | Summary validation status |

### 4. Events: `ledger_blocks`
| Target Field | Source DB Column (or mapping rule) | Details |
|---|---|---|
| `ts` | `timestamp` | UTC ISO-8601 timestamp |
| `type` | Derived | Parsed from event JSON object type |
| `message` | `event` | Extracted action summary |
