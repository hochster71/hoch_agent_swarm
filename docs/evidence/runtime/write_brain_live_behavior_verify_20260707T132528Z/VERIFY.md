# write_brain_live Behavior Verification

## HEAD
b173dbb3e947e62ecb4689ff822465a64e473c49
b173dbb Harden runtime start stop SQLite writes
0a7d3d5 Harden provider key provisioning script
e1216e2 feat(r1): guided provider API-key provisioning script (opens key page, hidden paste, .env store)
0c50cdc Harden HOCH-200 mission commander truth dashboard
432eb73 fix(pert): wire tests/evidence/accountability/blocked to real sources (UNKNOWN if missing); guard: no hardcoded metric literals
305cc5a fix(pert): derived goal-percent wins over stale cadence-cache override (no more 80)

## Scoped status
 M scripts/write_brain_live.py
?? backend/factory/champion_loader.py
?? backend/factory/outcome_stats.py
?? backend/factory/runtime_ledger.py

## Compile

## Import and build live state
{
  "has_combat": true,
  "has_fleet": true,
  "has_gateway": true,
  "combat_keys": [
    "at",
    "gates",
    "genes_with_combat_record",
    "top",
    "total_champion_executions"
  ],
  "fleet_keys": [
    "latency",
    "nodes",
    "reachable",
    "status",
    "sync",
    "telemetry_note"
  ],
  "gateway_keys": [
    "alive_count",
    "backends",
    "primary"
  ],
  "gateway_alive_count": 3,
  "top_champions_count": 6
}

## Outcome stats dry verification
{'schema': 'brain-outcome-stats', 'genes_with_combat_record': 7, 'total_champion_executions': 15, 'gate_names': ['live_judge', 'm0_generation']}

## Forbidden behavior scan
NO_FORBIDDEN_BRAIN_LIVE_BEHAVIOR

## Generated output status check
?? data/prompt_brain/outcome_feedback_ledger.jsonl
?? data/prompt_brain/outcome_stats.json
?? data/prompt_brain/runtime_usage_ledger.jsonl

## Runtime containment
Containment CLEAN
