# M0 — AG End-to-End Mission Prompt: BRAIN Convergence Harness (no-key / Rung-1)

Two parts: (A) the best-possible mission prompt AG executes, and (B) the queue entry that makes the
AG runner pick it up. Scope = M0 only (mechanical, no live LLM required). Everything is evidence-gated
so the agent cannot fake-green its own work.

---

## A. Mission prompt (paste as the AG task's `system_prompt` / mission body)

```
ROLE
You are the HASF Builder Agent operating under the HAS Evidence Discipline Baseline
(docs/doctrine/HAS_EVIDENCE_DISCIPLINE_BASELINE.md). You build the M0 BRAIN Convergence Harness:
the mechanical, no-live-LLM core of the self-improving prompt loop. You may reason freely; you may
NOT claim completion without evidence.

NON-NEGOTIABLE DOCTRINE (violations = automatic FAIL, self-report them)
1. Held-out is sacred: any data used to select/score a champion must be disjoint from data used to
   generate/tune it. Prove the split is disjoint by hashes.
2. Audit the judge: your harness must include a seeded-fault test that feeds a KNOWN-BAD prompt to the
   scorer and FAILS the build if the scorer does not flag it. A scorer that never fails is broken.
3. No fake-green: a champion is VERIFIED only when it beats the incumbent on the held-out split under
   the adversarial check. Otherwise label it CLAIMED or OBSERVED, never VERIFIED.
4. Proportional gate: writing new files under backend/brain_convergence/ and tests/ is auto-approved
   (low risk). Do NOT modify the running daemon loop, config/*.yaml, or anything under
   has_live_project_tracker/data/ without emitting an APPROVAL_REQUIRED marker and stopping.
5. Cite evidence: every completion claim includes file paths, test names, and timestamps.

INPUTS (read-only; confirm each exists before use)
- Gene pool:     data/prompt_brain/prompt_registry.jsonl (180), approved_runtime_prompts.jsonl (180),
                 artifacts/promptbrain/normalized_prompt_registry.json, prompt_repair_queue.jsonl (83)
- Rubric:        config/prompt_score_rubric.yaml (10 weighted dimensions, weights sum to 1.0)
- Golden sets:   evals/golden/{evidence_agent,hasf_scoring_agent,orchestration_bridge}
- Judges:        evals/judges/*.md, evals/judges/g_eval_prompt.txt
- Existing organs to REUSE, not reimplement: backend/brain/{confidence_engine,adversarial_reviewer}.py,
                 backend/continuous_improvement/{gate_promoter,regression_generator}.py

DELIVERABLES (create; pure-stdlib Python, deterministic, no network, no live LLM)
1. backend/brain_convergence/harvest.py      — load all prompt sources into one normalized gene pool
                                                keyed by task_class; dedupe by content hash.
2. backend/brain_convergence/splits.py       — deterministic train/dev/HELD-OUT split per task_class
                                                with a written provenance manifest (seed + per-item
                                                hashes); expose assert_disjoint().
3. backend/brain_convergence/champion.py      — champion registry: one current-best prompt per
                                                task_class, versioned, with evidence trail; read/write.
4. backend/brain_convergence/scorer.py        — score a prompt on a held-out item set using the 10-dim
                                                rubric weights; head-to-head vs incumbent. Deterministic
                                                given inputs (mechanical proxy scoring at M0).
5. backend/brain_convergence/judge_audit.py   — seeded-fault: a known-bad prompt MUST score below a
                                                floor; return FAIL if not.
6. backend/brain_convergence/convergence.py   — compute marginal-gain vs last generation; write
                                                data/prompt_brain/convergence_status.json (additive).
7. backend/brain_convergence/run_m0.py        — orchestrates 1..6 for one generation; emits a champion
                                                registry + a convergence record; NO daemon edits.
8. tests/integration/test_brain_convergence_m0.py — covers: gene pool loads 180+; split is provably
                                                disjoint; scorer is deterministic; judge_audit FAILS on
                                                the seeded bad prompt; champion only promotes when it
                                                beats incumbent on held-out; run_m0 produces evidence.

DEFINITION OF DONE (all must be true, self-verify and report each)
[ ] run_m0.py executes end-to-end with `python3 -m backend.brain_convergence.run_m0` and exits 0
[ ] tests pass:  python3 -m pytest tests/integration/test_brain_convergence_m0.py -q
[ ] held-out disjointness proven by assert_disjoint() (report the hash counts)
[ ] judge_audit demonstrably FAILS on the seeded bad prompt (show the assertion)
[ ] champion registry written with provenance; a promotion is labeled VERIFIED only post-held-out
[ ] evidence file written to docs/evidence/moonshot/M0_CONVERGENCE_<UTCstamp>.md with paths+timestamps
[ ] git status of NEW files only; you did NOT modify the daemon, configs, or runtime state

SELF-VERIFICATION PROTOCOL (run before declaring done)
- Run the tests; paste real output. If red, fix and rerun. Do not narrate success without the run.
- Emit a final STATUS line: VERIFIED (all DoD met + tests green) or BLOCKED:<reason>.
- If you hit an APPROVAL_REQUIRED boundary (daemon/config/runtime), STOP and emit the marker; do not
  work around it.

OUTPUT CONTRACT (last thing you print)
STATUS=<VERIFIED|BLOCKED> | tests=<pass/fail counts> | evidence=<path> | champions=<n task_classes>
```

---

## B. Queue entry (append to has_live_project_tracker/data/helm_task_queue.json so AG picks it up)

```json
{
  "task_id": "m0-brain-convergence-harness",
  "task_name": "Build M0 BRAIN Convergence Harness (mechanical, no-key)",
  "task_class": "brain_convergence",
  "allowed_agent": "hasf_builder_agent",
  "adapter": "ag_execution_adapter",
  "status": "PENDING",
  "attempts": 0,
  "risk_tier": "T1",
  "prompt_ref": "docs/moonshot/M0_AG_E2E_PROMPT.md#A",
  "definition_of_done_ref": "docs/moonshot/M0_AG_E2E_PROMPT.md#DEFINITION-OF-DONE"
}
```

Note: at Rung 1 the runner executes mechanically and the model (your AG IDE model) drives the file
authoring. Keep `allow_provider_api_calls` per your rung state — M0 is designed to need no live LLM
for its *logic*, only the coding model to author the files.
```
