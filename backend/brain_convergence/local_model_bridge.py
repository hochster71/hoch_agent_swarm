"""M0→M1 bridge: the $0 live-brain path.

The convergence loop's GENERATE stage needs a model to *create* improved prompt candidates
(not just select existing ones). Rung 2 uses paid Opus; this bridge uses your LOCAL models
(Ollama / LM Studio) so the brain can reason for $0 — your NS-01 local-first north star.

Design contract (honest + safe):
- Detects a local model backend (Ollama :11434, LM Studio :1234). If none is reachable, returns
  NO candidates and says so — it NEVER fabricates output and NEVER crashes the loop.
- Every candidate is labeled with its real source (LOCAL:<model>), so downstream scoring/judging
  knows it came from a local model, not a mechanical heuristic and not a paid frontier model.
- Runs on the operator's machine (where Ollama lives); it only calls localhost, never the web.
"""
import json
import os
import urllib.request
from typing import List, Dict, Any, Optional

# Host is env-configurable so an always-on daemon (e.g. HOCH-200) can point at the operator's
# Ollama over Tailscale instead of its own empty localhost. Defaults unchanged (localhost).
#   OLLAMA_HOST / OLLAMA_URL  e.g. http://100.x.y.z:11434   (Mac's tailscale IP)
#   LMSTUDIO_URL              e.g. http://100.x.y.z:1234
#   BRAIN_M1_MODEL            preferred model (e.g. qwen3:14b); falls back to first available
OLLAMA_URL = os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434"
LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://127.0.0.1:1234")
_PREFERRED_MODEL = os.environ.get("BRAIN_M1_MODEL", "").strip()

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def _urlopen(url_or_req, timeout: float):
    return _opener.open(url_or_req, timeout=timeout)


def detect_local_backend(timeout: float = 1.5) -> Optional[Dict[str, str]]:
    """Return {'kind','base','model'} for the first reachable local backend, else None."""
    # Ollama
    try:
        with _urlopen(f"{OLLAMA_URL}/api/tags", timeout=timeout) as r:
            tags = json.loads(r.read().decode())
            models = [m.get("name") for m in tags.get("models", []) if m.get("name")]
            if models:
                chosen = _PREFERRED_MODEL if _PREFERRED_MODEL in models else models[0]
                return {"kind": "ollama", "base": OLLAMA_URL, "model": chosen}
    except Exception:
        pass
    # LM Studio (OpenAI-compatible)
    try:
        with _urlopen(f"{LMSTUDIO_URL}/v1/models", timeout=timeout) as r:
            data = json.loads(r.read().decode())
            ms = [m.get("id") for m in data.get("data", []) if m.get("id")]
            if ms:
                chosen = _PREFERRED_MODEL if _PREFERRED_MODEL in ms else ms[0]
                return {"kind": "lmstudio", "base": LMSTUDIO_URL, "model": chosen}
    except Exception:
        pass
    return None


def _ollama_generate(base: str, model: str, prompt: str, timeout: float) -> str:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(f"{base}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with _urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()).get("response", "").strip()


def _lmstudio_generate(base: str, model: str, prompt: str, timeout: float) -> str:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.7}).encode()
    req = urllib.request.Request(f"{base}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with _urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
        return d["choices"][0]["message"]["content"].strip()


def generate_candidates(base_prompt: str, task_class: str, n: int = 2,
                        timeout: float = 60.0, backend: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Ask the local model to produce N improved variants of base_prompt. Returns a list of
    {text, source}. Empty list if no local backend is up (honest — mechanical-only fallback)."""
    backend = backend or detect_local_backend()
    if not backend:
        return []
    instruction = (
        f"You are improving an agent prompt for the task class '{task_class}'. Rewrite the prompt "
        f"below to be MORE disciplined: add explicit scope, required evidence/verification, "
        f"anti-fake-green checks, rollback conditions, and a structured output. Return ONLY the "
        f"improved prompt.\n\n---\n{base_prompt}\n---"
    )
    out = []
    for _ in range(max(1, n)):
        try:
            if backend["kind"] == "ollama":
                text = _ollama_generate(backend["base"], backend["model"], instruction, timeout)
            else:
                text = _lmstudio_generate(backend["base"], backend["model"], instruction, timeout)
            if text:
                out.append({"text": text, "source": f"LOCAL:{backend['kind']}:{backend['model']}"})
        except Exception as e:
            out.append({"text": "", "source": f"LOCAL_ERROR:{e}"})
    return [c for c in out if c["text"]]


def status() -> Dict[str, Any]:
    b = detect_local_backend()
    return {"live_brain_available": bool(b), "backend": b,
            "note": "brain can GENERATE at $0" if b else "no local model up — mechanical-only (start Ollama for live brain)"}
