"""Apply Epic Fury 2026 TestFlight Test Information via the App Store Connect API.

Sets the Beta App Localization (description + feedback email) and the latest build's
"What to Test" (betaBuildLocalizations.whatsNew). Content mirrors
docs/products/epic-fury-2026/TESTFLIGHT_TEST_INFO.md.

SAFE BY DEFAULT: dry-run — prints exactly what it WOULD do and changes nothing. Pass
--apply to actually write. Uses the founder's ASC creds from the environment (never
logged). This is a FOUNDER-run action (writes to your Apple account).

    .venv/bin/python3 scripts/goal/asc_write_testinfo.py            # dry run
    .venv/bin/python3 scripts/goal/asc_write_testinfo.py --apply    # write
"""
from __future__ import annotations

import sys
import pathlib

# Allow running as a standalone script (python3 scripts/goal/asc_write_testinfo.py):
# put the repo root on sys.path so the package import resolves.
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.goal.asc_client import (ASC_BASE, ASCUnavailable, _app_id,
                                     _bearer_token, _get)

DESCRIPTION = (
    "Epic Fury 2026 is a dark-mode, military HUD-style tactical intelligence dashboard. "
    "Monitor a real-time tactical feed of intel reports with confidence metrics, a live "
    "AI-agent roster grid (status, logs, telemetry), and an interactive DMO canvas "
    "simulation. This beta validates real-time feed reliability, dashboard performance, "
    "and the subscription flow."
)
FEEDBACK_EMAIL = "michael.b.hoch@gmail.com"
WHATS_NEW = (
    "What to test:\n"
    "- Real-time tactical feed: intel reports stream in; confidence metrics render.\n"
    "- AI Agent Roster Grid: agent cards update live (logs, telemetry) without stalls.\n"
    "- DMO Canvas Simulation: the scenario map is interactive and smooth.\n"
    "- Subscription/paywall (Stripe/RevenueCat): purchase, restore, and gated unlock.\n"
    "- General: dark-mode legibility, layout on your device, reconnect after network loss."
)


def _write(method: str, path: str, payload: dict, apply: bool) -> None:
    if not apply:
        print(f"  DRY-RUN would {method} {path}")
        return
    import requests
    r = requests.request(method, f"{ASC_BASE}{path}",
                         headers={"Authorization": f"Bearer {_bearer_token()}",
                                  "Content-Type": "application/json"},
                         json=payload, timeout=25)
    if r.status_code >= 400:
        raise ASCUnavailable(f"{method} {path} -> {r.status_code}: {r.text[:200]}")
    print(f"  OK {method} {path} -> {r.status_code}")


def run(apply: bool) -> int:
    try:
        app_id = _app_id(__import__("os").environ.get("HELM_ASC_BUNDLE_ID") or "com.epicfury.dashboard")
    except ASCUnavailable as e:
        print(f"FAIL-CLOSED: {e}")
        return 2
    print(f"app id: {app_id}   mode: {'APPLY' if apply else 'DRY-RUN'}")

    # 1. Beta App Localization (description + feedback email) --------------
    locs = _get(f"/apps/{app_id}/betaAppLocalizations", {"limit": 10}).get("data", [])
    attrs = {"description": DESCRIPTION, "feedbackEmail": FEEDBACK_EMAIL}
    if locs:
        lid = locs[0]["id"]
        print(f"  beta app localization exists ({locs[0]['attributes'].get('locale')}) -> update")
        _write("PATCH", f"/betaAppLocalizations/{lid}",
               {"data": {"type": "betaAppLocalizations", "id": lid, "attributes": attrs}}, apply)
    else:
        print("  no beta app localization -> create en-US")
        _write("POST", "/betaAppLocalizations",
               {"data": {"type": "betaAppLocalizations",
                         "attributes": {**attrs, "locale": "en-US"},
                         "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}}, apply)

    # 2. Latest build "What to Test" (betaBuildLocalizations.whatsNew) -----
    builds = _get("/builds", {"filter[app]": app_id, "sort": "-uploadedDate", "limit": 1}).get("data", [])
    if not builds:
        print("  no build uploaded yet -> skip 'What to Test' (upload a build first)")
        return 0
    bid = builds[0]["id"]
    bver = builds[0]["attributes"].get("version")
    bl = _get(f"/builds/{bid}/betaBuildLocalizations", {"limit": 10}).get("data", [])
    if bl:
        blid = bl[0]["id"]
        print(f"  build {bver} localization exists -> update whatsNew")
        _write("PATCH", f"/betaBuildLocalizations/{blid}",
               {"data": {"type": "betaBuildLocalizations", "id": blid, "attributes": {"whatsNew": WHATS_NEW}}}, apply)
    else:
        print(f"  build {bver} has no localization -> create en-US whatsNew")
        _write("POST", "/betaBuildLocalizations",
               {"data": {"type": "betaBuildLocalizations",
                         "attributes": {"locale": "en-US", "whatsNew": WHATS_NEW},
                         "relationships": {"build": {"data": {"type": "builds", "id": bid}}}}}, apply)
    return 0


if __name__ == "__main__":
    apply = "--apply" in sys.argv[1:]
    try:
        raise SystemExit(run(apply))
    except ASCUnavailable as e:
        print(f"FAIL-CLOSED: {e}")
        raise SystemExit(2)
