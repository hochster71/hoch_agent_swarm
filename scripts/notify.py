#!/usr/bin/env python3
"""HAS notify fabric — mobile push (ntfy or Pushover). Stdlib only.
Reads config/notify.json (falls back to config/notify.example.json for shape).
Never hardcodes secrets. Usage:
  python3 scripts/notify.py "title" "message" [priority]
Priority: default|high  (maps per channel).
"""
import json, sys, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config/notify.json"

def load():
    if CFG.exists():
        return json.loads(CFG.read_text())
    raise SystemExit("config/notify.json not set — copy config/notify.example.json and fill it.")

def send(title, message, priority="default"):
    c = load(); ch = c.get("channel", "ntfy")
    if ch == "ntfy":
        n = c["ntfy"]; url = n["server"].rstrip("/") + "/" + n["topic"]
        req = urllib.request.Request(url, data=message.encode("utf-8"),
              headers={"Title": title, "Priority": "5" if priority == "high" else "3"})
        urllib.request.urlopen(req, timeout=10); return "ntfy sent"
    if ch == "pushover":
        p = c["pushover"]
        data = urllib.parse.urlencode({"token": p["app_token"], "user": p["user_key"],
               "title": title, "message": message, "priority": 1 if priority == "high" else 0}).encode()
        urllib.request.urlopen(urllib.request.Request("https://api.pushover.net/1/messages.json", data=data), timeout=10)
        return "pushover sent"
    raise SystemExit(f"unknown channel: {ch}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit('usage: notify.py "title" "message" [default|high]')
    print(send(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "default"))
