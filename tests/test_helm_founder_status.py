#!/usr/bin/env python3
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "helm_founder_status_contract.json"
COMMAND = ROOT / "scripts" / "helm-status"


class HelmFounderStatusBaselineTests(unittest.TestCase):
    def test_canonical_files_exist(self):
        self.assertTrue(COMMAND.exists())
        self.assertTrue((ROOT / "scripts" / "helm_founder_status.py").exists())
        self.assertTrue(CONTRACT.exists())

    def test_contract_keeps_baseline_sections(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        required = {
            "HELM FOUNDER CONSOLE",
            "MISSION",
            "BURNDOWN TO 100%",
            "CRITICAL CONTROLS",
            "CRITICAL PATH",
            "FOUNDER-ONLY GATES",
            "RUNTIME AND EVIDENCE",
            "SECURITY AND RISK",
            "PROMOTION",
            "NEXT FOUNDER ACTION",
            "EVIDENCE SOURCES",
            "NO FAKE GREEN",
        }
        self.assertTrue(required.issubset(set(contract["baseline_sections"])))
        self.assertEqual(contract["canonical_command"], "bash scripts/helm-status")

    def test_console_renders_baseline(self):
        result = subprocess.run(
            ["bash", str(COMMAND)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertIn(result.returncode, (0, 2))
        output = result.stdout
        for section in (
            "HELM FOUNDER CONSOLE",
            "BURNDOWN TO 100%",
            "CRITICAL CONTROLS",
            "PROMOTION",
            "NO FAKE GREEN",
        ):
            self.assertIn(section, output)

    def test_no_fake_green_guard_is_present(self):
        source = (ROOT / "scripts" / "helm_founder_status.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("if blockers and completion >= 100.0", source)
        self.assertIn("100% is prohibited", source)


if __name__ == "__main__":
    unittest.main()
