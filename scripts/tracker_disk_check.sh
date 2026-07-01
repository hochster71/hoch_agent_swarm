#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.parse
import os

port = os.environ.get("TRACKER_PORT", "3001")
user = os.environ.get("UI_USER", "admin")
password = os.environ.get("UI_PASS", "change-this-password")

url = f"http://127.0.0.1:{port}/api/disk"
passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
passman.add_password(None, url, user, password)
authhandler = urllib.request.HTTPBasicAuthHandler(passman)
opener = urllib.request.build_opener(authhandler)
urllib.request.install_opener(opener)

try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        print("--------------------------------------------------")
        print("DISK SAFETY SCORECARD")
        print("--------------------------------------------------")
        print(f"Total Space:      {data['disk_total']} GB")
        print(f"Used Space:       {data['disk_used']} GB")
        print(f"Available Space:  {data['disk_available']} GB")
        print(f"Used Capacity:    {data['disk_capacity_percent']}%")
        print(f"Backups Size:     {data['snapshot_dir_size']} GB")
        print(f"Snapshot Allowed: {data['snapshot_allowed']}")
        if data.get('warning'):
            print(f"Alert Warning:    {data['warning']}")
        print("--------------------------------------------------")
except Exception as e:
    print(f"Error checking disk space: {e}")
    sys.exit(1)
