#!/usr/bin/env python3
"""REQ-TO-002 (FOUNDER_ONLY) — champion product SHIPPED to production distribution.

Evidence-gated and FAIL-CLOSED. "Shipped" means Apple's App Store Connect reports the
champion's version in a truly-live, purchasable state (READY_FOR_SALE / READY_FOR_DISTRIBUTION)
via the same live read the CP-APP_STORE_CONNECT gate uses. Merely "approved but not released"
(PENDING_DEVELOPER_RELEASE) or any unreadable/UNKNOWN state does NOT count as shipped.
No credentials or no live confirmation => shipped=False (never a fabricated pass).
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.goal.asc_client import read_distribution_state

OUT = ROOT / "coordination" / "goal" / "shipped_report.json"
SHIPPED_LIVE = {"READY_FOR_SALE", "READY_FOR_DISTRIBUTION"}  # released & purchasable


def main() -> int:
    dist = read_distribution_state()
    aps = dist.get("app_store", {}) or {}
    state = aps.get("state")                 # PASS / FAIL / UNKNOWN
    detail = aps.get("detail", "") or ""
    m = re.search(r"appStoreState=([A-Z_]+)", detail)
    live = m.group(1) if m else None
    shipped = (state == "PASS" and live in SHIPPED_LIVE)
    report = {
        "requirement": "REQ-TO-002",
        "shipped": shipped,
        "appStoreState": live,
        "asc_state": state,
        "asc_detail": detail,
        "read_at": dist.get("read_at"),
        "bundle_id": dist.get("bundle_id"),
        "evidence": "asc:appStoreVersions (live App Store Connect read)",
        "reason": (
            f"App Store Connect reports appStoreState={live}: the champion is live and for sale."
            if shipped else
            f"Not confirmed shipped-to-production (asc_state={state}, appStoreState={live}). "
            "Fail-closed: requires a live READY_FOR_SALE/READY_FOR_DISTRIBUTION read from Apple "
            "(and valid ASC credentials in the environment)."
        ),
        "status": "PASS" if shipped else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"shipped={shipped} appStoreState={live} asc_state={state} (live ASC read)")
    return 0 if shipped else 1


if __name__ == "__main__":
    sys.exit(main())
