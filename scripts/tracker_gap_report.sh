#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.parse
import os

port = os.environ.get("TRACKER_PORT", "3001")
user = os.environ.get("UI_USER", "admin")
password = os.environ.get("UI_PASS", "change-this-password")

url = f"http://127.0.0.1:{port}/api/gaps"
passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
passman.add_password(None, url, user, password)
authhandler = urllib.request.HTTPBasicAuthHandler(passman)
opener = urllib.request.build_opener(authhandler)
urllib.request.install_opener(opener)

try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        gaps = data.get("gaps", [])
        print("==================================================")
        print(f"HAS/HASF ACTIVE GAP ANALYSIS REPORT ({len(gaps)} active)")
        print("==================================================")
        
        for g in gaps:
            sev = g.get("severity", "P2")
            name = g.get("name", "Unknown Gap")
            domain = g.get("domain", "General")
            owner = g.get("owner", "System")
            blocker = g.get("blocker", "")
            fix = g.get("fix", "")
            
            print(f"[{sev}] {name} (Domain: {domain})")
            print(f"  Owner:      {owner}")
            print(f"  Blocker:    {blocker}")
            print(f"  Fix:        {fix}")
            print("-" * 50)
            
except Exception as e:
    print(f"Error checking gaps: {e}")
    sys.exit(1)
