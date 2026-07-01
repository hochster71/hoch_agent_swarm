#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.parse
import os

port = os.environ.get("TRACKER_PORT", "3001")
user = os.environ.get("UI_USER", "admin")
password = os.environ.get("UI_PASS", "change-this-password")

url = f"http://127.0.0.1:{port}/api/landscape"
passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
passman.add_password(None, url, user, password)
authhandler = urllib.request.HTTPBasicAuthHandler(passman)
opener = urllib.request.build_opener(authhandler)
urllib.request.install_opener(opener)

try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        ns = data.get("northstar", {})
        domains = data.get("domains", [])
        
        print("==================================================")
        print("HAS/HASF LANDSCAPE COMMAND CENTER STATUS")
        print("==================================================")
        print(f"Executive Verdict:  {ns.get('verdict')}")
        print(f"Verdict Reason:     {ns.get('verdict_reason')}")
        print(f"Overall Progress:   {ns.get('percent_done')}%")
        print(f"Active Blockers:    {ns.get('blocker_count')}")
        print("==================================================")
        print("DOMAIN STATUS LANES")
        print("==================================================")
        
        for d in domains:
            name = d.get("name", "Unknown Domain")
            status = d.get("status", "Queued")
            tasks = d.get("task_count", 0)
            done = d.get("done_count", 0)
            next_action = d.get("next_action", "")
            
            status_pill = f"[{status}]"
            print(f"{name:<32} {status_pill:<14} (Tasks: {done}/{tasks})")
            if next_action:
                print(f"  Next Action: {next_action}")
            print("-" * 50)
            
except Exception as e:
    print(f"Error checking landscape: {e}")
    sys.exit(1)
