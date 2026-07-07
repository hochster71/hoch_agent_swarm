import os
import sys
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

import backend.homemesh_runtime_asset_graph as hm

class TestHomeMeshSpatialGraph(unittest.TestCase):
    def setUp(self):
        # Clear/Reset store
        hm.RECONCILED_DEVICES.clear()
        hm.EVIDENCE_OBSERVATIONS.clear()
        hm.ALERTS.clear()
        hm.init_property_context()

    def test_schema_validation(self):
        # Assert schema files exist
        self.assertTrue(hm.PROPERTY_SCHEMA_PATH.exists())
        self.assertTrue(hm.ROOM_SCHEMA_PATH.exists())
        
        # Verify they are valid JSON
        prop = json.loads(hm.PROPERTY_SCHEMA_PATH.read_text(encoding="utf-8"))
        room = json.loads(hm.ROOM_SCHEMA_PATH.read_text(encoding="utf-8"))
        
        self.assertIn("parcel", prop["properties"])
        self.assertIn("rooms", room["properties"])


    def test_evidence_ingestion_and_mac_merge(self):
        # Add two observations for same MAC
        hm.EVIDENCE_OBSERVATIONS.append({
            "id": "obs-1",
            "timestamp": "2026-07-06T22:00:00Z",
            "source": "ARP Table Parser",
            "device_id": None,
            "mac_address": "00:11:22:33:44:55",
            "observed_ip": "10.0.0.50",
            "observed_hostname": "lg-webos-tv.local",
            "confidence": 0.5,
            "details": {}
        })
        hm.EVIDENCE_OBSERVATIONS.append({
            "id": "obs-2",
            "timestamp": "2026-07-06T22:01:00Z",
            "source": "SSDP Discovery",
            "device_id": None,
            "mac_address": "00:11:22:33:44:55",
            "observed_ip": "10.0.0.50",
            "observed_hostname": "lg-webos-tv.local",
            "confidence": 0.6,
            "details": {}
        })
        
        hm.reconcile_devices()
        
        # The reconciler should merge the two observations into a single device record
        self.assertTrue(len(hm.RECONCILED_DEVICES) >= 2)

        tv = hm.RECONCILED_DEVICES.get("00:11:22:33:44:55")
        self.assertIsNotNone(tv)
        self.assertEqual(tv["ip_address"], "10.0.0.50")
        self.assertIn("ARP Table Parser", tv["evidence_sources"])
        self.assertIn("SSDP Discovery", tv["evidence_sources"])

    def test_stale_device_detection(self):
        # Create an observation in the past
        hm.EVIDENCE_OBSERVATIONS.append({
            "id": "obs-stale",
            "timestamp": "2026-07-06T20:00:00Z", # hours ago
            "source": "ARP Table Parser",
            "device_id": None,
            "mac_address": "99:88:77:66:55:44",
            "observed_ip": "10.0.0.99",
            "observed_hostname": "stale-host",
            "confidence": 0.5,
            "details": {}
        })
        hm.reconcile_devices()
        dev = hm.RECONCILED_DEVICES.get("99:88:77:66:55:44")
        self.assertIsNotNone(dev)
        self.assertEqual(dev["online_status"], "stale")

    def test_unknown_device_alert_creation(self):
        # Discover a new unknown MAC
        hm.EVIDENCE_OBSERVATIONS.append({
            "id": "obs-new",
            "timestamp": "2026-07-06T22:00:00Z",
            "source": "ARP Table Parser",
            "device_id": None,
            "mac_address": "bb:aa:cc:dd:ee:ff",
            "observed_ip": "10.0.0.180",
            "observed_hostname": "unseen-host",
            "confidence": 0.5,
            "details": {}
        })
        hm.reconcile_devices()
        
        # An alert should be created in the alerts log
        self.assertTrue(len(hm.ALERTS) > 0)
        self.assertEqual(hm.ALERTS[0]["mac_address"], "bb:aa:cc:dd:ee:ff")

    def test_manual_room_assignment_and_resolver(self):
        # Manually map a device
        hm.manual_map_device({
            "mac_address": "44:55:66:77:88:99",
            "room_id": "garage",
            "zone_id": "exterior"
        })
        
        hm.reconcile_devices()
        
        dev = hm.RECONCILED_DEVICES.get("44:55:66:77:88:99")
        self.assertIsNotNone(dev)
        self.assertEqual(dev["room_id"], "garage")
        self.assertEqual(dev["zone_id"], "exterior")
        self.assertEqual(dev["confidence_score"], 90.0)

    def test_brain_evidence_citation(self):
        hm.reconcile_devices()
        # BRAIN queries assets, and can see the list of evidence sources for each device
        for dev in hm.RECONCILED_DEVICES.values():
            self.assertTrue(len(dev["evidence_sources"]) > 0)
            # Source should cite where the claims came from
            self.assertTrue(any(src in ["manual_import", "ARP Table Parser", "DHCP Lease Importer", "mDNS Discovery", "SSDP Discovery", "UDM/UniFi Controller Adapter", "Home Assistant Adapter"] for src in dev["evidence_sources"]))

    def test_fail_closed_behavior(self):
        # A discovered unknown device must have a low trust score
        hm.EVIDENCE_OBSERVATIONS.append({
            "id": "obs-untrusted",
            "timestamp": "2026-07-06T22:00:00Z",
            "source": "ARP Table Parser",
            "device_id": None,
            "mac_address": "ff:ff:ff:ee:ee:ee",
            "observed_ip": "10.0.0.222",
            "observed_hostname": "attacker-host",
            "confidence": 0.5,
            "details": {}
        })
        hm.reconcile_devices()
        
        dev = hm.RECONCILED_DEVICES.get("ff:ff:ff:ee:ee:ee")
        self.assertIsNotNone(dev)
        self.assertEqual(dev["room_id"], "unmapped_devices")
        self.assertEqual(dev["zone_id"], "unmapped_zones")
        # Assert low trust score is enforced
        self.assertTrue(dev["trust_score"] <= 30.0)

if __name__ == "__main__":
    unittest.main()
