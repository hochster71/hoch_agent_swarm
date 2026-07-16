#!/usr/bin/env python3
"""HELM 8-FACTORY MOONSHOT — arm all eight factories toward revenue, in parallel.

DOCTRINE
--------
Every mission is REVENUE-FIRST and BOUNDED. The swarm does the build/spec/analysis work
LOCAL_ONLY (zero credentials, zero spend) and STOPS at a FOUNDER GATE for anything that
sets keys, deploys, publishes, or moves money. Revenue rail = Stripe for every factory.
No rung is asserted; each is earned and observed by factory_census.

SOAK INTERLOCK (why this file exists instead of a raw seeder)
------------------------------------------------------------
The scheduler dispatches ANY row with status IN ('PENDING','FAILED') from the shared
mission_control_tasks DB — it is NOT scoped to SOAK-*. Seeding live missions while a soak
runs would inject them into the soak and destroy the 24/7 proof (this is what killed the
prior soak attempts). So this launcher REFUSES to seed while a soak is active. It is armed
now and fires only once the soak has sealed.

USAGE
    python3 scripts/council/launch_8factory_moonshot.py            # dry-run (default)
    python3 scripts/council/launch_8factory_moonshot.py --arm      # seed (blocked if soak live)
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "backend" / "swarm_ledger.db"
POINTER = ROOT / "coordination" / "council" / "active_runtime_source.json"
PKG_DIR = ROOT / "coordination" / "council" / "live_proof_packages"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---- The eight missions. Each is bounded; each ends at an explicit FOUNDER_GATE. -------
MISSIONS = [
    {
        "mission_id": "MOON-HASF-01", "factory": "HASF", "rung_now": 4, "rung_target": 5,
        "name": "Epic Fury: first-buyer distribution kit",
        "founder_gate": "PUBLISH/SEND — founder posts the landing copy and sends outreach.",
        "prompt": (
            "Epic Fury 2026 is LIVE on the App Store and SELLABLE ($19/mo, $190/yr) but has "
            "zero buyers. Produce a concrete first-buyer distribution kit as markdown: (1) a "
            "tightened one-paragraph value proposition for geopolitical/defense analysts; (2) "
            "three specific, non-spammy outreach messages to named analyst communities "
            "(e.g. OSINT/wargaming forums), each under 120 words; (3) a 5-point audit of the "
            "pricing/upgrade page for conversion. Do NOT send anything — output copy only for "
            "the founder to publish."
        ),
    },
    {
        "mission_id": "MOON-HSF-01", "factory": "HSF", "rung_now": 2, "rung_target": 4,
        "name": "Story Studio: make it genuinely sellable",
        "founder_gate": "LIVE KEYS + DEPLOY — founder sets Stripe live keys in Vercel and deploys.",
        "prompt": (
            "HSF Story Studio has a Stripe checkout scaffold at hsf/deploy (tiers: One-Story "
            "Export + Creators subscription) but the UI was quarantined as fake and the scaffold "
            "is inert. Produce: (1) a real, honest Story Studio product page spec (what it does, "
            "who buys, the two prices); (2) a verification checklist that exercises "
            "create-checkout-session.js and webhook.js in Stripe TEST mode end to end; (3) a "
            "go-live checklist naming exactly which env vars the founder must set. Build/spec "
            "only — do NOT set live keys or deploy."
        ),
    },
    {
        "mission_id": "MOON-HCF-01", "factory": "HCF", "rung_now": 2, "rung_target": 3,
        "name": "Cyber: name & spec one product from the artifacts",
        "founder_gate": "KEYS/DEPLOY — founder approves the checkout when the spec is ready.",
        "prompt": (
            "HCF (Hoch Cyber Factory) has produced 531 validated artifacts but no PRODUCT. "
            "Review what it actually produces (security/compliance deliverables) and define ONE "
            "sellable product: a specific name, a named buyer, a price, and a one-page spec of "
            "what the buyer receives. Output the product spec + a Stripe checkout scaffold plan. "
            "Register the product in coordination/products/product_registry.json is a FOUNDER "
            "step — propose the exact JSON entry, do not commit it."
        ),
    },
    {
        "mission_id": "MOON-HRF-01", "factory": "HRF", "rung_now": 2, "rung_target": 3,
        "name": "Research: name & spec one product from the artifacts",
        "founder_gate": "KEYS/DEPLOY — founder approves the checkout when the spec is ready.",
        "prompt": (
            "HRF (Hoch Research Factory) has produced 531 validated artifacts (research & "
            "intelligence). Define ONE sellable product: name, buyer, price, and a one-page spec "
            "(e.g. a recurring intelligence brief or a report pack). Output the product spec + a "
            "Stripe checkout scaffold plan + the proposed product_registry.json entry. Do not "
            "commit the registry entry — that is the founder's approval."
        ),
    },
    # The four DECLARED factories: first governed mission -> first validated artifact -> product candidate.
    {
        "mission_id": "MOON-HFF-01", "factory": "HFF", "rung_now": 0, "rung_target": 2,
        "name": "Finance: first governed mission + product candidate",
        "founder_gate": "None yet (pre-revenue). Money actions remain founder-only downstream.",
        "prompt": (
            "HFF (Hoch Finance Factory) has never run a mission. Execute one bounded, useful "
            "financial-tooling deliverable (e.g. a small, correct, well-tested Python module that "
            "computes something a finance user needs) as a validated artifact, then propose ONE "
            "product candidate (name, buyer, price) it could become. Local only; no market data "
            "credentials, no spend, no financial advice."
        ),
    },
    {
        "mission_id": "MOON-HHF-01", "factory": "HHF", "rung_now": 0, "rung_target": 2,
        "name": "Home: first governed mission + product candidate",
        "founder_gate": "None yet (pre-revenue).",
        "prompt": (
            "HHF (Hoch Home Factory) has never run a mission. Execute one bounded home/personal-"
            "automation deliverable as a validated artifact, then propose ONE product candidate "
            "(name, buyer, price). Local only; no spend."
        ),
    },
    {
        "mission_id": "MOON-HMF-01", "factory": "HMF", "rung_now": 0, "rung_target": 2,
        "name": "Music: first governed mission + product candidate",
        "founder_gate": "None yet (pre-revenue). Respect copyright — original works only.",
        "prompt": (
            "HMF (Hoch Music Factory) has never run a mission. Execute one bounded music/audio "
            "deliverable as a validated artifact (original composition or a tool that generates "
            "one — never copying an existing artist), then propose ONE product candidate (name, "
            "buyer, price). Local only; no spend."
        ),
    },
    {
        "mission_id": "MOON-HPF-01", "factory": "HPF", "rung_now": 0, "rung_target": 2,
        "name": "Pods: first governed mission + product candidate",
        "founder_gate": "None yet (pre-revenue).",
        "prompt": (
            "HPF (Hoch Pods Factory) has never run a mission. Execute one bounded digital/physical-"
            "goods deliverable as a validated artifact, then propose ONE product candidate (name, "
            "buyer, price). Local only; no spend."
        ),
    },
]


def soak_active() -> tuple[bool, str]:
    """INTERLOCK: is a soak currently running? If so, refuse to seed."""
    try:
        out = subprocess.run(["pgrep", "-f", "soak_runner.py"], capture_output=True, text=True)
        if out.stdout.strip():
            return True, f"soak_runner.py alive (pids {out.stdout.split()})"
    except Exception:
        pass
    # also: if the canonical runtime pointer names a soak daemon whose ledger is fresh
    try:
        if POINTER.exists():
            p = json.loads(POINTER.read_text())
            ed = str(p.get("evidence_dir", ""))
            if "SOAK" in ed:
                import time as _t
                lp = Path(p.get("ledger_path", ""))
                if lp.exists() and (_t.time() - lp.stat().st_mtime) < 300:
                    return True, f"active runtime pointer names a live SOAK ledger ({ed})"
    except Exception:
        pass
    return False, "no soak active"


def seed(apply: bool) -> int:
    blocked, why = soak_active()
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    manifest = {"program": "HELM-8-FACTORY-MOONSHOT", "armed_at": now(),
                "revenue_rail": "stripe", "mode": "APPLY" if apply else "DRY-RUN",
                "soak_interlock": {"blocked": blocked, "reason": why},
                "missions": [{k: m[k] for k in ("mission_id", "factory", "rung_now",
                              "rung_target", "name", "founder_gate")} for m in MISSIONS]}
    print(f"HELM 8-FACTORY MOONSHOT — {'APPLY' if apply else 'DRY-RUN'}")
    print(f"  soak interlock: {'BLOCKED — ' + why if blocked else 'clear (' + why + ')'}")
    for m in MISSIONS:
        print(f"  {m['mission_id']:14} {m['factory']:5} rung {m['rung_now']}->{m['rung_target']}  {m['name']}")
        print(f"                 founder gate: {m['founder_gate']}")

    if apply and blocked:
        print("\nREFUSING TO SEED: a soak is active. This launcher fires only after the soak seals.")
        return 3
    if not apply:
        print("\n(dry-run — nothing seeded. Re-run with --arm once the soak has sealed.)")
        return 0

    conn = sqlite3.connect(str(DB))
    ts = now()
    for m in MISSIONS:
        tid = f"T-{m['mission_id']}"
        conn.execute(
            """INSERT OR REPLACE INTO mission_control_tasks
               (task_id, mission_id, name, assigned_agent, status, step_index, dependencies,
                error_message, evidence_path, created_at, updated_at, mission_prompt,
                validator_ctx, required_capability)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, m["mission_id"], m["name"], f"Agent{m['factory']}", "PENDING", 0, "",
             None, None, ts, ts, m["prompt"],
             json.dumps({"factory": m["factory"], "rung_target": m["rung_target"],
                         "founder_gate": m["founder_gate"], "revenue_rail": "stripe"}),
             "LOCAL_ONLY"))
    conn.commit()
    conn.close()

    pkg = PKG_DIR / f"HELM-8FACTORY-MOONSHOT-{stamp}"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "launch_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nSEEDED {len(MISSIONS)} missions. Manifest: {pkg}/launch_manifest.json")
    print("The governed scheduler will now dispatch them LOCAL_ONLY. Money/keys/deploy stay founder-only.")
    return 0


if __name__ == "__main__":
    sys.exit(seed(apply="--arm" in sys.argv[1:]))
