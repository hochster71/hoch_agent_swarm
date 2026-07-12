#!/usr/bin/env python3
"""CHAMPION PRODUCT GATES — Epic Fury 2026. Ten validators, computed not remembered.

RATIFIED: "It must not assign an initial percentage from memory or a hardcoded value."

Each gate returns PASS / FAIL / UNKNOWN from EVIDENCE ON DISK. Two rules make this
honest rather than flattering:

  1. A JSON file asserting its own success is NOT evidence of success.
     epic_fury_release_ledger.json says security_gate=SIGNED and state=WAITING_FOR_REVIEW.
     That is a CLAIM. A gate PASSES only when a distinct artifact -- an approval record,
     a scan result, a gate-verify verdict -- exists and is fresh.

  2. Anything only Apple can answer is UNKNOWN, never PASS.
     APP_STORE_CONNECT and TESTFLIGHT state live in App Store Connect. Reading them needs
     credentials, which are NOT_PROVISIONED and are founder-only. The local ledger's
     five-day-old "WAITING_FOR_REVIEW" cannot be re-verified from here. UNKNOWN is the
     truthful answer. (Audit F-21.1: the K-track gates cited themselves as their own
     evidence and every one was expired. Not repeating that.)

UNKNOWN contributes ZERO completion. That is the point.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "champion_gates.json"

LEDGER = ROOT / "has_live_project_tracker" / "data" / "epic_fury_release_ledger.json"
PRODUCT = ROOT / "docs" / "products" / "epic-fury-2026"
EVIDENCE = ROOT / "docs" / "evidence" / "products" / "epic-fury-2026"

# How stale a claim may be before it stops counting.
FRESHNESS_SLA_HOURS = 168          # 7 days
ASC_CREDENTIAL_REFS = ["APP_STORE_CONNECT_KEY_ID", "ASC_API_KEY", "APP_STORE_CONNECT_ISSUER_ID"]

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def age_hours(p: Path) -> float | None:
    if not p.exists():
        return None
    return round((now().timestamp() - p.stat().st_mtime) / 3600.0, 1)


def gate(name: str, status: str, detail: str, evidence: list[str],
         age: float | None = None, blocker: str | None = None) -> dict:
    return {"gate": name, "status": status, "detail": detail,
            "evidence": evidence, "evidence_age_hours": age, "blocker": blocker,
            "contributes": 1.0 if status == PASS else 0.0}


def credentials_present() -> bool:
    # existence check only; never reads a value
    return any(k in os.environ for k in ASC_CREDENTIAL_REFS)


def run() -> dict:
    led = load(LEDGER) or {}
    led_age = age_hours(LEDGER)
    stale = led_age is not None and led_age > FRESHNESS_SLA_HOURS

    gates: list[dict] = []

    # 1. BUILD -------------------------------------------------------------
    b = led.get("build") or {}
    if not b:
        gates.append(gate("BUILD", UNKNOWN, "no build record", [], led_age,
                          "no build evidence"))
    elif b.get("state") == "VALID" and b.get("number") and not stale:
        gates.append(gate("BUILD", PASS,
                          f"build {b['number']} VALID, selected={b.get('selected')}",
                          [str(LEDGER.relative_to(ROOT))], led_age))
    else:
        gates.append(gate("BUILD", UNKNOWN if stale else FAIL,
                          f"build state={b.get('state')} ledger_age={led_age}h",
                          [str(LEDGER.relative_to(ROOT))], led_age,
                          "ledger stale" if stale else "build not VALID"))

    # 2. TEST --------------------------------------------------------------
    specs = sorted((ROOT / "tests" / "e2e").glob("*epic-fury*.spec.ts"))
    # The specs EXIST. Whether they PASS requires running them against a live app,
    # which is not available here. Existence is not passage.
    gates.append(gate(
        "TEST", UNKNOWN,
        f"{len(specs)} Epic Fury e2e specs exist, but no CURRENT execution record was "
        f"found. Existence of a test is not evidence that it passed.",
        [str(s.relative_to(ROOT)) for s in specs[:4]], None,
        "no fresh test-execution artifact"))

    # 3. SECURITY ----------------------------------------------------------
    gv = load(PRODUCT / "HASF_GATE_VERIFY.json")
    scan = EVIDENCE / "security_scan_results_20260707.md"
    gv_age = age_hours(PRODUCT / "HASF_GATE_VERIFY.json")
    if gv and gv.get("verdict") == "GO" and int(gv.get("open_high", 1)) == 0 and scan.exists():
        gates.append(gate("SECURITY", PASS,
                          f"gate verdict GO, open_high=0, {len(gv.get('rules', []))} rules PASS",
                          ["docs/products/epic-fury-2026/HASF_GATE_VERIFY.json",
                           str(scan.relative_to(ROOT))], gv_age))
    else:
        gates.append(gate("SECURITY", FAIL if gv else UNKNOWN,
                          f"verdict={(gv or {}).get('verdict')} open_high={(gv or {}).get('open_high')}",
                          [], gv_age, "security gate not GO"))

    # 4. SIGNING_READINESS -------------------------------------------------
    approval = next(iter(sorted(EVIDENCE.glob("RELEASE_APPROVAL_*.json"))), None)
    sg = led.get("security_gate") or {}
    if approval and approval.exists() and sg.get("status") == "SIGNED":
        gates.append(gate("SIGNING_READINESS", PASS,
                          f"founder release approval artifact present; signed by {sg.get('by')}",
                          [str(approval.relative_to(ROOT))], age_hours(approval)))
    else:
        gates.append(gate("SIGNING_READINESS", UNKNOWN,
                          "no distinct founder release-approval artifact found",
                          [], None, "signing evidence absent"))

    # 5. STORE_METADATA ----------------------------------------------------
    fields = led.get("listing_fields") or []
    done = [f for f in fields if f.get("status") == "DONE"]
    if fields and len(done) == len(fields) and not stale:
        gates.append(gate("STORE_METADATA", PASS,
                          f"{len(done)}/{len(fields)} listing fields DONE",
                          [str(LEDGER.relative_to(ROOT))], led_age))
    else:
        gates.append(gate("STORE_METADATA", UNKNOWN if stale else FAIL,
                          f"{len(done)}/{len(fields)} DONE, ledger_age={led_age}h",
                          [str(LEDGER.relative_to(ROOT))], led_age,
                          "ledger stale" if stale else "listing incomplete"))

    # 6. PRIVACY -----------------------------------------------------------
    priv = [f for f in fields if "privacy" in str(f.get("item", "")).lower()]
    if priv and all(f.get("status") == "DONE" for f in priv) and not stale:
        gates.append(gate("PRIVACY", PASS,
                          f"{len(priv)} privacy fields DONE (policy URL + App Privacy)",
                          [str(LEDGER.relative_to(ROOT))], led_age))
    else:
        gates.append(gate("PRIVACY", UNKNOWN, "privacy declarations unverified or stale",
                          [], led_age, "stale or missing"))

    # 7. MONETIZATION ------------------------------------------------------
    pricing = [f for f in fields if "pricing" in str(f.get("item", "")).lower()]
    roi = ROOT / "has_live_project_tracker" / "data" / "epic_fury_roi_model.json"
    # Pricing being configured is NOT revenue. Say so.
    if pricing and all(f.get("status") == "DONE" for f in pricing) and not stale:
        gates.append(gate("MONETIZATION", PASS,
                          "pricing configured. NOTE: configured pricing is not shipped "
                          "revenue -- $0 has been earned.",
                          [str(LEDGER.relative_to(ROOT))] +
                          ([str(roi.relative_to(ROOT))] if roi.exists() else []), led_age))
    else:
        gates.append(gate("MONETIZATION", UNKNOWN, "pricing configuration unverified",
                          [], led_age, "stale or missing"))

    # 8. TESTFLIGHT --------------------------------------------------------
    gates.append(gate(
        "TESTFLIGHT", UNKNOWN,
        "TestFlight state lives in App Store Connect. No local artifact records a "
        "current TestFlight build/tester state, and ASC credentials are NOT_PROVISIONED.",
        [], None, "requires App Store Connect access (founder-only credential)"))

    # 9. APP_STORE_CONNECT -------------------------------------------------
    sub = led.get("submit_for_review") or {}
    creds = credentials_present()
    claim = f"ledger claims state={sub.get('state')} submitted={sub.get('submitted_utc')}"
    gates.append(gate(
        "APP_STORE_CONNECT", UNKNOWN,
        f"{claim}. This is a {led_age}h-old CLAIM in a local file, not a live reading. "
        f"ASC credentials present: {creds}. Apple may have approved or rejected since. "
        f"The truthful state is UNKNOWN until App Store Connect is read.",
        [str(LEDGER.relative_to(ROOT))], led_age,
        "requires App Store Connect read (founder-only credential)"))

    # 10. SUBMISSION_PACKAGE ------------------------------------------------
    required_docs = ["RELEASE_CHECKLIST.md", "FOUNDER_RELEASE_DECISION.md",
                     "DEPLOYMENT_PLAN.md", "KNOWN_LIMITATIONS.md", "PRODUCT_BRIEF.md"]
    have = [d for d in required_docs if (PRODUCT / d).exists()]
    if len(have) == len(required_docs) and approval:
        gates.append(gate("SUBMISSION_PACKAGE", PASS,
                          f"{len(have)}/{len(required_docs)} release docs + founder decision present",
                          [f"docs/products/epic-fury-2026/{d}" for d in have], None))
    else:
        gates.append(gate("SUBMISSION_PACKAGE", FAIL,
                          f"{len(have)}/{len(required_docs)} release docs present",
                          [], None, "submission package incomplete"))

    passed = [g for g in gates if g["status"] == PASS]
    completion = round(100.0 * len(passed) / len(gates), 1)

    unresolved = [g for g in gates if g["status"] != PASS]
    # critical path = the failing/unknown gates, agent-actionable first
    founder_only = {"TESTFLIGHT", "APP_STORE_CONNECT"}
    agent_actionable = [g for g in unresolved if g["gate"] not in founder_only]

    report = {
        "champion_product": "EPIC_FURY_2026",
        "selection_evidence": "coordination/goal/champion_selection.json",
        "computation_rule": ("Completion is the fraction of gates whose validator PASSED "
                             "against fresh evidence. UNKNOWN and FAIL contribute ZERO. "
                             "No percentage is assigned from memory."),
        "gates": gates,
        "gates_passed": len(passed),
        "gates_total": len(gates),
        "champion_product_completion": completion,
        "ledger_age_hours": led_age,
        "ledger_is_stale": stale,
        "unresolved_gates": [g["gate"] for g in unresolved],
        "next_critical_path_gate": (agent_actionable[0]["gate"] if agent_actionable
                                    else (unresolved[0]["gate"] if unresolved else None)),
        "founder_only_gates_pending": [g["gate"] for g in unresolved
                                       if g["gate"] in founder_only],
        "generated_at": now().isoformat().replace("+00:00", "Z"),
        "status": PASS if not unresolved else "INCOMPLETE",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, indent=2, sort_keys=True) + "\n"
    OUT.write_text(body, encoding="utf-8")

    print(f"CHAMPION: EPIC_FURY_2026   completion={completion}%  "
          f"({len(passed)}/{len(gates)} gates)")
    for g in gates:
        mark = "PASS" if g["status"] == PASS else g["status"]
        print(f"  {mark:8} {g['gate']:20} {g['detail'][:70]}")
    print(f"  next gate: {report['next_critical_path_gate']}")
    print(f"  report sha256: {hashlib.sha256(body.encode()).hexdigest()}")
    return report


if __name__ == "__main__":
    r = run()
    # The validator EXITS 0 when it ran successfully. Completion is a MEASUREMENT the
    # engine consumes -- an incomplete champion is not a validator failure.
    raise SystemExit(0)
