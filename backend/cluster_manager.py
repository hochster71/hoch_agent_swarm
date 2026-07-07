# LIVE-REAL-ONLY (2026-07-07): the ACTIVITY_POOLS dict of canned activity strings
# ("Reasoning over failing unit test suite", "Streaming live vitals to C2 dashboard",
# "Building iOS binary…") was DELETED. It was dead code (never referenced) but was the
# origin of the fabricated fleet "activity" theater. Non-measured nodes now report only
# what is true: reachability + "no telemetry agent on node". A node's activity is real
# only where telemetry_authority == MEASURED_LOCAL.

# Node roster — identity/config only. cpu/ram/agents/activity for non-L1 nodes are
# DECLARED roster values, not measurements, and are labeled as such at runtime.
NODES_CONFIG = {
    "L1": {
        "id": "L1",
        "fleet_group": "core_compute",
        "name": "MBP MS PRO (CONTROL PLANE)",
        "ip": "10.0.0.6",
        "role": "CONTROL PLANE / KERNEL HUB",
        "specs": "24GB RAM, 1TB SSD",
        "status": "Active",
        "activity": "Orchestrating cross-node task distribution",
        "missionDomain": "control",
        "total_agents": 10,
        "os": "macOS",
        "cpu_usage": 45,
        "ram_usage": 60,
        "latency_ms": 1.2,
        "agents": [
            {
                "name": "KernelHub-Mgr",
                "type": "System Orchestrator",
                "status": "Active",
                "description": "Global task scheduling and communication manager. Currently routing PERT critical-path tasks T1→T2→T4 and enforcing DoD ZTA session policies across all enclaves."
            },
            {
                "name": "TaskScheduler-01",
                "type": "Routing Engine",
                "status": "Active",
                "description": "Assigns incoming prompts to optimal nodes based on real-time CPU/RAM load. Triaging queue depth spike — redistributing 3 overdue tasks to L3 and W1."
            },
            {
                "name": "Auditor-Proxy",
                "type": "Observability",
                "status": "Active",
                "description": "Tracks agent costs, token counts, and output validations. Self-healing: flagged and corrected 2 stale audit entries in ConMon log. CDAO RAI traceability score: 98/100."
            },
            {
                "name": "ConMon-Sentinel",
                "type": "Continuous Monitoring",
                "status": "Active",
                "description": "NIST SP 800-53 SI-4 / AU-6 real-time monitoring agent. Streaming telemetry from all nodes into the RMF ConMon pipeline. Last anomaly resolved 4m ago."
            }
        ]
    },
    "L2": {
        "id": "L2",
        "fleet_group": "core_compute",
        "name": "MICHAEL'S IMAC",
        "ip": "10.0.0.92",
        "role": "Coder Node — Refactor & Analysis",
        "specs": "M3, 8GB RAM, 512GB SSD",
        "status": "Triaging",
        "activity": "Triaging runtime exception in module core/router.py",
        "missionDomain": "coder",
        "total_agents": 4,
        "os": "macOS",
        "cpu_usage": 58,
        "ram_usage": 63,
        "latency_ms": 1.5,
        "agents": [
            {
                "name": "Gordy-iMac-01",
                "type": "Docker Coder (GORDY)",
                "status": "Triaging",
                "description": "Active triage pass on core/router.py — null pointer exception on line 247. Reasoning over 3 candidate root causes. Self-healing patch in progress."
            },
            {
                "name": "Parser-02",
                "type": "Data Extraction",
                "status": "Self-Healing",
                "description": "Parsed 1,842 lines of unstructured repository content. Detected and auto-repaired 4 malformed JSON config entries. Feeding clean artefacts back to KernelHub-Mgr."
            },
            {
                "name": "Refactor-Agent-01",
                "type": "Code Quality",
                "status": "Active",
                "description": "Running automated refactor sweep — reducing cyclomatic complexity from 18 → 6 in auth_middleware.py. Applying SOLID principles and generating diff for operator review."
            }
        ]
    },
    "L3": {
        "id": "L3",
        "fleet_group": "core_compute",
        "name": "HOCH-MESH MACBOOK NEO",
        "ip": "10.0.0.8",
        "role": "Coder Node — Deploy & Self-Heal Engine",
        "specs": "M3, 8GB RAM, 512GB SSD",
        "status": "Self-Healing",
        "activity": "Self-healing: rebuilding Docker image layer cache",
        "missionDomain": "deployer",
        "total_agents": 5,
        "os": "macOS",
        "cpu_usage": 74,
        "ram_usage": 68,
        "latency_ms": 1.1,
        "agents": [
            {
                "name": "Gordy-Neo-01",
                "type": "Docker Coder (GORDY)",
                "status": "Active",
                "description": "Engineering self-healing routines for API gateway layer. Synthesized fix for memory leak in telemetry collector — patch validated, deploying to staging. CPU load elevated due to parallel build pipeline."
            },
            {
                "name": "Deploy-Deployer",
                "type": "Docker Deployment",
                "status": "Deploying",
                "description": "Building iOS binary in RELEASE configuration. Triaging App Store rejection — regenerating privacy manifest and re-signing IPA. ETA to TestFlight: ~8 min."
            },
            {
                "name": "Gordy-App-Deployer",
                "type": "App Store Deployer (GORDY)",
                "status": "Active",
                "description": "Validating artefact checksums for build rev 4.2.1. Reasoning over crash symbolication report — identified off-by-one in UICollectionView delegate. Automated PR raised for operator approval."
            },
            {
                "name": "SelfHeal-Watchdog",
                "type": "Self-Heal Monitor",
                "status": "Self-Healing",
                "description": "Continuously monitors L3 container health. Detected and resolved stale lock file in /tmp — rebuilt Docker image layer cache. Zero downtime achieved. Next scan in 90s."
            }
        ]
    },
    "W1": {
        "id": "W1",
        "fleet_group": "core_compute",
        "name": "DELL 9440",
        "ip": "10.0.0.207",
        "role": "Coder Node — Heavy Compute & Reasoning",
        "specs": "i9-13900H, 32GB RAM, 1TB SSD",
        "status": "Reasoning",
        "activity": "Reasoning over failing unit test suite — 3 cases",
        "missionDomain": "coder",
        "total_agents": 12,
        "os": "Windows 11",
        "cpu_usage": 82,
        "ram_usage": 78,
        "latency_ms": 1.8,
        "agents": [
            {
                "name": "Gordy-Dell-01",
                "type": "Docker Coder (GORDY)",
                "status": "Reasoning",
                "description": "Deep reasoning pass over 3 failing unit test cases in the PERT critical path calculation suite. Generated 5 hypotheses, narrowed to root cause: float precision rounding in backward pass. Fix authored and staged."
            },
            {
                "name": "Gordy-Dell-02",
                "type": "Docker Coder (GORDY)",
                "status": "Active",
                "description": "Multi-threaded build pipeline: parallel syntax check across 148 modified files. 0 critical errors. Resolved 7 lint warnings via automated fix. Build artefact compressed and sent to L3 deployer."
            },
            {
                "name": "Optimizer-01",
                "type": "Performance Optimization",
                "status": "Active",
                "description": "Profiling execution latency across the cluster — identified 340ms bottleneck in WebSocket broadcast loop. Self-healing: injected async message queue to resolve. Latency reduced to 12ms."
            },
            {
                "name": "SecurityScan-W1",
                "type": "Security Scanner",
                "status": "Active",
                "description": "Running SAST scan on latest code delta — 0 HIGH findings, 2 MEDIUM flagged for operator review. Cross-referencing against NVD CVE database for dependency vulnerabilities."
            }
        ]
    },
    "IPAD": {
        "id": "IPAD",
        "fleet_group": "mobile_fleet",
        "name": "IPAD PRO 12\"",
        "ip": "10.0.0.120",
        "role": "C2 Monitor / Lightweight Triage Client",
        "specs": "M2, 8GB RAM",
        "status": "Active",
        "activity": "Streaming live vitals to C2 dashboard",
        "missionDomain": "monitor",
        "total_agents": 3,
        "os": "iPadOS",
        "cpu_usage": 28,
        "ram_usage": 38,
        "latency_ms": 2.4,
        "agents": [
            {
                "name": "UI-Client-Pad",
                "type": "C2 Monitor Agent",
                "status": "Active",
                "description": "Rendering live diagnostic stream and operator alerting overlay. Triaging latency anomaly reported at 10.0.0.8 — rerouting traffic through alternate mesh path. Dashboard refresh rate: 1s."
            },
            {
                "name": "AlertBroker-Pad",
                "type": "Notification Engine",
                "status": "Active",
                "description": "Broadcasting swarm health alerts to all operator surfaces. Processed 14 events in the last 5 minutes. 1 WARN escalated to operator — self-heal response triggered on L3."
            }
        ]
    },
    "IPHONE": {
        "id": "IPHONE",
        "fleet_group": "edge_phone",
        "name": "IPHONE 15 PRO MAX",
        "ip": "10.0.0.74",
        "role": "Mobile Sentinel / Push Alert Gateway",
        "specs": "A17 Pro, 8GB RAM",
        "status": "Active",
        "activity": "Performing network topology health scan",
        "missionDomain": "monitor",
        "total_agents": 3,
        "os": "iOS",
        "cpu_usage": 22,
        "ram_usage": 32,
        "latency_ms": 3.1,
        "agents": [
            {
                "name": "UI-Client-Phone",
                "type": "Mobile Sentinel",
                "status": "Active",
                "description": "Vitals notifier and mobile C2 observer. Monitoring all 6 node heartbeats. Sent push alert at 08:17 — L3 self-heal triggered. Scanning network topology: all paths HEALTHY."
            },
            {
                "name": "PushRelay-01",
                "type": "Push Gateway",
                "status": "Active",
                "description": "APNs relay agent for critical cluster events. Processed 6 push notifications in the current session. Zero delivery failures. Encrypted TLS 1.3 channel to control plane verified."
            }
        ]
    },
    "IPAD_PRO_11": {
        "id": "IPAD_PRO_11",
        "fleet_group": "mobile_fleet",
        "name": "Michael's iPad pro 11-inch MTXQ2LL/A",
        "ip": "10.0.0.44",
        "role": "Edge Client / Mobile Node",
        "specs": "Apple M4, 8GB RAM",
        "status": "Active",
        "activity": "Streaming live vitals to C2 dashboard",
        "missionDomain": "monitor",
        "total_agents": 2,
        "os": "iPadOS",
        "cpu_usage": 15,
        "ram_usage": 25,
        "latency_ms": 3.8,
        "agents": [
            {
                "name": "UI-Client-iPad-Pro-11",
                "type": "C2 Monitor Agent",
                "status": "Active",
                "description": "Active C2 session telemetry streaming on Apple Silicon iPad."
            }
        ]
    },
    "IPAD_MINI_1": {
        "id": "IPAD_MINI_1",
        "fleet_group": "mobile_fleet",
        "name": "iPad mini MUU62LL/A",
        "ip": "10.0.0.91",
        "role": "Edge Client / Mobile Node",
        "specs": "A12 Bionic, 3GB RAM",
        "status": "Active",
        "activity": "Streaming live vitals to C2 dashboard",
        "missionDomain": "monitor",
        "total_agents": 2,
        "os": "iPadOS",
        "cpu_usage": 18,
        "ram_usage": 35,
        "latency_ms": 4.1,
        "agents": [
            {
                "name": "UI-Client-iPad-Mini-1",
                "type": "C2 Monitor Agent",
                "status": "Active",
                "description": "Edge interface active on iPad mini (gen 5)."
            }
        ]
    },
    "IPAD_MINI_2": {
        "id": "IPAD_MINI_2",
        "fleet_group": "mobile_fleet",
        "name": "iPad mini MGNV2LL/A",
        "ip": "10.0.0.137",
        "role": "Edge Client / Mobile Node",
        "specs": "A7, 1GB RAM",
        "status": "Active",
        "activity": "Streaming live vitals to C2 dashboard",
        "missionDomain": "monitor",
        "total_agents": 2,
        "os": "iPadOS",
        "cpu_usage": 22,
        "ram_usage": 45,
        "latency_ms": 5.5,
        "agents": [
            {
                "name": "UI-Client-iPad-Mini-2",
                "type": "C2 Monitor Agent",
                "status": "Active",
                "description": "Edge interface active on legacy iPad mini 3."
            }
        ]
    },
    "RELAY": {
        "id": "RELAY",
        "fleet_group": "always_on_backstop",
        "name": "hoch-relay-001 (HOCH-200)",
        "ip": "100.87.18.15",
        "role": "relay / always-on 24-7 backstop",
        "specs": "VPS (Linode)",
        "status": "Active",
        "activity": "Relay API + burn-in daemon + local inference (measured on host)",
        "total_agents": 0,
        "os": "Ubuntu 24.04",
        "cpu_usage": 0,
        "ram_usage": 0,
        "latency_ms": 0.0,
        "telemetry_authority": "MEASURED_REMOTE",
        "agents": []
    }
}

import json
import random
import time
import logging
import psutil
import copy
import subprocess
import threading
import urllib.request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ClusterManager")

class ClusterManager:
    def __init__(self):
        # Deep-copy so random mutations don't corrupt the module-level config
        self.nodes = copy.deepcopy(NODES_CONFIG)
        self._activity_idx = {nid: 0 for nid in self.nodes}
        self.status_lock = threading.Lock()
        
        # Load approved service nodes from sqlite registry
        self.load_approved_service_nodes()
        
        # Start background telemetry loop to run pings and host checks asynchronously
        self.bg_thread = threading.Thread(target=self._bg_telemetry_loop, daemon=True)
        self.bg_thread.start()

    def load_approved_service_nodes(self):
        try:
            from backend.runtime_execution_store import list_service_nodes
            approved = list_service_nodes()
            with self.status_lock:
                self.nodes = copy.deepcopy(NODES_CONFIG)
                self._activity_idx = {nid: 0 for nid in self.nodes}
                for node in approved:
                    nid = node["node_id"]
                    # Extract IP address from list if stored as dict or string
                    ip_addr = node.get("ip_address", "127.0.0.1")
                    self.nodes[nid] = {
                        "id": nid,
                        "fleet_group": node.get("fleet_group", "unknown"),
                        "name": node.get("display_name", "Service Node"),
                        "ip": ip_addr,
                        "role": f"{node.get('compute_tier', 'none').upper()} | Roles: {', '.join(node.get('service_roles', []))}",
                        "specs": f"Class: {node.get('device_class')}, Tier: {node.get('compute_tier')}",
                        "status": "Active",
                        "total_agents": 0,
                        "os": node.get("device_class", "unknown"),
                        "cpu_usage": 15,
                        "ram_usage": 25,
                        "latency_ms": 1.5,
                        "agents": []
                    }
        except Exception as e:
            logger.error(f"Failed to load approved service nodes from registry: {e}")

    def _bg_telemetry_loop(self):
        # Perform initial telemetry scan, then update telemetry continuously
        while True:
            try:
                self._update_telemetry_data()
                self._ingest_relay_node()  # pull MEASURED vitals from the always-on relay
            except Exception as e:
                logger.error(f"Error in background telemetry loop: {e}")
            time.sleep(3.0)

    def _update_telemetry_data(self):
        # 1. Host vitals (Control Plane L1) via psutil
        try:
            cpu_percent = psutil.cpu_percent()
            virtual_mem = psutil.virtual_memory()
            ram_percent = virtual_mem.percent
            ram_total_gb = round(virtual_mem.total / (1024 ** 3), 1)
            with self.status_lock:
                self.nodes["L1"]["cpu_usage"] = int(cpu_percent)
                self.nodes["L1"]["ram_usage"] = int(ram_percent)
                self.nodes["L1"]["specs"] = f"{ram_total_gb}GB RAM, Disk: {psutil.disk_usage('/').percent}% used"
        except Exception as e:
            logger.warning(f"Failed to query psutil host vitals: {e}")

        # 2. Ping checks + honest per-node state.
        # LIVE-REAL-ONLY (2026-07-06): removed (a) random-walk CPU/RAM "fluctuations" that
        # made fabricated vitals wobble to look alive, and (b) the rotating pool of canned
        # activity strings ("Triaging latency spike...") that drove fictional statuses like
        # Self-Healing/Reasoning. Remote nodes report only what is measured: reachability.
        for node_id, node in list(self.nodes.items()):
            if node_id not in ("L1", "RELAY"):
                with self.status_lock:
                    node["activity"] = "(unmeasured — no telemetry agent on node)"
                    node["status"] = "Reachable"
                    # LIVE-REAL-ONLY (2026-07-07): scrub fabricated per-agent
                    # descriptions ("Reasoning over 3 candidate root causes",
                    # "Building iOS binary…") on non-measured nodes. Without a
                    # telemetry agent reporting real work, these are declared
                    # roster fiction, not measurements.
                    for _agent in node.get("agents", []):
                        _agent["status"] = "DECLARED"
                        _agent["description"] = (
                            "DECLARED roster entry — no telemetry agent on this node; "
                            "not a live measurement."
                        )
            else:
                with self.status_lock:
                    node["activity"] = "Control plane: API + cadence + BRAIN loops (this host)"

            # Run ping check outside status lock to prevent blocking
            if node_id == "L1":
                latency = 0.0
            else:
                latency = self._ping_node(node["ip"])

            with self.status_lock:
                node["latency_ms"] = latency
                if latency < 0:
                    # Honest fleet state: no ping response overrides any scripted activity status.
                    node["status"] = "Unreachable"
                    node["telemetry_authority"] = "UNREACHABLE"
                elif node_id == "L1":
                    # LIVE-REAL-ONLY (2026-07-06): the control-plane node reports REAL local
                    # telemetry (psutil), replacing the hardcoded roster figures.
                    try:
                        node["cpu_usage"] = int(psutil.cpu_percent(interval=None))
                        node["ram_usage"] = int(psutil.virtual_memory().percent)
                        # MEASURED agents: enumerate launchd-managed com.hoch.* jobs with a
                        # live PID right now. LIVE-REAL-ONLY (2026-07-07): this REPLACES the
                        # hardcoded roster of 4 fabricated agents (KernelHub-Mgr et al. with
                        # invented "Self-healing…" narratives). Clear the list first so a
                        # launchctl failure yields an honest empty list, never fiction.
                        node["agents"] = []
                        try:
                            out = subprocess.run(["launchctl", "list"], capture_output=True,
                                                 text=True, timeout=5).stdout
                            measured = []
                            for line in out.splitlines():
                                parts = line.split("\t")
                                if len(parts) >= 3 and "com.hoch" in parts[2] and parts[0].strip().isdigit():
                                    measured.append({
                                        "name": parts[2].strip(),
                                        "type": "launchd job",
                                        "status": "Active",
                                        "description": f"launchd-managed process (PID {parts[0].strip()}) — measured live.",
                                    })
                            node["agents"] = measured
                            node["total_agents"] = len(measured)
                            node["telemetry_authority"] = "MEASURED_LOCAL"
                        except Exception:
                            # Could not enumerate launchd — report unknown, not fiction.
                            node["total_agents"] = 0
                            node["telemetry_authority"] = "DECLARED_ROSTER_NOT_MEASURED"
                    except Exception:
                        node["telemetry_authority"] = "DECLARED_ROSTER_NOT_MEASURED"
                else:
                    # Reachable but unmeasured: cpu/ram/agents/activity are DECLARED roster
                    # values, not measurements. Only latency_ms is real (ICMP).
                    node["telemetry_authority"] = "DECLARED_ROSTER_NOT_MEASURED"

    def _ingest_relay_node(self):
        """Pull MEASURED telemetry from the always-on HOCH-200 relay over Tailscale and
        represent it as a real fleet node. LIVE-REAL-ONLY (2026-07-07): this replaces
        the iPad 'streaming live vitals' theater with the one remote node that actually
        reports measured vitals + agent counts. Fails closed to UNREACHABLE."""
        url = "http://100.87.18.15:3012/api/fleet/node"
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                p = json.loads(r.read().decode())
            authority = p.get("telemetry_authority", "DECLARED_ROSTER_NOT_MEASURED")
            # Measured on the relay host, fetched remotely → MEASURED_REMOTE from here.
            if authority == "MEASURED_LOCAL":
                authority = "MEASURED_REMOTE"
            node = {
                "id": "RELAY", "fleet_group": "always_on_backstop",
                "name": p.get("display_name", "hoch-relay-001 (HOCH-200)"),
                "ip": "100.87.18.15",
                "role": p.get("role", "relay / always-on 24-7 backstop"),
                "specs": "VPS (Linode) · Ubuntu 24.04",
                "status": p.get("status", "Active"),
                "activity": p.get("activity", "Relay API + burn-in daemon (measured)"),
                "total_agents": p.get("measured_agent_count", 0),
                "os": "Ubuntu 24.04",
                "cpu_usage": p.get("cpu_pct") if p.get("cpu_pct") is not None else 0,
                "ram_usage": p.get("ram_pct") if p.get("ram_pct") is not None else 0,
                "latency_ms": self._ping_node("100.87.18.15"),
                "telemetry_authority": authority,
                "ollama_models": p.get("ollama_models", []),
                "agents": p.get("agents", []),
            }
            with self.status_lock:
                self.nodes["RELAY"] = node
        except Exception as e:
            logger.warning(f"Relay telemetry ingest failed ({e}); marking RELAY UNREACHABLE.")
            with self.status_lock:
                self.nodes["RELAY"] = {
                    "id": "RELAY", "fleet_group": "always_on_backstop",
                    "name": "hoch-relay-001 (HOCH-200)", "ip": "100.87.18.15",
                    "role": "relay / always-on 24-7 backstop", "specs": "VPS (Linode)",
                    "status": "Unreachable", "activity": "(relay telemetry unreachable)",
                    "total_agents": 0, "os": "Ubuntu 24.04",
                    "cpu_usage": 0, "ram_usage": 0, "latency_ms": -1.0,
                    "telemetry_authority": "UNREACHABLE", "agents": [],
                }

    def _ping_node(self, ip: str) -> float:
        """Runs ICMP ping to check actual node latency. Returns ms, or a simulated value if it fails."""
        try:
            # -c 1 = 1 packet, -t 1 = 1 second timeout (macOS/Linux)
            cmd = ["ping", "-c", "1", "-t", "1", ip]
            start_time = time.time()
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            duration_ms = round((time.time() - start_time) * 1000, 1)
            if res.returncode == 0:
                stdout_str = res.stdout.decode("utf-8", errors="ignore")
                for line in stdout_str.split("\n"):
                    if "time=" in line:
                        time_part = line.split("time=")[1].split()[0]
                        return round(float(time_part), 1)
                return duration_ms
        except Exception:
            pass
        # LIVE-REAL-ONLY (2026-07-06): an unreachable node is UNREACHABLE. The previous
        # fallback returned a random 1-3ms latency, making dead machines look excellently
        # online in fleet status. -1.0 = no ICMP response.
        return -1.0

    def get_cluster_status(self):
        with self.status_lock:
            nodes_copy = copy.deepcopy(self.nodes)

        total_agents = 0
        total_cpu = 0
        total_ram_used = 0
        total_ram_cap = 0
        count = 0

        for node_id, node in nodes_copy.items():
            total_agents += node["total_agents"]
            total_cpu += node["cpu_usage"]

            # RAM capacity from specs string
            ram_gb = 8
            if "24GB" in node["specs"]:
                ram_gb = 24
            elif "32GB" in node["specs"]:
                ram_gb = 32
            elif "GB" in node["specs"]:
                try:
                    parts = node["specs"].split("GB")[0].strip().split()[-1]
                    ram_gb = float(parts)
                except (ValueError, IndexError):
                    ram_gb = 8

            total_ram_cap += ram_gb
            total_ram_used += (node["ram_usage"] / 100.0) * ram_gb
            count += 1

        avg_cpu = total_cpu / max(count, 1)

        # LIVE-REAL-ONLY (2026-07-06): summary is COMPUTED, never hardcoded. (Previously
        # returned literal "HEALTHY 100%" and "1.1ms (Excellent)" regardless of state.)
        for n in nodes_copy.values():
            n.setdefault("telemetry_authority", "DECLARED_ROSTER_NOT_MEASURED")
        reachable = [n for n in nodes_copy.values()
                     if n["status"] not in ("Offline", "Unreachable")]
        real_lat = [n["latency_ms"] for n in nodes_copy.values()
                    if isinstance(n.get("latency_ms"), (int, float)) and n["latency_ms"] >= 0]
        n_total = max(count, 1)
        pct = int(100 * len(reachable) / n_total)
        return {
            "status": f"{len(reachable)}/{n_total} REACHABLE ({pct}%)",
            "active_assets": len(reachable),
            "sync": "OK" if len(reachable) == n_total else "DEGRADED",
            "latency": (f"{round(sum(real_lat)/len(real_lat), 1)}ms avg (measured)"
                        if real_lat else "unmeasured"),
            "total_agents": total_agents,
            "system_cpu": f"{int(avg_cpu)}%",
            "system_ram": f"{round(total_ram_used, 1)}GB/{int(total_ram_cap)}GB",
            "telemetry_note": ("cpu/ram/agents are MEASURED only where telemetry_authority="
                               "MEASURED_LOCAL; DECLARED_ROSTER values are configuration, "
                               "not measurements"),
            "nodes": list(nodes_copy.values())
        }

    def add_node(self, node_data: dict):
        node_id = node_data.get("id")
        if not node_id:
            return False
        with self.status_lock:
            # Normalize node structure
            self.nodes[node_id] = {
                "id": node_id,
                "name": node_data.get("name", "Unknown Node"),
                "ip": node_data.get("ip", "10.0.0.1"),
                "role": node_data.get("role", "Worker Node"),
                "specs": node_data.get("specs", "8GB RAM, 512GB SSD"),
                "status": node_data.get("status", "Active"),
                "total_agents": int(node_data.get("total_agents", 0)),
                "os": node_data.get("os", "Linux"),
                "cpu_usage": int(node_data.get("cpu_usage", 10)),
                "ram_usage": int(node_data.get("ram_usage", 20)),
                "latency_ms": float(node_data.get("latency_ms", 1.5)),
                "agents": node_data.get("agents", [])
            }
        logger.info(f"Node '{node_id}' successfully registered in cluster.")
        return True

    def remove_node(self, node_id: str):
        with self.status_lock:
            if node_id in self.nodes:
                # Prevent removing L1 control plane
                if node_id == "L1":
                    return False
                del self.nodes[node_id]
                logger.info(f"Node '{node_id}' successfully removed from cluster.")
                return True
        return False

    def route_task(self, task_type: str, prompt: str, explicit_caps: list[str] = None):
        from backend.capability_router import route_task_by_capabilities
        try:
            return route_task_by_capabilities(task_type, prompt, explicit_caps, self.nodes)
        except Exception as e:
            logger.error(f"Capability routing failed: {e}. Falling back to default L1 routing.")
            return self.nodes.get("L1")
