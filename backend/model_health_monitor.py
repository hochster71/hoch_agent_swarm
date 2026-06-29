import os
import time
import json
import yaml
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.runtime_truth.state_store import resolve_root_dir
ROOT = Path(resolve_root_dir())
ROUTING_PATH = ROOT / "src/hoch_agent_swarm/config/model_routing.yaml"

class ModelHealthMonitor:
    def __init__(self):
        self.ollama_url = os.environ.get("OLLAMA_HOST") or os.environ.get("API_BASE") or "http://localhost:11434"
        self._cached_health: Dict[str, Any] = {}
        self._last_scan_time = 0.0
        self._cache_ttl = 15.0  # seconds

    def get_routing_config(self) -> Dict[str, Any]:
        if not ROUTING_PATH.exists():
            return {}
        try:
            with open(ROUTING_PATH, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading routing config in health monitor: {e}")
            return {}

    def get_pulled_models(self) -> Dict[str, Dict[str, Any]]:
        url = f"{self.ollama_url.rstrip('/')}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                pulled = {}
                for m in data.get("models", []):
                    name = m.get("name") or m.get("model")
                    if name:
                        pulled[name] = m
                        # Also support name without tag if it's :latest
                        if ":" in name:
                            base, tag = name.split(":", 1)
                            if tag == "latest":
                                pulled[base] = m
                return pulled
        except Exception as e:
            print(f"Ollama offline or tags unreachable at {url}: {e}")
            return {}

    def ping_model(self, model_name: str) -> Dict[str, Any]:
        """Perform a fast, single-token generate completion check to verify chat compatibility."""
        url = f"{self.ollama_url.rstrip('/')}/api/generate"
        payload = {
            "model": model_name,
            "prompt": "ping",
            "stream": False,
            "options": {
                "num_predict": 1
            }
        }
        start_time = time.perf_counter()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=4.0) as response:
                res = json.loads(response.read().decode("utf-8"))
                latency = (time.perf_counter() - start_time) * 1000.0
                return {
                    "compatible": True,
                    "latency_ms": round(latency, 2),
                    "error": None
                }
        except Exception as e:
            return {
                "compatible": False,
                "latency_ms": -1.0,
                "error": str(e)
            }

    def scan_health(self, force: bool = False) -> Dict[str, Any]:
        now = time.time()
        if not force and self._cached_health and (now - self._last_scan_time < self._cache_ttl):
            return self._cached_health

        config = self.get_routing_config()
        routing_rules = config.get("routing", {})
        agents_mapping = config.get("agents", {})

        pulled = self.get_pulled_models()
        ollama_online = len(pulled) > 0 or (self.check_ollama_reachable())

        # Collect unique models mentioned in config
        unique_models = set()
        for rule in routing_rules.values():
            if rule.get("primary"):
                unique_models.add(rule.get("primary"))
            if rule.get("fallback"):
                unique_models.add(rule.get("fallback"))
        
        # Also check default model from env
        env_default = os.getenv("MODEL", "ollama/llama3.1:8b")
        unique_models.add(env_default)

        # Build detailed model status dictionary
        model_details = {}
        for raw_model in unique_models:
            # Strip provider prefix if needed
            model_name = raw_model
            if model_name.startswith("ollama/"):
                model_name = model_name[len("ollama/"):]

            is_pulled = model_name in pulled
            size_bytes = -1
            size_category = "UNKNOWN"
            status = "MISSING"
            latency = -1.0
            compatibility_error = None

            if not ollama_online:
                status = "OFFLINE"
            elif is_pulled:
                m_info = pulled[model_name]
                size_bytes = m_info.get("size", -1)
                
                # Sizing categorizations
                if size_bytes > 15_000_000_000:
                    size_category = "HEAVY"
                elif 0 < size_bytes < 4_000_000_000:
                    size_category = "LIGHT"
                elif size_bytes > 0:
                    size_category = "STANDARD"

                # Perform chat-test check
                ping_res = self.ping_model(model_name)
                if ping_res["compatible"]:
                    status = "HEALTHY"
                    latency = ping_res["latency_ms"]
                else:
                    status = "FAILING"
                    compatibility_error = ping_res["error"]

            model_details[raw_model] = {
                "raw_name": raw_model,
                "clean_name": model_name,
                "pulled": is_pulled,
                "size_bytes": size_bytes,
                "size_category": size_category,
                "status": status,
                "latency_ms": latency,
                "compatibility_error": compatibility_error
            }

        # Evaluate fallback readiness per task class
        fallback_readiness = {}
        for class_name, rule in routing_rules.items():
            primary = rule.get("primary")
            fallback = rule.get("fallback")

            primary_status = model_details.get(primary, {}).get("status", "MISSING") if primary else "MISSING"
            fallback_status = model_details.get(fallback, {}).get("status", "MISSING") if fallback else "MISSING"

            if primary_status == "HEALTHY":
                color = "GREEN"
                msg = f"Primary model '{primary}' is healthy and available."
            elif fallback_status == "HEALTHY":
                color = "AMBER"
                msg = f"Primary '{primary}' is {primary_status.lower()}; automatically falling back to healthy model '{fallback}'."
            else:
                color = "RED"
                msg = f"CRITICAL: Both primary '{primary}' ({primary_status.lower()}) and fallback '{fallback}' ({fallback_status.lower()}) are unavailable!"

            fallback_readiness[class_name] = {
                "class_name": class_name,
                "primary": primary,
                "fallback": fallback,
                "primary_status": primary_status,
                "fallback_status": fallback_status,
                "status": color,
                "message": msg
            }

        # Return consolidated report
        self._cached_health = {
            "ollama_online": ollama_online,
            "endpoint_url": self.ollama_url,
            "models": list(model_details.values()),
            "fallback_readiness": list(fallback_readiness.values()),
            "agents_mapping": agents_mapping,
            "last_checked": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        self._last_scan_time = now
        return self._cached_health

    def check_ollama_reachable(self) -> bool:
        try:
            req = urllib.request.Request(self.ollama_url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5):
                return True
        except Exception:
            return False

# Global health monitor instance
MONITOR = ModelHealthMonitor()
