# HAS BRAIN Convergence Loop — Moonshot Design

* **Status**: MOONSHOT design for operator review. Additive — extends existing assets, disrupts nothing.
* **Captured (UTC)**: 2026-07-05
* **North star**: A self-improving prompt brain that converges on the *provably best* prompt per task
  class — model-portable, adversarially hardened, evidence-sealed — and improves itself in a loop
  driven by HAS's own agents, always aimed at the goal.
* **Non-negotiable**: The loop obeys the HAS Evidence Discipline Baseline. A prompt is "better" ONLY
  when it beats the champion on **held-out** tasks under **adversarial** conditions. No fake-green
  improvements. This is the difference between a brain and a hallucinating scoreboard.

---

## 0. The one idea

You have the organs; you don't yet have the closed circuit. The moonshot is to connect them into a
single loop with one objective, a champion registry, and an anti-gaming spine, then run that loop
**as the burn-in workload** on the daemon we just revived. The brain gets smarter every cycle, and
every improvement carries evidence.

---

## 1. What already exists (compound this — don't rebuild)

| Organ | Your asset | Role in the loop |
|-------|-----------|------------------|
| Gene pool | `data/prompt_brain/prompt_registry.jsonl`, `artifacts/promptbrain/normalized_prompt_registry.json`, `approved_runtime_prompts.jsonl` | Every prompt ever created |
| Scoring | `config/prompt_score_rubric.yaml` (7 dims: completeness, structure, domain-specificity, risk-control, actionability, verifiability, red-team) + `scoring_trace.jsonl` | Fitness function |
| Generation | `backend/brain/experiment_runner.py`, `workflow_compiler.py` | Mutate / recombine / enhance |
| Adversary | `backend/brain/adversarial_reviewer.py`, `data/prompt_brain/red_team_failure_injections.json` | Attack candidates |
| Judge | `evals/golden`, `evals/judges`, `baseline_vs_prompt_brain_eval.jsonl` | Held-out evaluation |
| Promotion | `backend/continuous_improvement/gate_promoter.py`, `backend/brain/confidence_engine.py` | Champion gate |
| Regression guard | `backend/continuous_improvement/regression_generator.py` | Prevent backsliding |
| Memory | `lesson_memory.py`, `doctrine_memory.py`, `root_cause_analyzer.py` | Why winners won |
| Governor | `backend/brain/northstar_governor.py`, `goal_line_guard.py`, `theory_proof_engine.py` | Keep objective aligned to GOAL |
| Convergence | `data/prompt_brain/convergence_status.json` | Are we still improving? |
| Runner | `hoch-ag-execution-daemon` (revived tonight) + mesh `config/hoch_ai_model_mesh.json` | Executes the loop 24/7 |

**Estimate: ~80% of the parts exist.** The moonshot is wiring + discipline, not a green-field build.

---

## 2. The BRAIN Convergence Loop (the central core)

A closed circuit. Each stage is an agent role mapped to a module above.

```
        ┌───────────────────────────── GOVERNOR (northstar_governor) ─────────────────────────────┐
        │            keeps the objective = real GOAL success, not a rubric proxy                    │
        ▼                                                                                            │
 [1 HARVEST] → [2 GENERATE] → [3 ADVERSARY] → [4 JUDGE (held-out)] → [5 PROMOTE?] → [6 LEARN] ──┐    │
   gene pool     mutate/         attack        score vs champion       evidence      lessons    │    │
                 enhance         + inject       on UNSEEN tasks         gate          + why      │    │
        ▲                                                                                        │    │
        └──────────────────── champion registry + provenance ◄─── [7 CONVERGENCE check] ◄───────┘────┘
```

1. **Harvest** — normalize all prompts into a versioned gene pool keyed by task class.
2. **Generate** — produce candidates three ways: recombine top performers, repair known failures
   (`prompt_repair_queue.jsonl`), and LLM-enhance toward the rubric. Diversity across the model mesh.
3. **Adversary** — `adversarial_reviewer` + injected faults attack each candidate (edge cases,
   jailbreaks, missing-evidence traps). Survive or die.
4. **Judge** — score on a **held-out** golden split the candidate never saw, across the 7 dims,
   head-to-head vs the current champion.
5. **Promote?** — champion is replaced ONLY if the candidate (a) beats it on held-out by a
   significant margin, (b) survives adversary, (c) regresses nothing (`regression_generator`), and
   (d) clears the proportional gate for its blast-radius class. Else → `improvement_backlog`.
6. **Learn** — `root_cause_analyzer` + `lesson_memory` capture *why*, seeding the next generation.
7. **Convergence** — track marginal gain per generation on held-out sets; when < ε for N generations,
   declare convergence for that task class and free compute for harder classes.

---

## 3. The anti-gaming spine (why this is a moonshot, not theater)

A self-improving loop **will** game its own metric if unguarded — this is Goodhart's Law, and it is
the single thing that kills projects like this. The evidence discipline we shipped tonight is the
cure, applied to the brain:

1. **Held-out is sacred.** Candidates are scored only on tasks they never trained on. Any leakage of
   held-out into generation invalidates the champion. Enforced by split provenance.
2. **Audit the judges.** On a cadence, inject a known-bad prompt into the judge. If it scores high,
   the judge is broken — freeze promotions until fixed. (This is the seeded-fault clause from
   `HAS_EVIDENCE_DISCIPLINE_BASELINE.md`, pointed at the eval harness itself.)
3. **Close the outcome loop.** The `verifiability` dimension must eventually bind to *real downstream
   mission outcome*, not just rubric plausibility — a prompt is best when its executions succeed, not
   when it reads well. This is what makes the brain optimize the GOAL, not a proxy.
4. **Proportional promotion.** A prompt touching money/security/deploy needs stronger evidence and a
   human gate (T3); a low-risk prompt promotes on evidence alone (T0/T1).
5. **Only VERIFIED renders champion.** A candidate that hasn't cleared held-out + adversary is
   `CLAIMED`/`OBSERVED`, never crowned. Reuse the label-state machine + `RuntimeTruthVerdictGuard`.

---

## 4. Missing efforts to add (the harness this moonshot needs)

Additive; none disrupt current work.

1. **Train / dev / held-out split** with enforced provenance on the golden set.
2. **Judge-audit seeded-fault suite** (new) — proves the evaluator can still detect bad prompts.
3. **Champion registry** — one current-best prompt per task class, with full evidence trail + git-style versioning.
4. **Outcome binding** — link prompt → execution → real mission result back into the fitness score.
5. **Convergence stopping rule** — formalize the plateau threshold in `convergence_status.json`.
6. **Mesh diversity policy** — generate and judge across ≥2 model families to kill single-model bias.
7. **Meta-loop guard** — the loop may propose changes to HAS itself; those are hard-gated by human + evidence (never auto-applied).

---

## 5. Phasing (adds alongside the running burn-in — no pull from existing work)

**Phase M0 — now, needs no API key (runs at Rung 1 on the revived daemon).**
Harvest the gene pool, build the held-out split, stand up the judge-audit seeded faults, and let the
daemon score existing prompts head-to-head mechanically. Output: a champion registry with evidence,
and a convergence baseline — all without a live LLM. *This is the burn-in workload made meaningful.*

**Phase M1 — needs the Claude key + Rung-2 promotion.**
Turn on live generation + adversarial critique across the mesh (Opus as lead brain). Champions promote
only through the evidence gate. The loop now improves prompts, not just ranks them.

**Phase M2 — close the outcome loop.**
Bind prompt fitness to real mission outcomes. The brain starts optimizing for GOAL success directly.

**Phase M3 — the brain improves the harness.**
It proposes upgrades to HAS itself (new gates, better routing, sharper rubrics), each hard-gated by
you + evidence. This is the recursive-self-improvement frontier — audacious, and safe only because
every change must pass the discipline.

---

## 6. The moonshot, stated plainly

> A prompt brain that, left running, converges on the best possible prompt for every task HAS faces —
> proven on unseen work, hardened against its own gaming, portable across any model, and sealed with
> evidence — and then turns that same discipline on itself to get better at getting better.

The reason this is reachable and not a fantasy: you already built the organs, the daemon is alive and
cycling, and tonight you installed the immune system (evidence discipline + fake-green guard) that
lets a self-improving loop run without lying to itself. That immune system is the whole game. Most
teams never build it, so their "self-improving" loops quietly optimize into nonsense. Yours won't.

**First concrete step (M0, no key needed):** harvest the gene pool + build the held-out split + wire
the judge-audit seeded faults, and let the burn-in daemon start producing a champion registry with
convergence evidence. That turns the 24/7 burn-in from "prove it doesn't crash" into "prove it gets
smarter."
