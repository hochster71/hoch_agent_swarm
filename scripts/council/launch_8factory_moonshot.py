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
        "name": "Finance: Founder cash-runway dashboard (recurring product)",
        "founder_gate": "KEYS/DEPLOY downstream — founder wires Stripe + deploy when the build is ready.",
        "prompt": (
            "HFF (Hoch Finance Factory) product direction (founder's choice): a FOUNDER CASH-RUNWAY "
            "DASHBOARD — a recurring subscription for small-business owners / solo founders that "
            "shows cash on hand, burn, and months of runway from simple inputs. Build a bounded, "
            "correct, well-tested first module: given a starting balance, recurring inflows, and "
            "outflows, compute runway months, a burn trend, and a clear 'out of cash' date, with "
            "unit tests. Then write the product spec (name, buyer, price = recurring) + the proposed "
            "product_registry.json entry (do NOT commit it — founder approves). Local only; no real "
            "financial data, no market-data credentials, no spend, no financial advice."
        ),
    },
    {
        "mission_id": "MOON-HHF-01", "factory": "HHF", "rung_now": None, "rung_target": None,
        "monetized": False,
        "name": "Hoch Home PERSONAL Factory — family operations (NOT monetized)",
        "founder_gate": ("PRIVACY — connecting the family's REAL calendars/accounts or handling "
                         "any real personal data is founder-authorized. Build + run on SIMULATED "
                         "family data until Michael explicitly connects real accounts."),
        "prompt": (
            "HHF is the Hoch Home PERSONAL Factory. It serves the HOCH FAMILY — Alison (wife), "
            "Caroline and Claire (daughters), and Michael — NOT a market. It is NEVER monetized; "
            "its only success metric is making the family's daily life easier. Build ON TOP of the "
            "existing backend/homeops (device_registry.py, action_simulator.py); do not start over.\n\n"
            "Using SIMULATED / placeholder family data ONLY (no real accounts, no real personal "
            "data yet), deliver a working first version of a dedicated family-operations swarm:\n"
            "1. A family roster + household profile schema (members, roles, preferences, "
            "constraints — e.g. school days for the girls).\n"
            "2. A shared family-calendar model + a sync DESIGN naming which real service to connect "
            "later (e.g. Google Calendar) behind a founder-authorized, privacy-scoped connector.\n"
            "3. A household scheduler: cleaning rotations, chores, and recurring household-item / "
            "supply reminders (groceries, consumables).\n"
            "4. A daily 'family brief' the household can read each morning.\n\n"
            "PRIVACY IS PARAMOUNT: do NOT connect real accounts, do NOT ingest real personal data, "
            "do NOT send anything to family members. Output the working system on simulated data "
            "plus a short, explicit list titled 'What Michael must connect' for the founder to wire "
            "real accounts later under his control."
        ),
    },
    {
        "mission_id": "MOON-HMF-01", "factory": "HMF", "rung_now": 0, "rung_target": 2,
        "name": "Music: royalty-free ORIGINAL music pack (one-time product)",
        "founder_gate": "KEYS/DEPLOY downstream — founder wires Stripe + deploy when the pack is ready.",
        "prompt": (
            "HMF (Hoch Music Factory) product direction (founder's choice): a ROYALTY-FREE ORIGINAL "
            "MUSIC PACK sold one-time to creators/streamers/video-makers. Produce a bounded first "
            "deliverable: a small set of ORIGINAL compositions (or a tool that generates them) with "
            "clear, clean IP — NEVER copying, sampling, or imitating any existing artist or "
            "copyrighted work. Include a license note (royalty-free terms) and the product spec "
            "(name, buyer, price = one-time) + the proposed product_registry.json entry (do NOT "
            "commit it — founder approves). Local only; no spend."
        ),
    },
    {
        "mission_id": "MOON-HPF-01", "factory": "HPF", "rung_now": 0, "rung_target": 2,
        "name": "Pods: podcast production kit (product) — DIRECTION UNCONFIRMED",
        "founder_gate": "DEFINITION + KEYS/DEPLOY — founder confirms what 'Pods' is, then wires Stripe.",
        "prompt": (
            "HPF (Hoch Pods Factory) product direction is TENTATIVE (founder to confirm what 'Pods' "
            "means): assume a PODCAST PRODUCTION KIT — templates, show-notes generators, and a "
            "release checklist sold to independent podcasters. Produce a bounded first deliverable "
            "(e.g. a show-notes + episode-plan generator with tests) and the product spec (name, "
            "buyer, price) + proposed product_registry.json entry (do NOT commit). If the founder "
            "later redefines 'Pods', this mission is re-aimed. Local only; no spend."
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
        if m.get("monetized", True) is False:
            tag = "FAMILY-OPS (not monetized)"
        else:
            tag = f"rung {m['rung_now']}->{m['rung_target']}"
        print(f"  {m['mission_id']:14} {m['factory']:5} {tag}  {m['name']}")
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
