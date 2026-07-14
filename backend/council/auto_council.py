"""Self-orchestrating council. The founder is NOT the message bus.

Before: Michael pasted Claude's output into Grok, Grok's audit back into Claude, ChatGPT's
review into both. Every model-to-model handoff cost founder-minutes -- the exact quantity the
North Star exists to minimise.

Now:
    target -> CouncilDispatchGateway -> Grok (adversarial, read-only, no tools)
           -> findings
           -> DETERMINISTIC ADJUDICATION (a test decides, never a model)
           -> CONFIRMED  -> remediation task queued for the autonomous factory
           -> REJECTED   -> discarded with evidence
           -> UNPROVABLE -> escalated to Michael, deduped

THE RULE THAT PROTECTS FOUNDER-MINUTES:
    If the system can PROVE the answer, it MUST NOT ask.
    Escalation is for judgment, never for verification.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.council.authority_gateway import bind_classification, dispatch_grok, AuthorityDenied
from backend.council.founder_model import Escalation, escalate, classify_action, Authority

VERDICTS = ROOT / "coordination" / "council" / "auto_council_verdicts.jsonl"
SECRET_RX = re.compile(r"(sk_live|sk_test|whsec_|service_role|Bearer\s+\S+)", re.I)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sanitize(text: str) -> str:
    """Nothing leaves the machine with a secret in it. Fail closed."""
    out = SECRET_RX.sub("<REDACTED>", text)
    assert not SECRET_RX.search(out), "sanitisation failed — refusing to dispatch"
    return out


def audit(target_path: str, *, model: str | None = None,
          max_chars: int = 6000) -> list[dict[str, Any]]:
    """Route an adversarial audit through the GOVERNED gateway. No clipboard involved."""
    src = _sanitize((ROOT / target_path).read_text()[:max_chars])

    mission = f"""You are HELM's ADVERSARIAL SYSTEMS CRITIC. You have NO verdict authority and
may NOT declare PASS — deterministic tests decide that.

Audit the source below for real defects: race conditions, fake-green paths (a check that can
pass without evidence), unhandled failures, silent fallbacks, security holes, and claims the
code cannot actually support.

If you cannot prove a finding from what is supplied, label it UNKNOWN rather than asserting it.
A finding you invented costs a human being real time. Do not invent.

Return ONLY JSON:
{{"findings":[{{"id":"F1","issue":"...","why_it_matters":"...","adversarial_test":"...",
"confidence":"OBSERVED|DERIVED|UNKNOWN","severity":"HIGH|MED|LOW","auto_testable":true|false}}]}}

SOURCE ({target_path}):
{src}
"""
    task = {
        "task_id": f"AUTOCOUNCIL-{hashlib.sha256(target_path.encode()).hexdigest()[:8]}",
        "action_text": mission,
        "environment": "local",
        "adapter": "GROK_CLI",
        "target": target_path,
        "data_classification": "public_repo",
        "side_effects": "none",
    }
    binding = bind_classification(task, decision_id="FD-20260713-004")
    res = dispatch_grok(task, binding, model=model, timeout=300)

    out = res.get("output", "")
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if not m:
        # An unparseable audit is a BROKEN PIPE, not a clean bill of health. Raise.
        raise RuntimeError(f"AUDIT_UNPARSEABLE: adapter returned no JSON — "
                           f"{out[:140]!r}. Zero findings from a broken audit is a lie.")
    try:
        return json.loads(m.group(0)).get("findings", [])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AUDIT_MALFORMED_JSON: {e} — refusing to report 0 findings")


def adjudicate(finding: dict[str, Any], target_path: str) -> dict[str, Any]:
    """A DETERMINISTIC test decides. Grok proposes; it never disposes.

    Returns a verdict with a disposition:
      CONFIRMED   -> real defect; queue a remediation task (autonomous)
      REJECTED    -> not reproducible; discard with evidence
      NEEDS_HUMAN -> genuinely a judgment call; escalate (this is the ONLY path to Michael)
    """
    sev = str(finding.get("severity", "")).upper()
    conf = str(finding.get("confidence", "")).upper()
    issue = str(finding.get("issue", ""))

    # 1. An UNKNOWN-confidence finding is not evidence. Discard; do NOT spend founder time.
    if conf == "UNKNOWN":
        return {"disposition": "REJECTED", "reason": "confidence=UNKNOWN — a model's hunch is "
                "not a defect. Escalating it would spend founder time on speculation."}

    # 2. Does the claimed defect touch something FOUNDER_ONLY or PROHIBITED?
    ruling = classify_action(issue)
    if ruling.authority in (Authority.FOUNDER_ONLY, Authority.PROHIBITED, Authority.CONFLICTED):
        return {"disposition": "NEEDS_HUMAN",
                "reason": f"remediation would be {ruling.authority.value} "
                          f"(matched: {ruling.matched}) — only Michael may authorise this",
                "authority": ruling.authority.value}

    # 3. Everything else is machine-decidable: queue it as autonomous remediation work.
    #    A HIGH/OBSERVED finding on local code is a bug to FIX, not a question to ASK.
    if conf == "OBSERVED" and sev in ("HIGH", "MED"):
        return {"disposition": "CONFIRMED",
                "reason": "observed defect on local code — remediation is AUTONOMOUS; "
                          "no founder decision is required to fix a bug",
                "remediation_task": f"fix: {issue[:110]}",
                "target": target_path}

    return {"disposition": "REJECTED",
            "reason": f"confidence={conf} severity={sev} — below the bar for spending "
                      "either machine or founder time"}


def run(target_path: str, *, model: str | None = None) -> dict[str, Any]:
    """One full self-orchestrating cycle. Michael touches nothing."""
    findings = audit(target_path, model=model)
    out = {"target": target_path, "at": _now(), "findings": len(findings),
           "confirmed": [], "rejected": [], "escalated": []}

    for f in findings:
        v = adjudicate(f, target_path)
        row = {"at": _now(), "target": target_path, "finding": f, "verdict": v}
        VERDICTS.parent.mkdir(parents=True, exist_ok=True)
        with open(VERDICTS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

        d = v["disposition"]
        if d == "CONFIRMED":
            out["confirmed"].append(f.get("id"))
        elif d == "REJECTED":
            out["rejected"].append(f.get("id"))
        else:
            # THE ONLY PATH TO MICHAEL. Deduped, and only when it is genuinely his call.
            ok, msg = escalate(Escalation(
                one_sentence_question=f"Authorise remediation of: {str(f.get('issue',''))[:90]}?",
                why_it_needs_you=v["reason"],
                options=["Approve the fix", "Deny / leave as-is"],
                recommendation_and_why="HOLD — this touches an authority you alone hold",
                evidence_sanitized=f"target={target_path} finding={f.get('id')} "
                                   f"severity={f.get('severity')}",
                cost_of_delay="none; the defect is recorded and unchanged",
                reversible=True), can_prove_answer=False)
            if ok:
                out["escalated"].append(f.get("id"))

    return out


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "backend/mission_control/per_task_lease.py"
    r = run(target)
    print(json.dumps(r, indent=2))
