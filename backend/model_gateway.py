"""HOCH Model Gateway — zero-downtime inference routing across all live backends.

Doctrine (2026-07-07): MODEL_OFFLINE is never acceptable. Three compute resources exist:
  - L1 local Mac (127.0.0.1:11434) — llama3.1:8b, primary
  - Tailscale Mac (100.103.155.4:11434) — same models, secondary
  - hoch-relay-001 (100.87.18.15:11434) — qwen3:1.7b, always-on fallback

This gateway:
  1. Probes all backends with a real generation probe (not just /api/tags listing)
  2. Routes to the best live backend with automatic failover
  3. Never returns MODEL_OFFLINE as long as ANY backend is alive
  4. Refreshes health state every 60s in a background thread
  5. Records every backend switch in the outcome ledger (transparent, traceable)

Sources:
  - HAProxy health check pattern: binadit.com/tutorials/load-balancer-multiple-ollama-instances (2026-04)
  - Generation-proven probe: Goodhart fix from scorer.py (2026-07-06) — listing != capability
  - Failover weight schedule: localaimaster.com/blog/ollama-load-balancing (2026-04)

stdlib + requests only. Drop-in replacement for AgentRunner's ollama_url + default_model.
"""
import json
import time
import logging
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

BACKENDS_CONFIG = [
    # Priority order: most capable first, relay last (always-on backstop).
    # LM Studio (gemma-4-12b) discovered live 2026-07-07 — highest local capability.
    {"name": "lmstudio",      "base": "http://127.0.0.1:1234",       "preferred_model": "google/gemma-4-12b-qat", "priority": 1, "api": "openai"},
    {"name": "mac-local",     "base": "http://127.0.0.1:11434",      "preferred_model": "llama3.1:8b",            "priority": 2, "api": "ollama", "probe_keep_alive": 0},
    # mac-tailscale REMOVED 2026-07-07: 100.103.155.4 is THIS same MacBook — a duplicate
    # of mac-local that ran a 2nd Ollama server + 2nd resident model copy, pushing free RAM
    # to ~6% and triggering macOS jetsam kills of Chrome. mac-local (127.0.0.1) already
    # serves the identical model store, so this cost RAM for zero added capability.
    {"name": "relay-001",     "base": "http://100.87.18.15:11434",    "preferred_model": "qwen3:1.7b",  "priority": 4, "api": "ollama"},
]
PROBE_TIMEOUT   = 20   # seconds for generation probe
HEALTH_INTERVAL = 60   # seconds between full health sweeps
PROBE_PROMPT    = "OK" # minimal probe — 1 token, proves generate works


@dataclass
class BackendState:
    name: str
    base: str
    preferred_model: str
    priority: int
    api: str = "ollama"   # "ollama" | "openai" (LM Studio / OpenAI-compatible)
    # probe_keep_alive: ollama keep_alive for HEALTH PROBES only. 0 = unload the model
    # right after the probe so a big failover model isn't held resident just to stay "alive"
    # (real generate calls still load on demand and use ollama's default keep_alive). None =
    # ollama default. Set 0 on heavy failover backends to protect control-plane RAM.
    probe_keep_alive: Optional[object] = None
    alive: bool = False
    proven_model: Optional[str] = None
    available_models: List[str] = field(default_factory=list)
    last_probe: float = 0.0
    consecutive_failures: int = 0
    latency_ms: Optional[float] = None


class ModelGateway:
    """Thread-safe, auto-failover inference gateway for all HOCH compute backends."""

    def __init__(self):
        self._states: List[BackendState] = [
            BackendState(**{k: v for k, v in b.items()}) for b in BACKENDS_CONFIG
        ]
        self._lock = threading.Lock()
        self._probe_all()  # synchronous initial probe so first call never misses
        self._thread = threading.Thread(target=self._health_loop, daemon=True)
        self._thread.start()
        logger.info(f"ModelGateway: {sum(1 for s in self._states if s.alive)} / "
                    f"{len(self._states)} backends alive at startup")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, prompt: str, system: Optional[str] = None,
                 model: Optional[str] = None, timeout: int = 300) -> str:
        """Generate text. Auto-routes to best live backend. Never raises MODEL_OFFLINE
        as long as any backend is reachable. Raises RuntimeError only if ALL are dead."""
        backends = self._ranked_alive()
        if not backends:
            self._probe_all()           # one emergency re-probe before giving up
            backends = self._ranked_alive()
        if not backends:
            raise RuntimeError(
                "MODEL_GATEWAY_ALL_OFFLINE: no backend is reachable — "
                "mac-local, mac-tailscale, and relay-001 all failed generation probes")

        last_err = None
        for state in backends:
            use_model = model or state.proven_model or state.preferred_model
            try:
                result = self._call_generate(state.base, use_model, prompt, system, timeout, api=state.api)
                with self._lock:
                    state.consecutive_failures = 0
                return result
            except Exception as e:
                last_err = e
                logger.warning(f"Gateway: {state.name} failed ({e}), trying next backend")
                with self._lock:
                    state.consecutive_failures += 1
                    if state.consecutive_failures >= 2:
                        state.alive = False   # mark dead; health loop will re-probe

        raise RuntimeError(f"MODEL_GATEWAY_ALL_FAILED: all live backends errored. "
                           f"Last error: {last_err}")

    def status(self) -> Dict:
        with self._lock:
            return {
                "backends": [
                    {"name": s.name, "alive": s.alive, "model": s.proven_model,
                     "latency_ms": s.latency_ms, "failures": s.consecutive_failures,
                     "last_probe": s.last_probe}
                    for s in sorted(self._states, key=lambda x: x.priority)
                ],
                "primary": next((s.name for s in self._states if s.alive), None),
                "alive_count": sum(1 for s in self._states if s.alive),
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ranked_alive(self) -> List[BackendState]:
        with self._lock:
            return sorted([s for s in self._states if s.alive], key=lambda x: x.priority)

    def _call_generate(self, base: str, model: str, prompt: str,
                       system: Optional[str], timeout: int,
                       api: str = "ollama") -> str:
        if api == "openai":
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            payload: Dict = {"model": model, "messages": msgs, "max_tokens": 2048}
            data = json.dumps(payload).encode()
            req = urllib.request.Request(f"{base}/v1/chat/completions", data=data,
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer lm-studio"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode())
            msg = resp["choices"][0]["message"]
            # Thinking models (gemma-4, nemotron) return content in reasoning_content
            # when content is empty — fall back gracefully.
            return msg.get("content") or msg.get("reasoning_content", "")
        payload: Dict = {"model": model, "prompt": prompt, "stream": False,
                         "options": {"num_predict": 2048}}
        if system:
            payload["system"] = system
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{base}/api/generate", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("response", "")

    def _probe_backend(self, state: BackendState) -> bool:
        """Generation-proven probe across Ollama and OpenAI-compatible (LM Studio) backends."""
        t0 = time.time()
        api = getattr(state, 'api', 'ollama')
        try:
            if api == "openai":
                with urllib.request.urlopen(f"{state.base}/v1/models", timeout=PROBE_TIMEOUT) as r:
                    data = json.loads(r.read().decode())
                models = [m["id"] for m in data.get("data", [])
                          if "embed" not in m.get("id","").lower()]
                ordered = ([state.preferred_model] if state.preferred_model in models else []) +                           [m for m in models if m != state.preferred_model]
                for m in ordered:
                    try:
                        payload = json.dumps({"model": m,
                                              "messages": [{"role":"user","content":"OK"}],
                                              "max_tokens": 1}).encode()
                        req = urllib.request.Request(
                            f"{state.base}/v1/chat/completions", data=payload,
                            headers={"Content-Type":"application/json",
                                     "Authorization":"Bearer lm-studio"})
                        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as pr:
                            resp = json.loads(pr.read().decode())
                        if resp.get("choices"):
                            with self._lock:
                                state.alive = True; state.proven_model = m
                                state.available_models = models
                                state.latency_ms = round((time.time()-t0)*1000,1)
                                state.last_probe = time.time()
                                state.consecutive_failures = 0
                            logger.info(f"Gateway probe OK: {state.name} → {m} ({state.latency_ms}ms)")
                            return True
                    except Exception:
                        continue
            else:
                with urllib.request.urlopen(f"{state.base}/api/tags", timeout=PROBE_TIMEOUT) as r:
                    tags = json.loads(r.read().decode())
                models = [m["name"] for m in tags.get("models", [])
                          if "embed" not in m.get("name","") and "guard" not in m.get("name","")]
                ordered = ([state.preferred_model] if state.preferred_model in models else []) +                           [m for m in models if m != state.preferred_model]
                for m in ordered:
                    try:
                        _body = {"model": m, "prompt": PROBE_PROMPT,
                                 "stream": False, "options": {"num_predict": 1}}
                        if state.probe_keep_alive is not None:
                            _body["keep_alive"] = state.probe_keep_alive  # e.g. 0 = unload after probe
                        payload = json.dumps(_body).encode()
                        req = urllib.request.Request(f"{state.base}/api/generate", data=payload,
                                                     headers={"Content-Type":"application/json"})
                        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as pr:
                            resp = json.loads(pr.read().decode())
                        if "response" in resp and "error" not in resp:
                            with self._lock:
                                state.alive = True; state.proven_model = m
                                state.available_models = models
                                state.latency_ms = round((time.time()-t0)*1000,1)
                                state.last_probe = time.time()
                                state.consecutive_failures = 0
                            logger.info(f"Gateway probe OK: {state.name} → {m} ({state.latency_ms}ms)")
                            return True
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Gateway probe FAIL: {state.name} — {e}")
        with self._lock:
            state.alive = False; state.proven_model = None; state.last_probe = time.time()
        return False

    def _probe_all(self):
        threads = [threading.Thread(target=self._probe_backend, args=(s,), daemon=True)
                   for s in self._states]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=PROBE_TIMEOUT + 5)

    def _health_loop(self):
        while True:
            time.sleep(HEALTH_INTERVAL)
            try:
                self._probe_all()
                alive = sum(1 for s in self._states if s.alive)
                logger.info(f"Gateway health sweep: {alive}/{len(self._states)} alive — "
                            f"primary={next((s.name for s in self._states if s.alive), 'NONE')}")
            except Exception as e:
                logger.error(f"Gateway health loop error: {e}")


# Module-level singleton — import and use anywhere.
_gateway: Optional[ModelGateway] = None
_gw_lock = threading.Lock()

def get_gateway() -> ModelGateway:
    global _gateway
    if _gateway is None:
        with _gw_lock:
            if _gateway is None:
                _gateway = ModelGateway()
    return _gateway
