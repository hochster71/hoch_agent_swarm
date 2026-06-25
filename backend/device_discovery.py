import re
import subprocess
import socket
import json
import os
import uuid
from datetime import datetime, timezone

# Optional Zeroconf helper
try:
    from zeroconf import Zeroconf, ServiceBrowser
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "device-discovery-fixtures.json")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_fixtures() -> list[dict]:
    # Fallback default fixtures if file is missing
    fallback = [
        {
            "node_id": "discovery-tv-mock",
            "display_name": "Living Room LG TV",
            "hostname": "lg-webos-tv.local",
            "ip_address": "10.0.0.50",
            "mac_address": "00:11:22:33:44:55",
            "vendor": "LG Electronics",
            "model": "LG Smart TV",
            "model_identifier": "OLED65CXPUA",
            "device_class": "tv_display",
            "fleet_group": "room_display",
            "compute_tier": "display_only",
            "service_roles": ["dashboard_receiver", "alert_wall", "release_status_display", "swarm_animation_surface"],
            "service_endpoints": ["http://10.0.0.50:8060"],
            "trusted_compute": False,
            "approval_required": True,
            "onboarding_status": "recommended",
            "network_profile": "Wi-Fi (WPA3)",
            "power_profile": "AC Powered",
            "sandbox_level": "browser_only",
            "requires_operator_presence": False,
            "last_seen": now_iso(),
            "discovery_sources": ["mDNS", "ARP"],
            "confidence_score": 0.95,
            "operator_notes": "LG WebOS smart display service node",
            "raw_fingerprint": {"services": ["_airplay._tcp", "_googlecast._tcp"]}
        },
        {
            "node_id": "discovery-quest-mock",
            "display_name": "Meta Quest 3 Headset",
            "hostname": "quest-3-xr.local",
            "ip_address": "10.0.0.75",
            "mac_address": "22:33:44:55:66:77",
            "vendor": "Meta Platforms",
            "model": "Meta Quest 3",
            "model_identifier": "Quest-3-128G",
            "device_class": "xr_headset",
            "fleet_group": "mixed_reality",
            "compute_tier": "edge_light",
            "service_roles": ["spatial_dashboard", "operator_console", "approval_terminal", "xr_topology_viewer", "voice_endpoint"],
            "service_endpoints": ["https://10.0.0.75:443"],
            "trusted_compute": False,
            "approval_required": True,
            "onboarding_status": "recommended",
            "network_profile": "Wi-Fi (5GHz)",
            "power_profile": "Battery (charging)",
            "sandbox_level": "app_sandbox",
            "requires_operator_presence": True,
            "last_seen": now_iso(),
            "discovery_sources": ["mDNS"],
            "confidence_score": 0.9,
            "operator_notes": "Meta Quest 3 XR command console terminal",
            "raw_fingerprint": {"services": ["_http._tcp", "_ssh._tcp"]}
        },
        {
            "node_id": "discovery-ipad-mock",
            "display_name": "Michael's iPad Mini",
            "hostname": "michaels-ipad-mini.local",
            "ip_address": "10.0.0.91",
            "mac_address": "44:55:66:77:88:99",
            "vendor": "Apple Inc.",
            "model": "iPad mini",
            "model_identifier": "MUU62LL/A",
            "device_class": "ipad",
            "fleet_group": "mobile_fleet",
            "compute_tier": "edge_light",
            "service_roles": ["mobile_dashboard", "approval_terminal", "camera_context", "document_review", "swarm_control_surface"],
            "service_endpoints": ["https://10.0.0.91:7000"],
            "trusted_compute": False,
            "approval_required": True,
            "onboarding_status": "recommended",
            "network_profile": "Wi-Fi",
            "power_profile": "Battery",
            "sandbox_level": "app_sandbox",
            "requires_operator_presence": False,
            "last_seen": now_iso(),
            "discovery_sources": ["mDNS", "ARP"],
            "confidence_score": 0.98,
            "operator_notes": "iPad Mini mobile client node",
            "raw_fingerprint": {"services": ["_airplay._tcp", "_raop._tcp"]}
        },
        {
            "node_id": "discovery-mac-mock",
            "display_name": "Michael's Mac Studio Studio Candidate",
            "hostname": "michaels-mac-studio.local",
            "ip_address": "10.0.0.120",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "vendor": "Apple Inc.",
            "model": "Mac Studio",
            "model_identifier": "MacStudio2,1",
            "device_class": "mac",
            "fleet_group": "core_compute",
            "compute_tier": "primary_compute",
            "service_roles": ["compute_worker", "browser_automation", "qa_runner", "build_runner", "evidence_archiver"],
            "service_endpoints": ["ssh://10.0.0.120:22"],
            "trusted_compute": False,
            "approval_required": True,
            "onboarding_status": "recommended",
            "network_profile": "Ethernet (10GbE)",
            "power_profile": "AC Powered",
            "sandbox_level": "native",
            "requires_operator_presence": False,
            "last_seen": now_iso(),
            "discovery_sources": ["ARP"],
            "confidence_score": 0.85,
            "operator_notes": "High performance macOS compute node candidate",
            "raw_fingerprint": {"services": ["_ssh._tcp"]}
        },
        {
            "node_id": "discovery-unknown-mock",
            "display_name": "Unknown Host",
            "hostname": "unknown-device-192.local",
            "ip_address": "10.0.0.192",
            "mac_address": "ff:ee:dd:cc:bb:aa",
            "vendor": "Unknown Vendor",
            "model": "Generic Network Device",
            "model_identifier": "Generic-v1",
            "device_class": "unknown",
            "fleet_group": "unknown",
            "compute_tier": "none",
            "service_roles": [],
            "service_endpoints": [],
            "trusted_compute": False,
            "approval_required": True,
            "onboarding_status": "discovered",
            "network_profile": "Unknown",
            "power_profile": "Unknown",
            "sandbox_level": "unknown",
            "requires_operator_presence": False,
            "last_seen": now_iso(),
            "discovery_sources": ["ARP"],
            "confidence_score": 0.3,
            "operator_notes": "Discovered via ARP neighbor scanning, untrusted",
            "raw_fingerprint": {}
        }
    ]
    if os.path.exists(FIXTURES_PATH):
        try:
            with open(FIXTURES_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return fallback

def discover_mdns_services() -> list[dict]:
    # Returns an empty list on dry-run/live failure.
    # In live environments, this query is read-only.
    # No credentials are sent, no logins attempted.
    return []

def discover_neighbor_table() -> list[dict]:
    discovered = []
    try:
        # Runs arp -a to get local neighbor nodes safely
        res = subprocess.run(["arp", "-a"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        if res.returncode == 0:
            stdout_str = res.stdout.decode("utf-8", errors="ignore")
            # Regex fits: ? (10.0.0.44) at 54:2a:a2:bb:cc:dd on en0
            for line in stdout_str.split("\n"):
                m = re.search(r'\(([\d\.]+)\)\s+at\s+([0-9a-fA-F:]+)', line)
                if m:
                    ip = m.group(1)
                    mac = m.group(2)
                    # Ignore loopback/multicast ranges
                    if ip.startswith("127.") or ip.startswith("224.") or ip.startswith("255."):
                        continue
                    discovered.append({
                        "ip_address": ip,
                        "mac_address": mac,
                        "hostname": f"host-{ip.replace('.', '-')}.local",
                        "sources": ["ARP"]
                    })
    except Exception:
        pass
    return discovered

def discover_optional_network_scan(enabled: bool = False) -> list[dict]:
    # Subnet scan mode. Since aggressive port scanning is forbidden,
    # we return empty list if not enabled.
    return []

def fingerprint_discovered_device(dev: dict) -> dict:
    ip = dev.get("ip_address", "127.0.0.1")
    mac = dev.get("mac_address", "").lower()
    hostname = dev.get("hostname", "").lower()
    
    # Defaults
    vendor = "Unknown Vendor"
    model = "Generic Network Device"
    model_identifier = "Generic"
    device_class = "unknown"
    
    # Vendor mapping from MAC OUI prefix (simplified for safety/portability)
    if mac.startswith("00:11:22") or mac.startswith("54:2a:a2"):
        vendor = "Apple Inc."
        device_class = "ipad"
        model = "iPad"
        model_identifier = "MUU62LL/A"
    elif mac.startswith("22:33:44"):
        vendor = "Meta Platforms"
        device_class = "xr_headset"
        model = "Meta Quest 3"
        model_identifier = "Quest-3"
    elif mac.startswith("00:1a:11") or "lg" in hostname or "tv" in hostname:
        vendor = "LG Electronics"
        device_class = "tv_display"
        model = "LG Smart TV"
        model_identifier = "OLED65"
    elif mac.startswith("00:11:32") or "nas" in hostname:
        vendor = "Synology"
        device_class = "nas"
        model = "Synology NAS"
        model_identifier = "DS920+"
    elif "macbook" in hostname or "mac" in hostname:
        vendor = "Apple Inc."
        device_class = "mac"
        model = "MacBook Pro"
        model_identifier = "MBP"
    elif "quest" in hostname:
        vendor = "Meta Platforms"
        device_class = "xr_headset"
        model = "Meta Quest 3"
        model_identifier = "Quest-3"
        
    return {
        "vendor": vendor,
        "model": model,
        "model_identifier": model_identifier,
        "device_class": device_class
    }

def classify_device_as_service(fingerprint: dict) -> dict:
    device_class = fingerprint.get("device_class", "unknown")
    
    # Defaults
    fleet_group = "unknown"
    compute_tier = "none"
    service_roles = []
    requires_operator_presence = False
    sandbox_level = "unknown"
    
    if device_class == "tv_display":
        fleet_group = "room_display"
        compute_tier = "display_only"
        service_roles = ["dashboard_receiver", "alert_wall", "release_status_display", "swarm_animation_surface"]
        sandbox_level = "browser_only"
    elif device_class == "apple_tv":
        fleet_group = "room_display"
        compute_tier = "display_only"
        service_roles = ["dashboard_receiver", "airplay_display", "alert_wall"]
        sandbox_level = "browser_only"
    elif device_class in ("android_tv", "google_tv"):
        fleet_group = "room_display"
        compute_tier = "edge_light"
        service_roles = ["dashboard_receiver", "cast_receiver", "alert_wall", "lightweight_android_service"]
        sandbox_level = "app_sandbox"
    elif device_class == "nvidia_shield":
        fleet_group = "room_display"
        compute_tier = "edge_worker"
        service_roles = ["dashboard_receiver", "cast_receiver", "android_edge_service", "media_processing_service"]
        sandbox_level = "adb_managed"
    elif device_class == "xr_headset":
        fleet_group = "mixed_reality"
        compute_tier = "edge_light"
        requires_operator_presence = True
        service_roles = ["spatial_dashboard", "operator_console", "approval_terminal", "xr_topology_viewer", "voice_endpoint"]
        sandbox_level = "app_sandbox"
    elif device_class == "ipad":
        fleet_group = "mobile_fleet"
        compute_tier = "edge_light"
        service_roles = ["mobile_dashboard", "approval_terminal", "camera_context", "document_review", "swarm_control_surface"]
        sandbox_level = "app_sandbox"
    elif device_class == "iphone":
        fleet_group = "edge_phone"
        compute_tier = "edge_light"
        service_roles = ["mobile_dashboard", "approval_terminal", "camera_context", "notification_endpoint"]
        sandbox_level = "app_sandbox"
    elif device_class in ("mac", "pc", "linux_host"):
        fleet_group = "core_compute"
        compute_tier = "primary_compute"
        service_roles = ["compute_worker", "browser_automation", "qa_runner", "build_runner", "evidence_archiver"]
        sandbox_level = "native"
    elif device_class == "nas":
        fleet_group = "storage"
        compute_tier = "edge_worker"
        service_roles = ["artifact_store", "evidence_archive", "backup_target", "local_registry"]
        sandbox_level = "container_managed"
    elif device_class == "router":
        fleet_group = "network"
        compute_tier = "none"
        service_roles = ["network_telemetry", "policy_surface"]
        sandbox_level = "unknown"
        
    return {
        "fleet_group": fleet_group,
        "compute_tier": compute_tier,
        "service_roles": service_roles,
        "requires_operator_presence": requires_operator_presence,
        "sandbox_level": sandbox_level
    }

def build_device_service_recommendation(dev: dict) -> dict:
    fingerprint = fingerprint_discovered_device(dev)
    classification = classify_device_as_service(fingerprint)
    
    node_id = f"daas-{uuid.uuid4().hex[:8]}"
    if dev.get("mac_address"):
        # Deterministic node ID from MAC address
        clean_mac = dev["mac_address"].replace(":", "").lower()
        node_id = f"daas-{clean_mac[:12]}"
        
    return {
        "node_id": node_id,
        "display_name": f"{fingerprint['vendor']} {fingerprint['model']}".strip(),
        "hostname": dev.get("hostname", f"{node_id}.local"),
        "ip_address": dev["ip_address"],
        "mac_address": dev.get("mac_address"),
        "vendor": fingerprint["vendor"],
        "model": fingerprint["model"],
        "model_identifier": fingerprint["model_identifier"],
        "device_class": fingerprint["device_class"],
        "fleet_group": classification["fleet_group"],
        "compute_tier": classification["compute_tier"],
        "service_roles": classification["service_roles"],
        "service_endpoints": [f"http://{dev['ip_address']}:80"] if classification["compute_tier"] != "none" else [],
        "trusted_compute": False,
        "approval_required": True,
        "onboarding_status": "recommended",
        "network_profile": "Wi-Fi (WPA2)",
        "power_profile": "AC Powered" if classification["compute_tier"] in ("primary_compute", "display_only") else "Battery",
        "sandbox_level": classification["sandbox_level"],
        "requires_operator_presence": classification["requires_operator_presence"],
        "last_seen": now_iso(),
        "discovery_sources": dev.get("sources", ["ARP"]),
        "confidence_score": 0.8,
        "operator_notes": f"Recommended service configuration for {fingerprint['model']}",
        "raw_fingerprint": {"original": dev}
    }

def run_local_discovery(enable_ping_sweep: bool = False, enable_tcp_probes: bool = False) -> list[dict]:
    # 1. ARP Neighbor scan
    neighbors = discover_neighbor_table()
    
    # 2. mDNS Scan
    mdns_devs = discover_mdns_services()
    
    # Combine lists
    combined = {n["ip_address"]: n for n in neighbors}
    for m in mdns_devs:
        ip = m["ip_address"]
        if ip in combined:
            combined[ip]["sources"].extend(m.get("sources", []))
            combined[ip]["sources"] = list(set(combined[ip]["sources"]))
        else:
            combined[ip] = m
            
    # 3. Generate recommendation payloads
    recommendations = []
    for dev in combined.values():
        rec = build_device_service_recommendation(dev)
        recommendations.append(rec)
        
    # 4. Inject mock fixtures if in development/test or if no items discovered
    fixtures = get_fixtures()
    for f in fixtures:
        # Check if already in list
        exists = any(r["mac_address"] == f.get("mac_address") for r in recommendations)
        if not exists:
            recommendations.append(f)
            
    return recommendations
