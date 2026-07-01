from __future__ import annotations
import time
import threading
import requests
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from backend.model_router.model_registry import get_providers
from backend.runtime_process import RuntimeProcessBus, RuntimeProcessType, RuntimeProcessState

@dataclass
class ProviderHealth:
    provider: str
    type: str
    base_url: str
    enabled: bool
    reachable: bool
    checked_at: str
    latency_ms: float | None
    error: str | None

class LocalRuntimeSupervisor:
    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = interval_seconds
        self.bus = RuntimeProcessBus()
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_health: list[ProviderHealth] = []

    def check_once(self) -> list[ProviderHealth]:
        results = []
        providers = get_providers()
        for name, data in providers.items():
            if data.get("type") == "local" and data.get("enabled", False):
                start = time.perf_counter()
                reachable = False
                error = None
                api_style = data.get("api_style", "openai")
                base_url = data.get("base_url", "")
                try:
                    if api_style == "ollama":
                        url = f"{base_url}/api/tags"
                    else:
                        url = f"{base_url}/models"
                    res = requests.get(url, timeout=5)
                    reachable = 200 <= res.status_code < 500
                except Exception as exc:
                    error = str(exc)
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                health = ProviderHealth(
                    provider=name,
                    type=data.get("type"),
                    base_url=base_url,
                    enabled=data.get("enabled", False),
                    reachable=reachable,
                    checked_at=datetime.now(timezone.utc).isoformat(),
                    latency_ms=latency_ms,
                    error=error,
                )
                results.append(health)
                self.bus.emit(
                    RuntimeProcessType.LOCAL_MODEL_HEALTH,
                    RuntimeProcessState.LIVE if reachable else RuntimeProcessState.FAILED,
                    f"Local provider health check: {name}",
                    provider=name,
                    model=None,
                    escalation_used=False,
                    metadata=asdict(health),
                )
        self._last_health = results
        return results

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        def loop() -> None:
            while self._running:
                self.check_once()
                time.sleep(self.interval_seconds)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "interval_seconds": self.interval_seconds,
            "providers": [asdict(x) for x in self._last_health],
        }

SUPERVISOR = LocalRuntimeSupervisor()
