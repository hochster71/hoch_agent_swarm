import random
import time
import logging
import psutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ClusterManager")

# Node configuration details exactly matching the visual dashboard mockups
NODES_CONFIG = {
    "L1": {
        "id": "L1",
        "name": "MBP MS PRO (CONTROL PLANE)",
        "ip": "10.0.0.6",
        "role": "CONTROL PLANE / KERNEL HUB",
        "specs": "24GB RAM, 1TB SSD",
        "status": "Active",
        "total_agents": 10,
        "os": "macOS",
        "cpu_usage": 45,
        "ram_usage": 60,
        "latency_ms": 1.2,
        "agents": [
            {"name": "KernelHub-Mgr", "type": "System Orchestrator", "status": "Active", "description": "Global task scheduling and communication manager."},
            {"name": "TaskScheduler-01", "type": "Routing Engine", "status": "Active", "description": "Assigns incoming prompts to optimal nodes based on load."},
            {"name": "Auditor-Proxy", "type": "Observability", "status": "Active", "description": "Tracks agent costs, token counts, and output validations."}
        ]
    },
    "L2": {
        "id": "L2",
        "name": "MICHAEL'S IMAC",
        "ip": "10.0.0.91",
        "role": "Coder Node",
        "specs": "M3, 8GB RAM, 512GB SSD",
        "status": "Idle",
        "total_agents": 4,
        "os": "macOS",
        "cpu_usage": 12,
        "ram_usage": 35,
        "latency_ms": 1.5,
        "agents": [
            {"name": "Gordy-iMac-01", "type": "Docker Coder (GORDY)", "status": "Idle", "description": "Specialized coding agent runner. Resolves system conflicts and refactoring."},
            {"name": "Parser-02", "type": "Data Extraction", "status": "Idle", "description": "Parses files, logs, and structures unstructured repository content."}
        ]
    },
    "L3": {
        "id": "L3",
        "name": "HOCH-MESH MACBOOK NEO",
        "ip": "10.0.0.8",
        "role": "Coder Node (SSH + DOCKER)",
        "specs": "M3, 8GB RAM, 512GB SSD",
        "status": "Underutilized",
        "total_agents": 5,
        "os": "macOS",
        "cpu_usage": 22,
        "ram_usage": 42,
        "latency_ms": 1.1,
        "agents": [
            {"name": "Gordy-Neo-01", "type": "Docker Coder (GORDY)", "status": "Active", "description": "Active specialized agent. Coding MVP features and debugging tests."},
            {"name": "Deploy-Deployer", "type": "Docker Deployment", "status": "Active", "description": "Builds and tests mobile binaries and packages for validation."},
            {"name": "Gordy-App-Deployer", "type": "App Store Deployer (GORDY)", "status": "Active", "description": "Specialized agent container for automatic MVP builds delivery to Apple App Store & Google Play."}
        ]
    },
    "W1": {
        "id": "W1",
        "name": "DELL 9440",
        "ip": "10.0.0.207",
        "role": "Coder Node (SSH + DOCKER)",
        "specs": "i9-13900H, 32GB RAM, 1TB SSD",
        "status": "Active",
        "total_agents": 12,
        "os": "Windows 11",
        "cpu_usage": 72,
        "ram_usage": 80,
        "latency_ms": 1.8,
        "agents": [
            {"name": "Gordy-Dell-01", "type": "Docker Coder (GORDY)", "status": "Active", "description": "Active specialized agent. Handles heavy refactoring and complex logic puzzles."},
            {"name": "Gordy-Dell-02", "type": "Docker Coder (GORDY)", "status": "Active", "description": "Active specialized agent. Multi-threaded build and syntax checking runner."},
            {"name": "Optimizer-01", "type": "Performance Optimization", "status": "Idle", "description": "Profiles execution latency and memory usage."}
        ]
    },
    "IPAD": {
        "id": "IPAD",
        "name": "IPAD PRO 12\"",
        "ip": "10.0.0.120",
        "role": "Lightweight Agent / UI Client",
        "specs": "M2, 8GB RAM",
        "status": "Active",
        "total_agents": 3,
        "os": "iPadOS",
        "cpu_usage": 15,
        "ram_usage": 30,
        "latency_ms": 2.4,
        "agents": [
            {"name": "UI-Client-Pad", "type": "Lightweight Agent", "status": "Active", "description": "Renders diagnostic outputs and monitoring stream."}
        ]
    },
    "IPHONE": {
        "id": "IPHONE",
        "name": "IPHONE 15 PRO MAX",
        "ip": "10.0.0.74",
        "role": "Lightweight Agent / UI Client",
        "specs": "A17 Pro, 8GB RAM",
        "status": "Active",
        "total_agents": 3,
        "os": "iOS",
        "cpu_usage": 18,
        "ram_usage": 28,
        "latency_ms": 3.1,
        "agents": [
            {"name": "UI-Client-Phone", "type": "Lightweight Agent", "status": "Active", "description": "Vitals and status notifier."}
        ]
    }
}

class ClusterManager:
    def __init__(self):
        self.nodes = NODES_CONFIG.copy()

    def get_cluster_status(self):
        # Check actual host vitals for L1 (Control Plane) using psutil
        try:
            cpu_percent = psutil.cpu_percent()
            virtual_mem = psutil.virtual_memory()
            ram_percent = virtual_mem.percent
            ram_total_gb = round(virtual_mem.total / (1024 ** 3), 1)
            
            self.nodes["L1"]["cpu_usage"] = int(cpu_percent)
            self.nodes["L1"]["ram_usage"] = int(ram_percent)
            self.nodes["L1"]["specs"] = f"{ram_total_gb}GB RAM, Disk: {psutil.disk_usage('/').percent}% used"
        except Exception as e:
            logger.warning(f"Failed to query psutil host vitals: {e}")

        # Update metrics with slight random fluctuations to simulate dynamic load
        total_agents = 0
        total_cpu = 0
        total_ram_used = 0
        total_ram_cap = 0
        count = 0
        
        for node_id, node in self.nodes.items():
            # Add dynamic variations to cpu and ram
            if node_id == "L1":
                pass
            elif node["status"] == "Active":
                node["cpu_usage"] = min(98, max(5, node["cpu_usage"] + random.randint(-5, 5)))
                node["ram_usage"] = min(95, max(10, node["ram_usage"] + random.randint(-2, 2)))
            
            total_agents += node["total_agents"]
            total_cpu += node["cpu_usage"]
            
            # Estimate RAM usage in GB based on specs string
            ram_gb = 8
            if "24GB" in node["specs"]:
                ram_gb = 24
            elif "32GB" in node["specs"]:
                ram_gb = 32
            elif "GB" in node["specs"]:
                try:
                    parts = node["specs"].split("GB")[0].strip()
                    ram_gb = float(parts)
                except ValueError:
                    ram_gb = 8
            
            total_ram_cap += ram_gb
            total_ram_used += (node["ram_usage"] / 100.0) * ram_gb
            count += 1
            
        avg_cpu = total_cpu / count
        
        return {
            "status": "HEALTHY 100%",
            "active_assets": len([n for n in self.nodes.values() if n["status"] != "Idle"]),
            "sync": "OK",
            "latency": "1.2ms (Excellent)",
            "total_agents": total_agents,
            "system_cpu": f"{int(avg_cpu)}%",
            "system_ram": f"{round(total_ram_used, 1)}GB/{total_ram_cap}GB",
            "nodes": list(self.nodes.values())
        }

    def add_node(self, node_data: dict):
        node_id = node_data.get("id")
        if not node_id:
            return False
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
        if node_id in self.nodes:
            # Prevent removing L1 control plane
            if node_id == "L1":
                return False
            del self.nodes[node_id]
            logger.info(f"Node '{node_id}' successfully removed from cluster.")
            return True
        return False

    def route_task(self, task_type: str, prompt: str):
        # Decide which node gets the task based on task requirements or explicit targeting
        prompt_lower = prompt.lower()
        
        if "neo" in prompt_lower or "l3" in prompt_lower:
            target_node = "L3"
        elif "deploy" in prompt_lower or "app store" in prompt_lower:
            target_node = "L3" # Neo hosts the Gordy-App-Deployer agent!
        elif "imac" in prompt_lower or "l2" in prompt_lower:
            target_node = "L2"
        elif "dell" in prompt_lower or "w1" in prompt_lower or "9440" in prompt_lower:
            target_node = "W1"
        elif "ipad" in prompt_lower:
            target_node = "IPAD"
        elif "iphone" in prompt_lower:
            target_node = "IPHONE"
        elif "code" in prompt_lower or "write" in prompt_lower or "research" in prompt_lower:
            # Code/Research tasks go to coder nodes
            active_coders = [n for n in ["L2", "L3", "W1"] if self.nodes[n]["status"] != "Offline"]
            if active_coders:
                # Select the one with the lowest CPU usage
                target_node = min(active_coders, key=lambda n: self.nodes[n]["cpu_usage"])
            else:
                target_node = "L1"
        elif "mobile" in task_type or "ui" in prompt_lower:
            target_node = "IPAD"
        else:
            target_node = "L1" # Default Control Plane
            
        logger.info(f"Routing task '{task_type}' to node: {self.nodes[target_node]['name']} ({self.nodes[target_node]['ip']})")
        return self.nodes[target_node]
