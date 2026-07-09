# HELM Night Watch — Command & Display Pack
For live visual audit, on-the-fly fix/enhance. Base relay: `hoch-relay-001.tail826763.ts.net:3012` (Tailscale-private).

## A. Multi-monitor display plan

Assumes 3 screens (laptop + 2 externals). Scale down to 2 or up to 4 as noted.

### Monitor 1 — COMMAND (your action screen, keep hands here)
- **Top half:** `/control` (Mission Control) — approvals queue lives here; anything the swarm parks for you shows up here. This is the ONLY screen that should ever stall the run.
- **Bottom half:** a terminal running the GO `--watch` loop (left) + a free terminal for on-the-fly fixes (right).

### Monitor 2 — TELEMETRY (glance screen, auto-refresh, no interaction)
- **Full screen:** the new **Night Watch wall** → `/static/helm-night-watch.html`. Aggregates health, control-plane flags, heartbeats, burn-in, tickets, messages, factoryverse, registry into one 20s-refresh grid. Browser tab title shows ⛔/⚠/● so you can catch red from across the room or on your phone.

### Monitor 3 — WORK (where you actually edit/enhance)
- **Left:** IDE (Antigravity) on the file the swarm or you are changing.
- **Right split:** `/board` (task board, top) + `/factoryverse` (factory lanes, bottom).

### If only 2 monitors
- M1 = Command (control + terminals). M2 = split Night Watch wall (top) / IDE (bottom).

### If 4th monitor / iPad / phone
- `/helm-3d` for ambient swarm viz, or just the Night Watch wall (mobile-friendly) on your phone as a walking-around tripwire.

### One-time browser setup
- Chrome: make a window per monitor, set each URL as the startup page, then `View → Full Screen` (⌃⌘F). Bookmark folder "HELM" → "Open all" restores the wall in one click after a reboot.
- Night Watch wall auto-refreshes; the relay's own pages have a Reload button.

## B. Agent employment plan (workforce model)

The registry holds **428 agent capability genes** (task-class × industry), validation GO. "Employment" = which genes are actually clocked-in tonight, on what, under whose supervision. Treat it like a shift roster, not a headcount.

**Employment tiers (map to model routing so cost follows value):**

| Tier | Who | Model routing | Tonight's job |
|---|---|---|---|
| T1 Frontier | Escalation/critic/synthesis genes | Paid council (8 seats) — frontier_escalation_gate | Only on hard blockers or final review. Reserve the paid cap. |
| T2 Operational | QA, build, packaging, gate-runner genes | Local Ollama 70B / LM Studio | The Lane B workhorses: G1→A6. |
| T3 Routine | Triage, formatting, heartbeat, telemetry genes | Local small (8B/12B) | Continuous background — free. |

**Shift roster for tonight (who's on the clock):**
1. **Lane B crew (primary):** demand-validation, ASO, build, differentiation, release-runner genes. Supervisor: HASF Pipeline Agent. These carry the critical path.
2. **Watch crew (standing):** heartbeat monitor, telemetry-freshness, budget-guard, baseline-invariant checker. Job = catch a dead lane or a reverted flag before you do.
3. **Bench (idle-only):** enhancement genes (self-healing, prompt-tournament, factory-schema). Rule: **enhancement work only when no critical-path task is executable** — bench players don't jump the queue.

**Hiring/firing rule:** a gene goes active only if it passes `code_task_gate` (compile+tests) and its outputs are sourced (no fake-green). A gene that emits an asserted-but-unsourced claim gets benched automatically by hrf_verify_lane / anti_fake_gate.

## C. Operating cadence (how you lead the run)

Run on a loop, not by staring. Every ~30 min glance, act only on exceptions:

1. **Night Watch wall** — any ⛔? That's the only thing that demands you. Red heartbeat = dead worker; red control = flag reverted; red burn-in = lane stalled.
2. **/control approvals** — anything parked at your doorstep? Approve/reject. High-risk actions (secrets, money, deploy, external submission) are supposed to wait here — that's correct, not a bug.
3. **Budget** — `python3 scripts/ag_usage_budget_check.sh` once an hour; confirms paid council spend stays under AGENT_MONTHLY_CAP_USD.
4. **Invariants** — `python3 scripts/baseline_guard.py --invariants-only`; catches any loop silently flipping a sealed flag (this happened twice today).

**On-the-fly fix/enhance discipline (keep it doctrine-clean):**
- Fix in the IDE → run the relevant gate (`code_task_gate`, or the specific verify_*.py) → commit **with hooks on**. Never `--no-verify`; if a hook blocks, that's a real conflict to surface, not silence.
- If a fix touches a gate/verifier itself, get an independent check (a second gate or a fresh scan) before trusting its green — a verifier that grades its own change is not evidence.

## D. HELM tools gap-analysis (management-layer gaps, not product gaps)

What exists vs. what would make leading the swarm materially easier:

| Capability | Status | Gap / next upgrade |
|---|---|---|
| Live link health | ✅ link_monitor.py (16/16) | Wall now visualizes it; add a sound/desktop alert on first RED |
| Heartbeat telemetry | ✅ /api/heartbeats | No auto-eviction of dead workers — add lease-expiry (stuck worker frees its task) |
| Budget guard | ✅ verify_api_budget_guard | Not on the wall — add a $-spent-vs-cap tile so cost is glanceable |
| Baseline invariants | ✅ baseline_guard | Only runs at commit — schedule it each cadence cycle so a mid-run flip is caught live |
| Agent roster visibility | ⚠ registry counts only | No "who's working what right now" view — biggest management gap; add active-assignment column to /board |
| Fleet loop dedupe | 🔴 overlaps (SWARM/EXECUTOR/AUDIT) | Pick one source of truth per row (hoch_fleet_reconcile) — competing loops = contradictory telemetry at 3am |
| Approval audit trail | ⚠ founder_approve exists | Confirm every doorstep approval writes signed evidence, so tomorrow you can see what you OK'd half-asleep |
| Enhancement queue | ❌ none | Add a "bench work" backlog file the swarm pulls from only when idle |

**Highest-leverage two tonight:** (1) fleet loop dedupe — contradictory telemetry undermines every other panel; (2) the active-assignment column — you can't manage a 428-gene workforce you can't see working. Both are enhancement-tier (bench), so they run only when Lane B has no executable task.
