import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.prompt_registry import PromptRegistry

class TestPromptRegistryHealth(unittest.TestCase):
    def test_get_manifest_health_missing(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            registry = PromptRegistry(base_dir=tmp_path)
            health = registry.get_manifest_health()
            self.assertEqual(health["validation_status"], "FAIL_CLOSED")
            self.assertEqual(health["total_agents"], 0)

    def test_get_manifest_health_valid(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create manifest structure
            manifest_dir = tmp_path / "data" / "prompt_registry"
            manifest_dir.mkdir(parents=True)
            manifest_file = manifest_dir / "agents.manifest.json"
            
            mock_manifest = {
                "name": "HOCH Agent Capability Registry",
                "version": "4.0.0",
                "created_for": "HOCH Agent Swarm",
                "total_agents": 558,
                "active_agents": 539,
                "deprecated_agents": 19,
                "duplicate_count": 19,
                "broken_link_count": 0,
                "last_validation_timestamp": "2026-07-05T12:00:00Z",
                "validation_status": "PASS",
                "entries": []
            }
            manifest_file.write_text(json.dumps(mock_manifest), encoding="utf-8")
            
            registry = PromptRegistry(base_dir=tmp_path)
            health = registry.get_manifest_health()
            self.assertEqual(health["validation_status"], "PASS")
            self.assertEqual(health["total_agents"], 558)
            self.assertEqual(health["active_agents"], 539)

    def test_get_manifest_health_invalid_status_fail_closed(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manifest_dir = tmp_path / "data" / "prompt_registry"
            manifest_dir.mkdir(parents=True)
            manifest_file = manifest_dir / "agents.manifest.json"
            
            mock_manifest = {
                "name": "HOCH Agent Capability Registry",
                "version": "4.0.0",
                "created_for": "HOCH Agent Swarm",
                "total_agents": 558,
                "active_agents": 539,
                "deprecated_agents": 19,
                "duplicate_count": 19,
                "broken_link_count": 5,
                "last_validation_timestamp": "2026-07-05T12:00:00Z",
                "validation_status": "FAIL",  # Failing status
                "entries": []
            }
            manifest_file.write_text(json.dumps(mock_manifest), encoding="utf-8")
            
            registry = PromptRegistry(base_dir=tmp_path)
            health = registry.get_manifest_health()
            
            # Should map to FAIL_CLOSED
            self.assertEqual(health["validation_status"], "FAIL_CLOSED")
            self.assertEqual(registry.status, "FAIL_CLOSED")

if __name__ == "__main__":
    unittest.main()
