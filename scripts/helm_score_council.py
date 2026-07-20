#!/usr/bin/env python3
"""HELM autonomous cross-model scoring runner.

One task in → HELM fans it to EVERY lane (Orchestrator / Builder / Auditor / Local),
collects each model's answer, then the Auditor scores them all against HELM doctrine and
real runtime state: scorecard, ranking, disagreements, synthesis, recommended action.

    python3 scripts/helm_score_council.py "What is the highest-value next move to GOAL?"
    python3 scripts/helm_score_council.py --task "..." --save

NO FAKE GREEN: if every lane is blocked, it reports that instead of inventing scores.
Runs headless (cron/autoloop friendly) — this is the autonomous path, no founder paste-in.
"""
import sys, os, json, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.pop("ANTHROPIC_API_KEY", None)  # keep Claude on flat Max billing


def main() -> int:
    args = [a for a in sys.argv[1:]]
    save = "--save" in args
    args = [a for a in args if a != "--save"]
    if args and args[0] == "--task":
        args = args[1:]
    task = " ".join(args).strip()
    if not task:
        print(__doc__)
        return 2

    from backend.dispatch.council_router import score_council
    print(f"\n▸ HELM autonomous scoring — fanning task to every lane…\n  task: {task[:120]}\n")
    res = score_council(task)

    for m in res.get("models", []):
        mark = "✓" if m.get("ok") else "✗"
        print(f"  {mark} {m.get('member','?'):<14} lane={m.get('role','?'):<13} "
              f"model={m.get('model','?'):<22} {m.get('chars',0)} chars")

    print(f"\n▸ Scored {res.get('scored_count',0)} responses "
          f"(scorer: {(res.get('scorer') or {}).get('model','?')})\n")
    if res.get("ok"):
        print(res.get("scorecard") or "(empty scorecard)")
    else:
        print(f"✗ SCORING BLOCKED: {res.get('error')}\n  {res.get('note','')}")

    if save:
        out = ROOT / "coordination" / "council"
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        p = out / f"score_{ts}.json"
        p.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
        print(f"\n  saved → {p.relative_to(ROOT)}")
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
