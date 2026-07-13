"""FACTORY CENSUS — the instrument that answers "where are my factories?" without you asking.

THE PROBLEM THIS SOLVES
-----------------------
Michael keeps having to ask: where are the factories? what are they producing? why is
nothing making money? He has to ask because HELM had NO CONCEPT of the difference between:

    an ARTIFACT   -- a file a model produced (a poem, a gap analysis)
    a PRODUCT     -- something a stranger would pay for
    REVENUE       -- something a stranger DID pay for

The 4 factories that ran produced 4 artifacts. HELM proudly reported PASS on all of them.
Not one is a product. Nothing in the system knew that, so nothing said it.

THE MONETIZATION LADDER
-----------------------
Every factory is scored on the ONLY ladder that matters. A factory does not "exist"
because it is declared in a config file. It exists at the rung it can PROVE:

    0  DECLARED       named in the registry. Nothing else. (a config entry is not a factory)
    1  RUNS           has dispatched a real mission through the governed runtime
    2  PRODUCES       has produced a validated artifact
    3  PRODUCTIZED    that artifact is a defined PRODUCT with a NAME and a PRICE
    4  SELLABLE       there is a real CHECKOUT a stranger can reach
    5  EARNING        a stranger has actually PAID -- settled, evidenced revenue

Rungs 0-2 cost money. Only rung 5 makes it.

Every rung is OBSERVED, never asserted. A factory claiming PRODUCTIZED without a price
in the product registry is DECLARED, not PRODUCTIZED. Absence of evidence is a rung you
have not reached.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB = ROOT / "backend" / "swarm_ledger.db"
ARTIFACTS = ROOT / "artifacts" / "factory"
PRODUCTS = ROOT / "coordination" / "products" / "product_registry.json"

RUNGS = ["DECLARED", "RUNS", "PRODUCES", "PRODUCTIZED", "SELLABLE", "EARNING"]

# What each factory is FOR. Declared intent, so a gap is visible instead of silent.
FACTORY_INTENT = {
    "HASF": ("Hoch App/Agent Swarm Factory", "applications & agents", "EPIC_FURY_2026"),
    "HRF":  ("Hoch Research Factory", "research & intelligence artifacts", None),
    "HCF":  ("Hoch Cyber Factory", "security & compliance deliverables", None),
    "HSF":  ("Hoch Story Factory", "narrative & creative works", None),
    "HMF":  ("Hoch Music Factory", "music & audio", None),
    "HFF":  ("Hoch Finance Factory", "financial tooling", None),
    "HHF":  ("Hoch Home Factory", "home/personal automation", None),
    "HPF":  ("Hoch Product Factory", "physical/digital goods", None),
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _products() -> Dict[str, Any]:
    """A product is real only if it has a NAME and a PRICE. No price -> not a product."""
    if not PRODUCTS.exists():
        return {}
    try:
        d = json.loads(PRODUCTS.read_text())
        return {p["factory"]: p for p in d.get("products", [])
                if p.get("price_usd") is not None}
    except Exception:
        return {}


def census() -> Dict[str, Any]:
    prods = _products()

    # what has each factory actually DISPATCHED and PRODUCED?
    dispatched: Dict[str, int] = {}
    produced: Dict[str, List[str]] = {}
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        for tid, pod in c.execute(
                "SELECT t.task_id, m.target_pod FROM mission_control_tasks t "
                "LEFT JOIN mission_control_missions m ON t.mission_id=m.mission_id "
                "WHERE t.status IN ('COMPLETED','FAILED')"):
            if pod:
                dispatched[pod] = dispatched.get(pod, 0) + 1
        c.close()
    except Exception:
        pass

    if ARTIFACTS.exists():
        for p in ARTIFACTS.glob("*.md"):
            for f in FACTORY_INTENT:
                if f"-{f}-" in p.stem:
                    produced.setdefault(f, []).append(p.name)

    # revenue actually earned, per product -> per factory
    earned: Dict[str, float] = {}
    try:
        from backend.mission_control.hoch_ledger import HochLedger
        by_product = HochLedger().revenue_by_product()
        for fac, p in prods.items():
            if p["name"] in by_product:
                earned[fac] = by_product[p["name"]]
    except Exception:
        pass

    rows: List[Dict[str, Any]] = []
    for fac, (name, makes, champion) in FACTORY_INTENT.items():
        has_run = dispatched.get(fac, 0) > 0
        arts = produced.get(fac, [])
        prod = prods.get(fac)
        has_checkout = bool(prod and prod.get("checkout_url"))
        rev = earned.get(fac, 0.0)

        if rev > 0:
            rung = 5
        elif has_checkout:
            rung = 4
        elif prod:
            rung = 3
        elif arts:
            rung = 2
        elif has_run:
            rung = 1
        else:
            rung = 0

        # the ONE thing that would move this factory up a rung
        blocker = {
            0: "never dispatched a mission — it is a config entry, not a factory",
            1: "dispatched but produced no validated artifact",
            2: "produces artifacts, but no PRODUCT is defined (no name, no price)",
            3: "product defined but NO CHECKOUT — a stranger cannot buy it",
            4: "sellable but nobody has paid — needs a buyer, not more code",
            5: None,
        }[rung]

        rows.append({
            "factory": fac, "name": name, "makes": makes,
            "champion": champion or (prod or {}).get("name") or "UNKNOWN",
            "rung": rung, "stage": RUNGS[rung],
            "missions_run": dispatched.get(fac, 0),
            "artifacts": len(arts),
            "product": (prod or {}).get("name"),
            "price_usd": (prod or {}).get("price_usd"),
            "checkout_url": (prod or {}).get("checkout_url"),
            "revenue_usd": rev,
            "next_blocker": blocker,
        })

    rows.sort(key=lambda r: (-r["rung"], r["factory"]))
    earning = [r for r in rows if r["rung"] == 5]
    sellable = [r for r in rows if r["rung"] >= 4]

    return {
        "schema": "FACTORY_CENSUS_v1",
        "observed_at": _now(),
        "ladder": RUNGS,
        "factories": rows,
        "declared": len(rows),
        "ever_ran": len([r for r in rows if r["rung"] >= 1]),
        "producing": len([r for r in rows if r["rung"] >= 2]),
        "productized": len([r for r in rows if r["rung"] >= 3]),
        "sellable": len(sellable),
        "earning": len(earning),
        "total_revenue_usd": round(sum(r["revenue_usd"] for r in rows), 2),
        "verdict": (
            "NO FACTORY IS EARNING. Artifacts are not products; a validated file that "
            "nobody can buy is a cost, not an asset."
            if not earning else
            f"{len(earning)} factory(ies) earning ${round(sum(r['revenue_usd'] for r in rows),2)}"),
        "doctrine": "a factory exists at the rung it can PROVE, not the one it is declared at",
    }


def main() -> int:
    c = census()
    print("FACTORY CENSUS — the monetization ladder\n")
    print(f"  {'FAC':5s} {'STAGE':12s} {'runs':>5s} {'arts':>5s} {'price':>8s} {'earned':>8s}  next blocker")
    for r in c["factories"]:
        price = f"${r['price_usd']}" if r["price_usd"] is not None else "—"
        print(f"  {r['factory']:5s} {r['stage']:12s} {r['missions_run']:5d} {r['artifacts']:5d} "
              f"{price:>8s} {('$'+format(r['revenue_usd'],'.2f')):>8s}  {r['next_blocker'] or 'EARNING'}")
    print(f"\n  declared {c['declared']} · ran {c['ever_ran']} · producing {c['producing']} · "
          f"productized {c['productized']} · sellable {c['sellable']} · EARNING {c['earning']}")
    print(f"\n  {c['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
