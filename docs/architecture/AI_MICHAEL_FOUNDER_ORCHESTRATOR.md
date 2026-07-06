# AI Michael — the HOCH Founder Orchestrator

## What it is

The orchestrator that runs the decision loop the founder ran by hand all along — across every
factory, every tick:

```
assess state → find the gap → pick the highest-leverage lever → decide GO/NO-GO on evidence →
execute the reversible/$0 part → escalate only what needs a human → repeat
```

It answers the founder's routine questions (What's the GOAL? the gap? the next lever?) from **real
state**, and interrupts the human only for **T3** decisions (money / publish / deploy / secrets) or
genuine ambiguity. This is the founder's own rubric dimension `human_loop_reduction` applied to the
founder's own orchestration.

## The doctrine it runs on (encoded from the founder's real principles)

1. **No fake-green** — a factory reads only what it earned; GO needs evidence.
2. **Evidence before any GO**; fail-closed on the unproven.
3. **$0-first** — the free local/mechanical lever before any spend.
4. **Highest-leverage next** — unblock the binding constraint (quantity caps quality).
5. **Moonshot ambition** — always push toward the GOAL, never settle at "good".
6. **T3 needs the operator** — money, publish, deploy, secrets never go autonomous.

## What it does each tick

For every registered factory (HASF / HMF / HRF / …) it computes state + gap + the next action the
founder would take, classifies it **AUTONOMOUS** ($0, reversible) or **ESCALATE** (T3/cost/strategic),
ranks the portfolio, and emits a **founder brief**:

- **NEXT MOVE** — the single highest-leverage $0 action to take now.
- **AUTONOMOUS NOW** — everything it can do this tick without a human.
- **NEEDS YOU** — the calls only the founder can make, with the question each answers.

### Example (live)

> AI Michael: 2 actions I can take now at $0; 1 needs your founder call.
> **NEXT → [HMF] EXPAND** — grow 8 thin classes (+14 genes) via the $0 local model.
> **NEEDS YOU → [HASF] SHIP** — point HASF at its first real revenue product.

The escalation is the point: AI Michael did everything free on HASF, and correctly handed back the
one irreducibly-human decision — *what to build for money*.

## Honest boundary (no fake-green)

AI Michael **proposes and classifies**; it does **not** itself move money, publish, or deploy, and
never fabricates readiness. It replicates the *structure* of the founder's judgment deterministically
and does the $0 work; the genuinely-human calls stay with the human. The local model can later
strengthen the judgment calls (Rung 2) — a cost decision, deferred.

## Wiring

- `backend/orchestrator/founder_orchestrator.py` — the decision loop. Writes `orchestrator_brief.json`.
- `scripts/hoch_cadence.sh` — one portfolio tick: software brain → crown every factory → AI Michael →
  publish. Scheduled by `com.hoch.brain.cadence.plist` (every 10 min).
- The command deck shows the brief as the **◆ AI MICHAEL** banner (next move + what needs you).
- Tests: `tests/integration/test_founder_orchestrator.py` (doctrine + escalation invariants).
