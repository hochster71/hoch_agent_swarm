import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

import backend.homemesh_runtime_asset_graph as hm

def run_test():
    # Reset
    hm.RECONCILED_DEVICES.clear()
    hm.EVIDENCE_OBSERVATIONS.clear()
    
    # Insert stale observation
    hm.EVIDENCE_OBSERVATIONS.append({
        "id": "obs-stale-test",
        "timestamp": "2026-07-06T10:00:00Z", # hours ago
        "source": "ARP Table Parser",
        "device_id": None,
        "mac_address": "de:ad:be:ef:12:34",
        "observed_ip": "10.0.0.199",
        "observed_hostname": "test-stale-host",
        "confidence": 0.5,
        "details": {}
    })
    
    hm.reconcile_devices()
    dev = hm.RECONCILED_DEVICES.get("de:ad:be:ef:12:34")
    assert dev is not None
    print(f"Device status: {dev['online_status']}")
    print(f"Stale status: {dev['stale_status']}")
    print(f"Source classification: {dev['source_classification']}")
    print(f"Automation allowed: {dev['automation_allowed']}")
    
    assert dev["online_status"] == "stale"
    assert dev["stale_status"] is True
    assert dev["source_classification"] == "stale_previous"
    assert dev["automation_allowed"] is False
    print("PASS: Stale device test succeeded.")

if __name__ == "__main__":
    run_test()
