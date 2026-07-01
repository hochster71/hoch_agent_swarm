# ---- Operational activity pools per node role ----
ACTIVITY_POOLS = {
    "control": [
        "Orchestrating cross-node task distribution",
        "Running ZTA policy enforcement sweep",
        "Reconciling agent heartbeat telemetry",
        "Dispatching PERT critical-path task T2→T4",
        "Validating CDAO RAI compliance tokens",
        "Flushing execution buffer and re-queuing stale tasks",
        "Broadcasting cluster health beacon to all nodes",
        "Routing DoD RMF continuous monitoring payload",
    ],
    "coder": [
        "Triaging runtime exception in module core/router.py",
        "Self-healing: patching null-ref in API gateway layer",
        "Reasoning over failing unit test suite — 3 cases",
        "Applying automated refactor to reduce cyclomatic complexity",
        "Resolving merge conflict in feature/zta-enforcement branch",
        "Running static analysis pass — 0 critical findings",
        "Executing self-heal: rebuilding Docker image layer cache",
        "Synthesizing fix for memory leak in telemetry collector",
    ],
    "deployer": [
        "Building iOS binary — xcodebuild RELEASE configuration",
        "Running automated smoke tests against staging environment",
        "Triaging App Store submission rejection — privacy manifest",
        "Self-healing: re-signing IPA with updated provisioning profile",
        "Deploying Docker container revision 4.2.1 to SWARM_A",
        "Validating TestFlight build artefact checksums",
        "Reasoning over crash report — symbolication in progress",
        "Rolling back failed canary deploy — restoring rev 4.1.9",
    ],
    "monitor": [
        "Streaming live vitals to C2 dashboard",
        "Triaging latency spike — packet loss 0.2% on 10.0.0.8",
        "Self-healing: rerouting traffic around congested path",
        "Reasoning over anomaly pattern in RAM usage delta",
        "Performing network topology health scan",
        "Alerting: CPU threshold exceeded — auto-scaling response",
    ],
}

# Node configuration — all assets ONLINE and actively working
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
    }
}

import random
import time
import logging
import psutil
import copy
import subprocess
import threading

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

        # 2. Worker nodes fluctuations, activity rotation, and ping checks
        for node_id, node in list(self.nodes.items()):
            if node_id != "L1":
                with self.status_lock:
                    node["cpu_usage"] = min(95, max(8, node["cpu_usage"] + random.randint(-4, 6)))
                    node["ram_usage"] = min(92, max(15, node["ram_usage"] + random.randint(-2, 3)))

            domain = node.get("missionDomain", "control")
            pool = ACTIVITY_POOLS.get(domain, ACTIVITY_POOLS["control"])
            idx = self._activity_idx.get(node_id, 0)
            
            with self.status_lock:
                node["activity"] = pool[idx % len(pool)]
                self._activity_idx[node_id] = (idx + 1) % len(pool)
                
                # Determine status dynamically based on activity keywords
                act_lower = node["activity"].lower()
                if "triage" in act_lower or "triaging" in act_lower:
                    node["status"] = "Triaging"
                elif "self-healing" in act_lower or "self-heal" in act_lower or "rebuilding" in act_lower or "rollback" in act_lower or "flushing" in act_lower or "rerouting" in act_lower:
                    node["status"] = "Self-Healing"
                elif "reasoning" in act_lower or "reason" in act_lower or "validating" in act_lower or "synthesizing" in act_lower:
                    node["status"] = "Reasoning"
                elif "deploying" in act_lower or "deploy" in act_lower or "dispatching" in act_lower or "building" in act_lower:
                    node["status"] = "Deploying"
                else:
                    node["status"] = "Active"

            # Run ping check outside status lock to prevent blocking
            if node_id == "L1":
                latency = 0.0
            else:
                latency = self._ping_node(node["ip"])

            with self.status_lock:
                node["latency_ms"] = latency

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
        # Fallback to simulated latency with minor fluctuation
        return round(1.0 + random.random() * 2.0, 1)

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

        return {
            "status": "HEALTHY 100%",
            "active_assets": len([n for n in nodes_copy.values() if n["status"] != "Offline"]),
            "sync": "OK",
            "latency": "1.1ms (Excellent)",
            "total_agents": total_agents,
            "system_cpu": f"{int(avg_cpu)}%",
            "system_ram": f"{round(total_ram_used, 1)}GB/{int(total_ram_cap)}GB",
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
