import threading
import time
import json
import sys
from pathlib import Path
from scripts.scan_ai_runtimes import main as run_scan
from backend.detection_events import DetectionEventBus

SCAN_LOCK = threading.Lock()
SCAN_JSON_PATH = Path(__file__).parent.parent / "artifacts" / "network_discovery" / "ai_runtime_scan.json"

class DiscoveryDaemon:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.event_bus = DetectionEventBus()

    def start(self):
        with self.lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._run_loop, name="DiscoveryDaemonThread", daemon=True)
                self.thread.start()
                print("DiscoveryDaemon started successfully.")

    def stop(self):
        with self.lock:
            self.running = False

    def _run_loop(self):
        # Stabilize startup
        time.sleep(5)
        while self.running:
            try:
                self.tick()
            except Exception as e:
                print(f"Error in DiscoveryDaemon tick: {e}", file=sys.stderr)
            # Sleep in small chunks to support responsive shutdown
            for _ in range(self.interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

    def tick(self) -> list:
        # 1. Read old findings
        old_findings = []
        if SCAN_JSON_PATH.exists():
            try:
                with open(SCAN_JSON_PATH, "r") as f:
                    old_data = json.load(f)
                    old_findings = old_data.get("findings", [])
            except Exception as e:
                print(f"Error loading old scan results: {e}", file=sys.stderr)

        old_map = {(f.get("host"), f.get("port")): f for f in old_findings}

        # 2. Run new scan under lock
        with SCAN_LOCK:
            try:
                run_scan()
            except Exception as e:
                print(f"Error running scan: {e}", file=sys.stderr)
                return []

        # 3. Read new findings
        new_findings = []
        if SCAN_JSON_PATH.exists():
            try:
                with open(SCAN_JSON_PATH, "r") as f:
                    new_data = json.load(f)
                    new_findings = new_data.get("findings", [])
            except Exception as e:
                print(f"Error loading new scan results: {e}", file=sys.stderr)
                return []
        else:
            return []

        new_map = {(f.get("host"), f.get("port")): f for f in new_findings}

        # 4. Perform diff and emit events
        MODEL_PORTS = (1234, 11434)

        # Appeared
        for key, new_item in new_map.items():
            host, port = key
            if port not in MODEL_PORTS:
                continue

            old_item = old_map.get(key)
            was_open = old_item.get("open", False) if old_item else False
            is_open = new_item.get("open", False)

            reachable = is_open
            raw = new_item.get("raw", {})
            # If endpoint is Ollama but model list failed, mark as degraded/unreachable
            if "api_tags" in raw and "_error" in raw["api_tags"]:
                reachable = False

            was_reachable = was_open
            if old_item:
                old_raw = old_item.get("raw", {})
                if "api_tags" in old_raw and "_error" in old_raw["api_tags"]:
                    was_reachable = False

            if reachable and not was_reachable:
                self.event_bus.emit(
                    event_family="discovery",
                    severity="low",
                    source_log="network_scan",
                    reason=f"Model server appeared: {host}:{port} ({new_item.get('kind', '')})",
                    metadata={
                        "host": host,
                        "port": port,
                        "kind": new_item.get("kind", ""),
                        "action": "appeared",
                        "model_count": len(new_item.get("models", []))
                    }
                )

        # Disappeared
        for key, old_item in old_map.items():
            host, port = key
            if port not in MODEL_PORTS:
                continue

            was_open = old_item.get("open", False)
            was_reachable = was_open
            old_raw = old_item.get("raw", {})
            if "api_tags" in old_raw and "_error" in old_raw["api_tags"]:
                was_reachable = False

            new_item = new_map.get(key)
            is_open = new_item.get("open", False) if new_item else False
            reachable = is_open
            if new_item:
                raw = new_item.get("raw", {})
                if "api_tags" in raw and "_error" in raw["api_tags"]:
                    reachable = False

            if was_reachable and not reachable:
                self.event_bus.emit(
                    event_family="discovery",
                    severity="medium",
                    source_log="network_scan",
                    reason=f"Model server disappeared: {host}:{port}",
                    metadata={
                        "host": host,
                        "port": port,
                        "action": "disappeared"
                    }
                )

        # Unexpected ports exposed on a model server host
        model_server_hosts = {host for (host, port), item in new_map.items() if port in MODEL_PORTS and item.get("open", False)}

        for key, new_item in new_map.items():
            host, port = key
            if host in model_server_hosts and port not in MODEL_PORTS:
                is_open = new_item.get("open", False)
                old_item = old_map.get(key)
                was_open = old_item.get("open", False) if old_item else False

                if is_open and not was_open:
                    self.event_bus.emit(
                        event_family="discovery",
                        severity="medium",
                        source_log="network_scan",
                        reason=f"Model server {host} exposed unexpected port: {port} ({new_item.get('kind', '')})",
                        metadata={
                            "host": host,
                            "port": port,
                            "kind": new_item.get("kind", ""),
                            "action": "unexpected_port"
                        }
                    )

        return new_findings

    def scan_now(self) -> dict:
        try:
            self.tick()
            from backend.live_runtime_discovery import load_ai_runtime_discovery
            return load_ai_runtime_discovery()
        except Exception as e:
            print(f"Error in manual rescan: {e}", file=sys.stderr)
            return {}

# Single global instance
DAEMON = DiscoveryDaemon(interval_seconds=60)
