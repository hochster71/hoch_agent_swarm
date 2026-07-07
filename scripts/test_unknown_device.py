import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

import backend.homemesh_runtime_asset_graph as hm

def run_test():
    # Reset
    hm.RECONCILED_DEVICES.clear()
    hm.EVIDENCE_OBSERVATIONS.clear()
    hm.ALERTS.clear()
    
    # Inject unknown observation
    hm.EVIDENCE_OBSERVATIONS.append({
        "id": "obs-unknown-test",
        "timestamp": hm.get_now_iso(),
        "source": "ARP Table Parser",
        "device_id": None,
        "mac_address": "ff:ff:ff:ee:ee:ee",
        "observed_ip": "10.0.0.222",
        "observed_hostname": "attacker-host",
        "confidence": 0.5,
        "details": {}
    })
    
    hm.reconcile_devices()
    
    # Verify it appears in unknown devices list
    unknowns = [d for d in hm.RECONCILED_DEVICES.values() if d["device_type"] == "unknown" or "untrusted" in d["tags"]]
    assert len(unknowns) > 0
    dev = hm.RECONCILED_DEVICES.get("ff:ff:ff:ee:ee:ee")
    assert dev is not None
    
    print(f"Unknown device: {dev['display_name']}")
    print(f"Trust score: {dev['trust_score']}")
    print(f"Automation allowed: {dev['automation_allowed']}")
    print(f"Alert count: {len(hm.ALERTS)}")
    if len(hm.ALERTS) > 0:
        print(f"Alert message: {hm.ALERTS[0]['message']}")
        
    assert dev["trust_score"] <= 30.0
    assert dev["automation_allowed"] is False
    assert len(hm.ALERTS) > 0
    assert hm.ALERTS[0]["mac_address"] == "ff:ff:ff:ee:ee:ee"
    print("PASS: Unknown device fail-closed test succeeded.")

if __name__ == "__main__":
    run_test()
