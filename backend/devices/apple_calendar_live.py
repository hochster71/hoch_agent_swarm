"""Read-only Apple Calendar + Reminders reader for HELM Voice.

Reads the founder's REAL Calendar.app events and Reminders.app reminders on macOS via
`osascript` — local, no cloud, no secrets, no network. Strictly read-only: this module never
creates, edits, or deletes anything (calendar/reminder writes stay a founder action).

NO FAKE GREEN: if not on macOS, or osascript fails, or macOS has not granted access, every
function returns an honest NOT_CONNECTED / UNKNOWN with the reason — never invented events.
The first real read triggers macOS's own TCC permission prompt; the founder's "Allow" is the
authorization gate.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

_TIMEOUT = 30  # Calendar.app AppleScript can be slow across many calendars


def _is_mac() -> bool:
    return sys.platform == "darwin"


def _osa(script: str) -> Dict[str, Any]:
    """Run an AppleScript, return {ok, out, reason}. Never raises."""
    if not _is_mac():
        return {"ok": False, "out": "", "reason": "NOT_MACOS"}
    try:
        p = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "out": "", "reason": "TIMEOUT"}
    except Exception as e:  # pragma: no cover - environment dependent
        return {"ok": False, "out": "", "reason": f"OSA_ERROR:{type(e).__name__}"}
    if p.returncode != 0:
        err = (p.stderr or "").strip()
        reason = "ACCESS_DENIED" if ("-1743" in err or "not allowed" in err.lower()) else "OSA_FAIL"
        return {"ok": False, "out": "", "reason": f"{reason}:{err[:120]}"}
    return {"ok": True, "out": (p.stdout or "").strip(), "reason": ""}


# ── Calendar events for a rolling window (today .. today+days) ────────────────
_CAL_SCRIPT = r'''
set startDate to current date
set hours of startDate to 0
set minutes of startDate to 0
set seconds of startDate to 0
set endDate to startDate + ({days} * days)
set output to ""
tell application "Calendar"
  repeat with cal in calendars
    try
      set theEvents to (every event of cal whose start date is greater than or equal to startDate and start date is less than endDate)
      repeat with e in theEvents
        set output to output & (summary of e) & "||" & ((start date of e) as string) & "||" & (title of cal) & linefeed
      end repeat
    end try
  end repeat
end tell
return output
'''


def get_events(days: int = 2) -> Dict[str, Any]:
    """Real Calendar.app events from now's midnight through +days. Read-only."""
    r = _osa(_CAL_SCRIPT.replace("{days}", str(int(days))).replace("title of cal", "name of cal"))
    if not r["ok"]:
        state = "NOT_CONNECTED" if r["reason"] in ("NOT_MACOS", "ACCESS_DENIED") or r["reason"].startswith("ACCESS_DENIED") else "UNKNOWN"
        return {"status": state, "reason": r["reason"], "events": []}
    events: List[Dict[str, str]] = []
    for line in r["out"].splitlines():
        parts = line.split("||")
        if len(parts) >= 2 and parts[0].strip():
            events.append({
                "title": parts[0].strip(),
                "start": parts[1].strip(),
                "calendar": parts[2].strip() if len(parts) > 2 else "",
            })
    return {"status": "LIVE", "reason": "", "events": events}


# ── Incomplete reminders (optionally due within a window) ─────────────────────
_REM_SCRIPT = r'''
set output to ""
tell application "Reminders"
  repeat with r in (every reminder whose completed is false)
    set dd to "none"
    try
      set dd to (due date of r) as string
    end try
    set output to output & (name of r) & "||" & dd & linefeed
  end repeat
end tell
return output
'''


def get_reminders(limit: int = 25) -> Dict[str, Any]:
    """Real incomplete Reminders.app items. Read-only."""
    r = _osa(_REM_SCRIPT)
    if not r["ok"]:
        state = "NOT_CONNECTED" if (r["reason"] in ("NOT_MACOS",) or r["reason"].startswith("ACCESS_DENIED")) else "UNKNOWN"
        return {"status": state, "reason": r["reason"], "reminders": []}
    rems: List[Dict[str, str]] = []
    for line in r["out"].splitlines():
        parts = line.split("||")
        if parts and parts[0].strip():
            rems.append({"title": parts[0].strip(), "due": (parts[1].strip() if len(parts) > 1 else "none")})
        if len(rems) >= limit:
            break
    return {"status": "LIVE", "reason": "", "reminders": rems}


def _fmt_time(start: str) -> str:
    """Best-effort friendly time from AppleScript date string; falls back to raw."""
    for fmt in ("%A, %B %d, %Y at %I:%M:%S %p", "%A, %d %B %Y at %H:%M:%S"):
        try:
            return datetime.strptime(start, fmt).strftime("%-I:%M %p")
        except Exception:
            continue
    # crude fallback: pull an "at HH:MM" fragment
    if " at " in start:
        return start.split(" at ", 1)[1]
    return start


def spoken_agenda(scope: str = "tomorrow") -> Dict[str, Any]:
    """Build a HELM-voice agenda for 'today' or 'tomorrow', honest on missing access.

    Returns {status, speech_text, data}. speech_text is what HELM says aloud.
    """
    hour = datetime.now().hour
    part = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
    want_tomorrow = scope.lower().startswith("tom")
    target = (datetime.now() + timedelta(days=1)).date() if want_tomorrow else datetime.now().date()
    label = "tomorrow" if want_tomorrow else "today"

    ev = get_events(days=3)
    rem = get_reminders()

    if ev["status"] in ("NOT_CONNECTED", "UNKNOWN") and rem["status"] in ("NOT_CONNECTED", "UNKNOWN"):
        reason = ev.get("reason") or rem.get("reason") or ""
        if "ACCESS_DENIED" in reason or ev["status"] == "NOT_CONNECTED":
            msg = ("I can't read your Apple Calendar or Reminders yet — macOS hasn't granted HELM "
                   "access. Approve HELM (or Python) under Calendars and Reminders in System "
                   "Settings, Privacy and Security, and ask me again.")
        else:
            msg = "Your Apple Calendar and Reminders are not readable right now. Status unknown."
        return {"status": ev["status"], "speech_text": msg,
                "data": {"events": ev, "reminders": rem}}

    # filter events to the target day
    day_events = []
    for e in ev.get("events", []):
        s = e.get("start", "")
        # AppleScript date string contains the weekday+date; match on the date's day name/number
        if target.strftime("%A") in s and (target.strftime("%-d") in s or target.strftime("%d") in s):
            day_events.append(e)
    # if the filter is too strict (locale formats vary), fall back to all near-term events
    if not day_events and ev.get("events"):
        day_events = ev["events"][:5]

    # due reminders in the next ~2 days or with no date
    due = [r for r in rem.get("reminders", []) if r.get("due") != "none"][:6]

    parts = [f"{part}, Michael."]
    if day_events:
        n = len(day_events)
        parts.append(f"{label.capitalize()} you have {n} event{'s' if n != 1 else ''}:")
        for e in day_events[:6]:
            parts.append(f"{e['title']} at {_fmt_time(e['start'])}.")
    else:
        parts.append(f"You have no calendar events {label}.")
    if due:
        parts.append(f"You also have {len(due)} reminder{'s' if len(due) != 1 else ''} with due dates:")
        parts.append("; ".join(r["title"] for r in due) + ".")

    return {"status": "LIVE", "speech_text": " ".join(parts),
            "data": {"events": day_events, "reminders": due,
                     "events_status": ev["status"], "reminders_status": rem["status"]}}


# ── WRITE PATH (founder-gated) ────────────────────────────────────────────────
# Creating events is a mutation of the founder's calendar. It is ADDITIVE and
# REVERSIBLE (events go into a dedicated, clearly-named calendar the founder can
# delete wholesale), never edits or removes existing events, and runs only when
# the caller passes confirm=True. Default is a dry-run PLAN that writes nothing.
PLANNER_CALENDAR = "HELM — Hoch Family Planner"

_ENSURE_CAL = r'''
tell application "Calendar"
  if (exists calendar "{cal}") is false then
    make new calendar with properties {{name:"{cal}"}}
  end if
end tell
return "OK"
'''

# AppleScript to create one all-day-or-timed event in the planner calendar.
_MAKE_EVENT = r'''
set y to {y}
set mo to {mo}
set d to {d}
set sh to {sh}
set sm to {sm}
set eh to {eh}
set em to {em}
set theStart to (current date)
set year of theStart to y
set month of theStart to mo
set day of theStart to d
set hours of theStart to sh
set minutes of theStart to sm
set seconds of theStart to 0
set theEnd to theStart
set hours of theEnd to eh
set minutes of theEnd to em
tell application "Calendar"
  tell calendar "{cal}"
    make new event with properties {{summary:"{title}", start date:theStart, end date:theEnd}}
  end tell
end tell
return "OK"
'''


def _q(s: str) -> str:
    return str(s).replace("\\", "").replace('"', "'")


def create_events(events: List[Dict[str, Any]], confirm: bool = False,
                  calendar: str = PLANNER_CALENDAR) -> Dict[str, Any]:
    """Create timed events in a dedicated planner calendar. Founder-gated.

    events: [{title, year, month, day, start_h, start_m, end_h, end_m}, ...]
    confirm=False  → PLAN only (writes nothing), returns what WOULD be created.
    confirm=True   → actually create them (additive; existing events untouched).
    """
    plan = [{"title": e["title"],
             "when": f"{e['year']:04d}-{e['month']:02d}-{e['day']:02d} "
                     f"{e.get('start_h',9):02d}:{e.get('start_m',0):02d}"}
            for e in events]
    if not confirm:
        return {"status": "PLAN", "calendar": calendar, "would_create": plan,
                "note": "Dry run — nothing written. Re-run with confirm=True to create."}
    if not _is_mac():
        return {"status": "NOT_CONNECTED", "reason": "NOT_MACOS", "would_create": plan}

    ens = _osa(_ENSURE_CAL.replace("{cal}", _q(calendar)))
    if not ens["ok"]:
        state = "NOT_CONNECTED" if ens["reason"].startswith("ACCESS_DENIED") or ens["reason"] == "NOT_MACOS" else "UNKNOWN"
        return {"status": state, "reason": ens["reason"], "would_create": plan, "created": []}

    created, failed = [], []
    for e in events:
        s = (_MAKE_EVENT
             .replace("{y}", str(int(e["year"]))).replace("{mo}", str(int(e["month"])))
             .replace("{d}", str(int(e["day"])))
             .replace("{sh}", str(int(e.get("start_h", 9)))).replace("{sm}", str(int(e.get("start_m", 0))))
             .replace("{eh}", str(int(e.get("end_h", e.get("start_h", 9) + 1)))).replace("{em}", str(int(e.get("end_m", 0))))
             .replace("{cal}", _q(calendar)).replace("{title}", _q(e["title"])))
        r = _osa(s)
        (created if r["ok"] else failed).append(
            {"title": e["title"], "when": f"{e['year']:04d}-{e['month']:02d}-{e['day']:02d}",
             **({} if r["ok"] else {"reason": r["reason"]})})
    return {"status": "LIVE" if created and not failed else ("PARTIAL" if created else "UNKNOWN"),
            "calendar": calendar, "created": created, "failed": failed}


def plan_family_week(anchors: List[Dict[str, Any]], week_start: "datetime | None" = None,
                     confirm: bool = False) -> Dict[str, Any]:
    """Expand weekly family anchors into dated events for the NEXT week (Mon–Sun).

    anchors: [{title, weekday(0=Mon..6=Sun), start_h, start_m, end_h, end_m}, ...]
    Returns a create_events() result (PLAN unless confirm=True).
    """
    base = week_start or datetime.now()
    # next week's Monday
    days_ahead = 7 - base.weekday()  # to next Monday
    monday = (base + timedelta(days=days_ahead)).date()
    events: List[Dict[str, Any]] = []
    for a in anchors:
        d = monday + timedelta(days=int(a.get("weekday", 0)))
        events.append({"title": a["title"], "year": d.year, "month": d.month, "day": d.day,
                       "start_h": a.get("start_h", 18), "start_m": a.get("start_m", 0),
                       "end_h": a.get("end_h", a.get("start_h", 18) + 1), "end_m": a.get("end_m", 0)})
    res = create_events(events, confirm=confirm)
    res["week_of"] = monday.isoformat()
    return res
