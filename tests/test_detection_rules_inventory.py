import os
from pathlib import Path

def test_detections_inventory():
    base = Path(__file__).parent.parent
    detections_dir = base / "detections"
    
    families = [
        "delta_tier_privilege_escalation",
        "approval_replay_or_bruteforce",
        "test_approval_misuse",
        "google_frontier_policy_block",
        "local_model_outage_surge"
    ]
    
    for fam in families:
        # Check rule files: splunk (.spl) or sigma (.yml)
        spl_path = detections_dir / "splunk" / f"{fam}.spl"
        sigma_path = detections_dir / "sigma" / f"{fam}.yml"
        assert spl_path.exists() or sigma_path.exists(), f"Missing Splunk/Sigma rule for {fam}"
        
        # Check playbooks
        playbook_path = detections_dir / "playbooks" / f"{fam}.md"
        assert playbook_path.exists(), f"Missing response playbook for {fam}"
        
        # Check fixtures
        fixture_path = detections_dir / "fixtures" / f"{fam}.jsonl"
        assert fixture_path.exists(), f"Missing unit fixture for {fam}"
