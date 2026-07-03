# HAS/HASF L3 QA Maturity PERT Baseline

This document locks the PERT baseline and critical path structure for transitioning HAS/HASF/HELM from L2 autonomous execution to L3 evaluated/reliable autonomy.

---

## 1. Network Table Summary

| Task ID | Task Description | Dependencies | Estimate (Hours) | Variance Risk |
|---|---|---|---|---|
| **C** | Agent Lifecycle Transitions | None | 6.0 | Low |
| **D** | Golden Datasets Formulation | C | 8.0 | High (Risk D) |
| **E** | Eval Harness Development | D | 10.0 | High (Risk E) |
| **F** | G-EVAL Gate Wiring | E | 4.0 | Low |
| **K** | Planted-Failure Proofs & Battery | F | 3.0 | Low |
| **L** | Integration Audit & Walkthrough | K | 2.5 | Low |
| **Q** | Final Production Sign-off | L | 2.2 | Low |
| **O** | 14B Model Bring-up | Parallel | 12.0 | High (Risk O) |

---

## 2. Critical Path

* **Critical Path Sequence**: **C → D → E → F → K → L → Q**
* **Phase 1+2 Total Estimate (TE)**: `35.7` focused labor hours.
* **Phase 1+2 95% Confidence Limit**: `~43` focused labor hours.
* **Full Build Total Estimate (TE)**: `53.2` focused labor hours.
* **Full Build 95% Confidence Limit**: `~62` focused labor hours.
* **Product 002 R2+ Earliest Unblock**: `41.2` focused labor hours.

---

## 3. Variance Risks & Mitigation

1. **Risk O (14B Model Performance)**: Low latency/throughput on EPYC CPUs.
   * *Mitigation*: Run 14B model validation tasks in parallel off the critical path, utilizing LM Studio fallback to preserve G-EVAL capability.
2. **Risk E (Harness Complexity)**: Divergence in model outputs.
   * *Mitigation*: Layered integration starting with deterministic validation checks (E1).
3. **Risk D (Golden Case Formulation Overhead)**: Gaining full founder alignment.
   * *Mitigation*: **Founder-Review Batching**. Segment cases into Batch 1 (initial unblock) and Batch 2 (full G-EVAL verification).
