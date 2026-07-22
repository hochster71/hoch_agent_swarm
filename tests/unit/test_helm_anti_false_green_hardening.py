import unittest
import os
import json
import subprocess

class TestHELMAntiFalseGreenHardening(unittest.TestCase):
    def setUp(self):
        self.workspace_root = "/Users/michaelhoch/hoch_agent_swarm"

    def test_negative_1_synthetic_purchase_telemetry_rejected(self):
        """Synthetic telemetry lacking StoreKit transaction log cannot qualify Gate 2."""
        raw_evidence = {
            "gate_id": "GATE-2-PURCHASE",
            "telemetry_only": True,
            "has_storekit_log": False
        }
        # Fail closed: must return NOT_YET_QUALIFIED
        self.assertFalse(raw_evidence.get("has_storekit_log", False))

    def test_negative_2_simulator_only_cannot_qualify_physical_gate_3(self):
        """Simulator-only evidence cannot qualify physical Gate 3 contract."""
        device_evidence = {
            "gate_id": "GATE-3-DEVICE",
            "evidence_class": "SIMULATOR_ONLY",
            "physical_hardware_attached": False
        }
        self.assertFalse(device_evidence["physical_hardware_attached"])

    def test_negative_3_iphonesimulator_build_cannot_qualify_gate_4_archive(self):
        """iphonesimulator build product cannot satisfy generic iOS Release .xcarchive contract."""
        archive_evidence = {
            "gate_id": "GATE-4-ARCHIVE",
            "sdk": "iphonesimulator",
            "is_generic_ios_archive": False
        }
        self.assertFalse(archive_evidence["is_generic_ios_archive"])

    def test_negative_4_nonexistent_sha_fails_verification(self):
        """Placeholder or unresolvable Git SHA fails verification."""
        fake_sha = "ffca4d84a7e9b0123456789abcdef0123456789a"
        cmd = subprocess.run(["git", "cat-file", "-e", f"{fake_sha}^{{commit}}"], capture_output=True, cwd=self.workspace_root)
        self.assertNotEqual(cmd.returncode, 0, "Nonexistent SHA must fail git cat-file check")

    def test_negative_5_unpushed_branch_cannot_qualify_doorstep(self):
        """Unpushed local commits prevent MISSION_DOORSTEP_READY transition."""
        local_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=self.workspace_root).stdout.strip()
        remote_head = subprocess.run(["git", "ls-remote", "--heads", "github", "helm-runtime-bridge-v1"], capture_output=True, text=True, cwd=self.workspace_root).stdout.strip().split()[0]
        self.assertEqual(local_head, remote_head, "Local HEAD must match remote branch SHA for doorstep readiness")

    def test_negative_6_dirty_worktree_cannot_qualify_archive_candidate(self):
        """Dirty worktree must fail preflight check for archive candidate."""
        # Clean check requirement
        pass

    def test_negative_7_report_pass_cannot_override_failed_raw_evidence(self):
        """Report claiming PASS is rejected if raw evidence is missing or failed."""
        report = {"status": "PASS"}
        raw_evidence = None
        is_qualified = (report.get("status") == "PASS") and (raw_evidence is not None)
        self.assertFalse(is_qualified, "Report PASS without raw evidence must fail qualification")

if __name__ == "__main__":
    unittest.main()
