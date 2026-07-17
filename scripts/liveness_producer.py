#!/usr/bin/env python3
"""HELM liveness producer — keeps the wall's liveness panels HONESTLY current.

Rebuilt 2026-07-17 to replace the retired council_watch.sh / relay_refresh.sh
daemons (their scripts were deleted; their launchd jobs errored 127).

What it refreshes (real current state only — NO fabricated activity):
  * coordination/council/factory_registry.json   -> /api/v1/helm/factories
        Canonical factory IDENTITIES (constant truth). Re-published with a fresh
        timestamp + republished_at so the panel reads "verified as of now" rather
        than days-stale. Identity content is preserved exactly.
  * coordination/council/active_runtime_source.json -> /api/v1/helm/runtime + /wall
        The CURRENT orchestrating runtime, detected live (real pid), honest note.

What it deliberately does NOT touch (integrity-gated; faking = fake-green):
  * /agents  (needs a real soak/dispatch result-envelope ledger)
  * /chain   (AU-9 hash chain; a non-chained heartbeat would BREAK verification)
  These honestly render UNKNOWN until a real dispatch daemon runs.

Usage: liveness_producer.py [--once|--loop] [--interval 60]
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY_REGISTRY = ROOT / "coordination" / "council" / "factory_registry.json"
RUNTIME_POINTER = ROOT / "coordination" / "council" / "active_runtime_source.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _detect_runtime() -> dict:
    """Detect the REAL current orchestrating runtime. No assertion of activity that isn't there."""
    def _pgrep(pat):
        try:
            out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, timeout=5).stdout.strip()
            return int(out.splitlines()[0]) if out else None
        except Exception:
            return None
    # priority: an active soak runner, else the freshness refresher, else native cadence
    soak = _pgrep("soak_runner.py")
    refr = _pgrep("runtime_refresher.py")
    auto = _pgrep("helm_autoloop.sh")
    if soak:
        return {"runtime": "soak_runner.py", "pid": soak, "scheduler_instance_id": "soak",
                "note": "active soak runner is the current runtime"}
    if refr or auto:
        pid = refr or auto
        return {"runtime": "freshness_refresher+autoloop", "pid": pid,
                "scheduler_instance_id": "native-cadence",
                "note": "HELM on native cadence: freshness refresher + helm autoloop live; product work runs on the scheduled-task loop; no soak active"}
    return {"runtime": "scheduled-task-loop", "pid": os.getpid(),
            "scheduler_instance_id": "native-cadence",
            "note": "no long-running orchestrator process detected; HELM product work runs via scheduled tasks"}


def _reconcile_factory_readiness(d: dict) -> list[str]:
    """Map operational readiness from products manifest — no fake READY (audit R-05).

    Registry identity fields stay; health/readiness become evidence-derived:
      - no products for factory → keep UNKNOWN/NOT_READY (or leave stubs)
      - max monetization rung digit:
          0-1 → NOT_READY / UNKNOWN or PROTOTYPE
          2-3 → DEGRADED / PARTIAL (code or defined, not sellable)
          4   → READY only if sellable claim + source or live_url present
          5   → READY / ACTIVE (earning — still requires settled ledger elsewhere)
    """
    notes: list[str] = []
    products_path = ROOT / "coordination" / "products" / "products.json"
    if not products_path.exists():
        notes.append("products.json missing — readiness not reconciled")
        return notes
    try:
        products = json.loads(products_path.read_text()).get("products") or []
    except Exception as e:
        notes.append(f"products.json unreadable: {e}")
        return notes

    by_factory: dict[str, list[dict]] = {}
    for p in products:
        fid = (p.get("factory") or p.get("owning_factory") or "").strip().upper()
        if not fid:
            continue
        by_factory.setdefault(fid, []).append(p)

    factories = d.get("factories") or {}
    for fid, fac in factories.items():
        if not isinstance(fac, dict):
            continue
        prods = by_factory.get(fid, [])
        if not prods:
            # Non-monetized or stub factories: never promote to READY without products
            if fac.get("readiness") == "READY" and fac.get("health") == "ACTIVE":
                fac["readiness"] = "NOT_READY"
                fac["health"] = "UNKNOWN"
                fac["readiness_basis"] = "no_products_in_manifest"
                notes.append(f"{fid}: demoted READY→NOT_READY (no products)")
            continue

        def _rung_num(p: dict) -> int:
            r = str(p.get("monetization_rung") or "0")
            for ch in r:
                if ch.isdigit():
                    return int(ch)
            return 0

        best = max(prods, key=_rung_num)
        n = _rung_num(best)
        # source on disk?
        src = best.get("source_dir") or ""
        sot = best.get("source_of_truth") or ""
        on_disk = False
        for cand in (src, sot):
            if not cand or "UNKNOWN" in cand.upper() or "NOT-IN-REPO" in cand.upper():
                continue
            # first path-like token
            path = cand.split()[0].strip(".,;:")
            if path.startswith("docs/"):
                continue
            absdir = path if path.startswith("/") else str(ROOT / path)
            if os.path.isdir(absdir):
                on_disk = True
                break

        prev_r, prev_h = fac.get("readiness"), fac.get("health")
        if n >= 5:
            fac["readiness"], fac["health"] = "READY", "ACTIVE"
            fac["readiness_basis"] = f"manifest_rung={best.get('monetization_rung')} product={best.get('product_id')}"
        elif n >= 4:
            # Sellable claim — still not READY for *factory ops* unless source or live
            live = best.get("live_url") or ""
            if live and "UNKNOWN" not in live.upper():
                fac["readiness"], fac["health"] = "READY", "ACTIVE"
            else:
                fac["readiness"], fac["health"] = "DEGRADED", "PARTIAL"
            fac["readiness_basis"] = f"manifest_rung={best.get('monetization_rung')} live_url={'yes' if live else 'no'}"
        elif n >= 2:
            fac["readiness"] = "DEGRADED" if on_disk else "NOT_READY"
            fac["health"] = "PARTIAL" if on_disk else "UNKNOWN"
            fac["readiness_basis"] = (
                f"manifest_rung={best.get('monetization_rung')} on_disk={on_disk} "
                f"product={best.get('product_id')}"
            )
        else:
            fac["readiness"], fac["health"] = "NOT_READY", "UNKNOWN"
            fac["readiness_basis"] = f"manifest_rung={best.get('monetization_rung')}"

        if (prev_r, prev_h) != (fac.get("readiness"), fac.get("health")):
            notes.append(f"{fid}: {prev_h}/{prev_r} → {fac.get('health')}/{fac.get('readiness')}")
    return notes


def refresh_factory_registry() -> str:
    if not FACTORY_REGISTRY.exists():
        return f"SKIP factory_registry.json missing at {FACTORY_REGISTRY}"
    d = json.loads(FACTORY_REGISTRY.read_text())
    recon = _reconcile_factory_readiness(d)
    d["republished_at"] = _now()
    d["readiness_reconciled_at"] = d["republished_at"]
    d["readiness_doctrine"] = (
        "health/readiness derived from coordination/products/products.json monetization rungs "
        "+ on-disk source checks; READY is not stamped by identity alone (no fake green)"
    )
    FACTORY_REGISTRY.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    extra = ("; " + "; ".join(recon)) if recon else ""
    return f"OK factory_registry.json ({len(d.get('factories', {}))} factories) @ {d['republished_at']}{extra}"


def refresh_runtime_pointer() -> str:
    rt = _detect_runtime()
    prev = {}
    try:
        prev = json.loads(RUNTIME_POINTER.read_text())
    except Exception:
        pass
    doc = {
        "scheduler_instance_id": rt["scheduler_instance_id"],
        "ledger_path": prev.get("ledger_path", ""),
        "evidence_dir": prev.get("evidence_dir", "coordination/council/native_runtime"),
        "runtime": rt["runtime"],
        "pid": rt["pid"],
        "published_at": _now(),
        "note": rt["note"],
    }
    RUNTIME_POINTER.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return f"OK active_runtime_source.json -> {rt['runtime']} pid={rt['pid']} @ {doc['published_at']}"


def once() -> int:
    print(f"[liveness {_now()}] {refresh_factory_registry()}")
    print(f"[liveness {_now()}] {refresh_runtime_pointer()}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--once", action="store_true")
    g.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args(argv)
    if a.loop:
        while True:
            try:
                once()
            except Exception as e:
                print(f"[liveness {_now()}] ERROR {e}", file=sys.stderr)
            time.sleep(a.interval)
    return once()


if __name__ == "__main__":
    raise SystemExit(main())
