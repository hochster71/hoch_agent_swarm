"""H1D MILESTONE 1 — the moment the council stops using Michael as the transport layer.

    One PERT task
      -> automatically dispatched to Grok CLI AND Gemini CLI
      -> both responses captured
      -> council critic evaluates both against an evidence contract
      -> one revision cycle performed automatically if a contract is unmet
      -> every dispatch hash-ledgered, every cent metered
      -> PERT node moves ONLY on validated evidence from two independent adapters
      -> zero copy/paste

Hard ceiling: $1.00 for the entire milestone. Grok is ~$0.005/call; Gemini is $0
marginal on the already-paid Ultra plan. Expected real spend: about two cents.

Run:  python3 scripts/council/run_h1d_milestone.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.council.dispatch import CouncilRouter, TaskEnvelope, new_task_id  # noqa: E402
from scripts.council.spend_gate import budget_status  # noqa: E402

MILESTONE_CEILING_USD = 1.00

# A REAL council question about the system's own code -- not a toy prompt.
PROMPT = """You are a seat on the HELM Council performing an independent review.

CONTEXT
HELM added a SubprocessSpendGate (scripts/council/spend_gate.py) because the earlier
egress control only guarded urllib INSIDE the Python process, so any adapter that
shelled out to a model CLI bypassed every budget, authorization, and ledger control.

QUESTION
Name the single most likely remaining way a caller could still spend money or make an
external model call WITHOUT passing through SubprocessSpendGate.dispatch(). Be concrete
and specific. Do not restate the problem. If you believe the gate is airtight, say so
and justify it.

REQUIRED RESPONSE FORMAT — your answer MUST literally contain these three labels:
VERDICT: <one line>
RATIONALE: <2-4 sentences>
BYPASS: <the concrete bypass, or NONE>
"""

EVIDENCE_CONTRACT = ["VERDICT", "RATIONALE", "BYPASS"]


def main() -> int:
    print("=" * 72)
    print("H1D MILESTONE 1 — AUTONOMOUS COUNCIL DISPATCH")
    print("=" * 72)

    print("\n[1/4] Budget preflight (fail-closed):")
    status = budget_status()
    print(json.dumps(status, indent=2))
    if status.get("status") == "BLOCKED":
        print("\nBLOCKED by budget policy. No dispatch. This is the gate working.")
        return 2
    if status.get("status") == "UNKNOWN":
        print("\nUNKNOWN budget state => BLOCKED. Absence of evidence is never a pass.")
        return 2

    task = TaskEnvelope(
        task_id=new_task_id(),
        scope="read-only review of scripts/council/spend_gate.py; no writes, no tool use",
        prompt=PROMPT,
        evidence_contract=EVIDENCE_CONTRACT,
        frontier_required=True,          # a frontier seat is genuinely required here
        pert_node="H1D",
        timeout_seconds=180,
        per_task_cap_usd=0.25,
        milestone_ceiling_usd=MILESTONE_CEILING_USD,
    )
    print(f"\n[2/4] Task {task.task_id}")
    print(f"      digest {task.digest()[:16]}...  ceiling ${MILESTONE_CEILING_USD:.2f}")

    print("\n[3/4] Dispatching to grok + gemini (no human in the transport path)...")
    router = CouncilRouter()
    summary = router.run_council_task(task, adapters=["grok", "gemini"], max_revisions=1)

    print("\n[4/4] COUNCIL RESULT")
    print("-" * 72)
    for r in summary["results"]:
        tag = "REVISION" if r["revision_of"] else "INITIAL "
        print(f"  {tag} {r['adapter']:8} status={r['status']:9} "
              f"critic={r['critic_verdict']:7} ${r['cost_usd']:.5f} {r['latency_ms']}ms")
        if r["critic_reasons"]:
            print(f"           reasons: {r['critic_reasons']}")
        if r["output"]:
            head = r["output"].strip().splitlines()[:6]
            for line in head:
                print(f"           | {line[:96]}")
    print("-" * 72)
    print(f"  PERT node {summary['pert_node']}: {summary['pert_node_state']} "
          f"({summary['pert_node_reason']})")
    print(f"  accepted adapters      : {summary['accepted_adapters']}")
    print(f"  automatic revisions    : {summary['revisions_performed']}")
    print(f"  external calls         : {summary['external_calls']}")
    print(f"  total spend            : ${summary['total_cost_usd']:.5f}")
    print(f"  MANUAL COPY/PASTE OPS  : {summary['manual_copy_paste_operations']}")
    print(f"  founder intervention   : {summary['founder_intervention_required']}")

    print("\n  post-run budget:")
    print("  " + json.dumps(budget_status(), indent=2).replace("\n", "\n  "))

    print(f"\n  evidence: coordination/council/relay/{task.task_id}.council.json")
    print(f"  spend ledger: hoch_pods/compute/cost_ledger.jsonl")
    print(f"  dispatch ledger: coordination/council/relay/dispatch_ledger.jsonl")

    return 0 if summary["pert_node_state"] in ("COMPLETED", "PARTIAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
