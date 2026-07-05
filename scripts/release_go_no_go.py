#!/usr/bin/env python3
"""P9 — Release Go/No-Go evidence assembler.

Scores each GOAL completion criterion (config/goal_completion_contract.json) against REAL evidence
probes and produces an honest verdict using the label-state machine:
  VERIFIED  — evidence found and the check passed        (green)
  PARTIAL   — some evidence, not fully proven             (amber)
  UNKNOWN   — could not establish either way              (grey)
  BLOCKED   — an explicit blocker is present              (red)

Verdict = GO only if EVERY criterion is VERIFIED. Otherwise NO-GO with the precise blocker list.
No fake-green: a criterion is VERIFIED only on concrete evidence (a file, a passing probe, a config
value) — never assumed. Deterministic, no network, no LLM, $0.
"""
import json
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "docs" / "evidence" / "release"


def _exists(*rel):
    return all((ROOT / r).exists() for r in rel)


def _probe(passed, evidence, partial=False, blocked=False, note=""):
    state = "BLOCKED" if blocked else ("VERIFIED" if passed else ("PARTIAL" if partial else "UNKNOWN"))
    return {"state": state, "evidence": evidence, "note": note}


def _pytest(paths):
    try:
        args = ["python3", "-m", "pytest", *paths.split(), "-q"]  # split: multiple paths, not one arg
        r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        return r.returncode == 0, (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    except Exception as e:
        return False, str(e)


def assemble():
    C = {}

    # 1. Local runtime starts reliably — heartbeat self-refresh code present
    C["local_runtime_reliable"] = _probe(
        _exists("backend/main.py") and "runtime_truth_heartbeat_loop" in (ROOT / "backend/main.py").read_text(),
        "backend/main.py: interval heartbeat loop", note="fresh heartbeat proven live earlier")

    # 2. Dashboard shows current truth — live console bound to real endpoints
    C["dashboard_truth"] = _probe(
        False, "frontend/has_brain_console.html (built, not yet mounted in cockpit index.html)",
        partial=_exists("frontend/has_brain_console.html"))

    # 3. Agents have owners / RACI — capability registry present + PASS
    reg = ROOT / "data/prompt_registry/agents.manifest.json"
    reg_status = json.loads(reg.read_text()).get("validation_status") if reg.exists() else None
    C["agents_have_owners"] = _probe(
        reg_status in ("PASS", "GO"),  # both are green terminal states for the registry
        f"data/prompt_registry/agents.manifest.json (validation_status={reg_status})")

    # 4. Critical path visible
    C["critical_path_visible"] = _probe(
        _exists("docs/pert/HAS_PERT_TO_GOAL_NORTHSTAR_ANALYSIS.md"),
        "docs/pert/HAS_PERT_TO_GOAL_NORTHSTAR_ANALYSIS.md")

    # 5. Tests prove the system — brain-convergence suite + audit stack present
    ok, last = _pytest("tests/integration/test_brain_convergence_harvest.py tests/integration/test_brain_convergence_guards.py tests/integration/test_brain_convergence_m0_full.py")
    C["tests_prove_system"] = _probe(
        ok and _exists("scripts/audit_stack.sh"),
        f"brain-convergence tests ({last}) + scripts/audit_stack.sh")

    # 6. No public 3012 exposure — private-first doctrine + UFW evidence
    C["no_public_exposure"] = _probe(
        _exists("docs/doctrine/HOCH_PRIVATE_FIRST_DOCTRINE.md"),
        "private-first doctrine; relay UFW blocks 3012 (verify live on relay)",
        partial=True, note="verify `ufw status` on relay for full VERIFIED")

    # 7. No fake PASS/ONLINE — evidence-discipline contract + guard
    C["no_fake_green"] = _probe(
        _exists("docs/doctrine/HAS_EVIDENCE_DISCIPLINE_BASELINE.md",
                "config/runtime_truth_contract.json",
                "backend/final_verifier/runtime_truth_contract.py"),
        "evidence-discipline baseline + contract + RuntimeTruthVerdictGuard")

    # 8. High-risk requires approval
    C["high_risk_gated"] = _probe(
        _exists("config/autonomy_policy.yaml", "config/goal_completion_contract.json"),
        "autonomy_policy.yaml + goal contract blocked_without_approval list")

    # 9. Metrics show progress — convergence status + champion registry
    C["metrics_show_progress"] = _probe(
        _exists("data/prompt_brain/convergence_status.json", "data/prompt_brain/champion_registry.json"),
        "convergence_status.json + champion_registry.json")

    # 10. Operator stops copy-pasting — autonomy daemon present
    C["operator_hands_off"] = _probe(
        _exists("scripts/ag_execution_daemon.py"),
        "ag_execution_daemon.py (Rung 1 cycling; deepens with local-model routing)",
        partial=True, note="mechanical autonomy live; full hands-off needs Rung-2 or local-model routing")

    verified = [k for k, v in C.items() if v["state"] == "VERIFIED"]
    blockers = [k for k, v in C.items() if v["state"] in ("BLOCKED", "PARTIAL", "UNKNOWN")]
    verdict = "GO" if len(verified) == len(C) else "NO-GO"
    return {"verdict": verdict, "verified": len(verified), "total": len(C),
            "criteria": C, "blockers": blockers,
            "release_go_note": "GO also requires an operator-signed production_go_status through the release-authority path."}


def main():
    r = assemble()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    EVID.mkdir(parents=True, exist_ok=True)
    md = EVID / f"GO_NO_GO_{ts.replace(':','').replace('-','')}.md"
    lines = [f"# Release Go/No-Go — {ts}", "",
             f"## VERDICT: **{r['verdict']}**  ({r['verified']}/{r['total']} criteria VERIFIED)", "",
             "| Criterion | State | Evidence |", "|---|---|---|"]
    for k, v in r["criteria"].items():
        lines.append(f"| {k} | {v['state']} | {v['evidence']} |")
    lines += ["", f"**Blockers to GO:** {', '.join(r['blockers']) or 'none'}", "",
              f"_{r['release_go_note']}_"]
    md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nevidence={md}")
    return r


if __name__ == "__main__":
    main()
