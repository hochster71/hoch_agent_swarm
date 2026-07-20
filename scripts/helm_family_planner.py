#!/usr/bin/env python3
"""HELM — Hoch Family Planner → Apple Calendar (next week).

Founder-gated, additive, reversible. Creates a full family week in a DEDICATED calendar
named "HELM — Hoch Family Planner" — your existing calendars are never touched, and you can
delete the whole planner calendar in one action if you don't like it.

    python3 scripts/helm_family_planner.py          # PLAN — prints the exact events, writes NOTHING
    python3 scripts/helm_family_planner.py --go      # CREATE the events in Apple Calendar

The first --go run triggers macOS's Calendar-access prompt; your "Allow" is the authorization.
Runs on the Mac hosting HELM (needs Calendar.app). No secrets, no network.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.devices.apple_calendar_live import plan_family_week, PLANNER_CALENDAR

# weekday: 0=Mon 1=Tue 2=Wed 3=Thu 4=Fri 5=Sat 6=Sun ; times 24h.
# Template picks: weeknight dinners + weekend planning/meals + kids/activities + weekly reset.
ANCHORS = [
    # Weeknight family dinners (Mon–Fri)
    *[{"title": "Family Dinner", "weekday": wd, "start_h": 18, "end_h": 19} for wd in range(5)],
    # Weekend dinners
    {"title": "Family Dinner", "weekday": 5, "start_h": 18, "end_h": 19},
    {"title": "Family Dinner", "weekday": 6, "start_h": 18, "end_h": 19},
    # Kids / activities placeholders (rename freely)
    {"title": "Homework Hour", "weekday": 0, "start_h": 19, "end_h": 20},
    {"title": "Homework Hour", "weekday": 1, "start_h": 19, "end_h": 20},
    {"title": "Homework Hour", "weekday": 3, "start_h": 19, "end_h": 20},
    {"title": "Kids Activity", "weekday": 1, "start_h": 16, "end_h": 17},
    {"title": "Kids Activity", "weekday": 3, "start_h": 16, "end_h": 17},
    {"title": "Family Activity", "weekday": 5, "start_h": 9, "end_h": 11},
    # Weekend planning + meals
    {"title": "Meal Planning & Groceries", "weekday": 6, "start_h": 10, "end_h": 11},
    # Weekly reset + admin
    {"title": "Plan the Weekend", "weekday": 4, "start_h": 17, "end_h": 18},
    {"title": "Mid-week Family Check-in", "weekday": 2, "start_h": 19, "end_h": 20},
    {"title": "Weekly Family Reset", "weekday": 6, "start_h": 20, "end_h": 21},
]

DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def main():
    go = "--go" in sys.argv
    res = plan_family_week(ANCHORS, confirm=go)
    print(f"\nHELM — Hoch Family Planner  ·  calendar: {PLANNER_CALENDAR}")
    print(f"Week of {res.get('week_of')}  ·  {'CREATE' if go else 'PLAN (dry run — nothing written)'}\n")
    items = res.get("created") if go else res.get("would_create")
    for e in (items or []):
        when = e.get("when", "")
        print(f"  • {e['title']:<26} {when}")
    if go:
        print(f"\nstatus: {res['status']}  created: {len(res.get('created') or [])}"
              f"  failed: {len(res.get('failed') or [])}")
        if res.get("failed"):
            print("  failed:", json.dumps(res["failed"], indent=2))
        if res["status"] == "NOT_CONNECTED":
            print("\n⚠ macOS hasn't granted Calendar access. Approve it in System Settings ▸ "
                  "Privacy & Security ▸ Calendars, then re-run with --go.")
    else:
        print(f"\n{len(items or [])} events staged. Re-run with --go to create them in Apple Calendar:")
        print("  python3 scripts/helm_family_planner.py --go")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
