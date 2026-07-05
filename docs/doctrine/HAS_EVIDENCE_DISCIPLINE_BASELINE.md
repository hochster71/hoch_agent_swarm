# HAS Evidence Discipline Baseline

* **Status**: MANDATORY / repo-wide enforcement.
* **Core Rule**: Any capable model may contribute. Only evidence-disciplined execution may ship.
* **Scope**: Applies to every agent, QA runner, gate, and dashboard in Hoch Agent Swarm (HAS) and HASF.
* **Durable asset**: The operating doctrine and its enforcement machinery — not any single model version.

---

## 0. Why this exists

A strong model can still produce weak output if the execution protocol is loose. The
durable performance advantage of HAS comes from the enforced operating doctrine, not from a
model version. Swap Opus 4.8 for a local 7B and the guards must still catch fake-green. This
document is the operating law that makes that true.

Related enforcement already in the repo (this doctrine binds them together, does not replace them):

* `config/has_operating_doctrine.yaml` — top-level operating principles
* `config/claim_evidence_policy.yaml` — which claims require which evidence
* `config/completion_gates.yaml` — which change types require which gates
* `config/confidence_policy.yaml` — evidence-weighted confidence caps
* `config/fake_completion_terms.yaml` — banned fake-green vocabulary
* `config/goal_completion_contract.json` — north-star completion definition
* `config/runtime_truth_contract.json` — source-of-truth hierarchy + label-state machine (companion to this doc)

---

## 1. Enforcement is binding; instruction is advisory

A system prompt is advisory. A gate is binding. Every model — Opus 4.8 included — will violate
behavioral instructions under load, mid-task, when context gets long.

**The doctrine is real only where compliance is checked by non-model code:**

* the release-readiness guard that refuses promotion when evidence paths are missing,
* the QA runner that injects seeded faults and fails the build if they are not caught,
* the ledger schema that has no field for "trust me."

Portability restated: **the doctrine is portable because compliance is checked outside the model.**
That is what makes the model replaceable — not the prose, the gate.

---

## 2. The ten evidence rules

1. No assertion is production-valid unless grounded in observable evidence: source citation, test output, runtime telemetry, or operator-approved context.
2. UNKNOWN is an acceptable state. It must never be silently converted into assumed success.
3. Green status requires verification, not narrative confidence.
4. Seeded-fault gates must prove QA can detect intentional failures before any pass result is accepted.
5. UI state is not authoritative unless backed by live runtime data.
6. Agents must label facts, assumptions, risks, blockers, and inferred conclusions separately.
7. Completion claims must include evidence paths, timestamps, test names, and validation status.
8. The doctrine is model-portable. Claude, GPT, Grok, Gemini, local, and future models may participate only if they obey the same evidence rules, checked by the same gates.
9. Fake-green, stale telemetry, uncited claims, and untested success states are release blockers.
10. The durable asset is the operating doctrine, not any single model version.

---

## 3. Anti-gaming clause (evidence quality)

Evidence discipline is itself gameable. An agent under pressure will produce evidence that
technically exists but proves nothing — a test that asserts `true`, telemetry from a stale run,
a citation to a doc that does not say what is claimed. Seeded faults defend the *detector*; they
do not defend *evidence quality*. Therefore:

1. **Verification must be adversarial to the thing being verified.** A test written by the agent that produced the code does not, alone, satisfy a gate; it must be paired with a negative/failure-mode test.
2. **The seeded-fault suite is itself audited on a cadence.** A QA harness that never fails is indistinguishable from one that is broken. Rotate seeded faults and confirm they are caught; a stale-passing harness is a blocker.
3. **Citations are resolved, not asserted.** A cited artifact must be re-read to confirm it states what the claim says; a dead or mismatched citation fails the gate.
4. **Telemetry has a freshness budget.** Evidence older than its budget (see `runtime_truth_contract.json`) is treated as STALE, not VERIFIED.

---

## 4. Proportionality tier (verification scales with blast radius)

Full evidence discipline on every action is unaffordable and self-defeating — it makes the swarm
slow and expensive enough that people route around it, which is how doctrines die. Verification
depth scales with blast radius.

| Tier | Example actions | Minimum verification |
|------|-----------------|----------------------|
| **T0 — Read-only** | queries, reads, reports | source cited or telemetry labeled; no gate blocking |
| **T1 — Reversible local change** | code/docs edits, local build | file diff + unit test + clean status |
| **T2 — Stateful / integration** | schema migration, service wiring, config policy change | T1 + E2E + seeded-fault pass + rollback path |
| **T3 — Irreversible / external** | production deploy, tag movement, money/send/secrets, public exposure | T2 + security scan + **operator approval** (see `goal_completion_contract.json` blocked-without-approval list) |

"No assertion is production-valid unless grounded in evidence" holds at every tier; only the
*depth* of required evidence changes.

---

## 5. Source-of-truth hierarchy

"UI is not authoritative" only means something once what *is* authoritative is named. When two
sources disagree, the higher-ranked source wins:

1. **Runtime telemetry** (live, within freshness budget)
2. **Test output** (from an adversarial/negative-inclusive suite)
3. **Operator assertion** (human-approved context)
4. **Agent inference** (lowest; never sufficient alone for T1+)

UI/dashboard state is a *rendering* of these sources, never a source itself. Full definition and
freshness budgets live in `config/runtime_truth_contract.json`.

---

## 6. Label-state machine

Every status shown to a human or written to the ledger carries exactly one state. This is the
schema that makes "runtime truth ≠ UI state" concrete and queryable.

| State | Meaning | Ledger requirement |
|-------|---------|--------------------|
| `CLAIMED` | An agent asserts it; not yet checked | source = agent inference |
| `OBSERVED` | Seen in a run, not adversarially verified | telemetry or test reference |
| `VERIFIED` | Passed adversarial verification within freshness budget | evidence paths + timestamps + test names |
| `STALE` | Was verified, but evidence exceeded its freshness budget | prior evidence + expiry reason |
| `UNKNOWN` | Not established either way | must not render as green |
| `BLOCKED` | A gate refused promotion | blocking gate + missing evidence |

Only `VERIFIED` may render as green. `CLAIMED`, `OBSERVED`, `STALE`, `UNKNOWN`, and `BLOCKED`
must be visually distinct from green in any dashboard.

---

## 7. Binding into the control plane

| Layer | Required behavior |
|-------|-------------------|
| Agent prompts | Cite, test, label uncertainty, refuse fake-green |
| QA gates | Include seeded faults and negative tests; audit the fault suite on cadence |
| UI dashboard | Show truth source, timestamp, and label state; never green unless `VERIFIED` |
| Runtime commander | Block promotion if evidence is missing or below tier requirement |
| Release readiness | Distinguish `CLAIMED`, `OBSERVED`, `VERIFIED`, `STALE`, `UNKNOWN`, `BLOCKED` |
| Revenue packaging | Sell the doctrine as the reliability differentiator |

---

## 8. Baseline principle

> Any capable model can contribute. Only evidence-disciplined execution can ship.
>
> Any agent may reason. No agent may claim completion without evidence. Unknown remains unknown
> until verified. Green status requires adversarial validation. UI state is not truth unless
> backed by live runtime evidence.
