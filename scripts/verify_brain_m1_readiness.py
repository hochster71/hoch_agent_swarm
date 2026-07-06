#!/usr/bin/env python3
"""
BRAIN M1 readiness — is the live-generation loop plug-and-play?

The implemented brain (backend/brain_convergence/local_model_bridge.py) runs M1 (live
candidate generation) off a LOCAL model backend: Ollama (:11434) or LM Studio (:1234).
`live_brain_available` flips true the moment one is reachable — no cloud API key needed.

This script probes those backends and reports, honestly and fail-closed:
  M1_READY               — a local backend answered; start/att the improver and M1 runs live.
  M1_PENDING_LOCAL_MODEL — no local backend up; start Ollama or LM Studio to flip M0 -> M1.

It also states the cloud (K1) situation truthfully: OPENAI/ANTHROPIC keys are NOT currently
read by the brain generator, so K1 keys alone do not enable M1 — the local path does. K1
enables Stripe + any future cloud mesh path, which is separate and not yet wired here.

Exit 0 always (informational). Prints a machine block and a human summary.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve(host, default):
    """Mirror local_model_bridge: honor env host; normalize to a scheme'd base URL."""
    h = (host or default).strip()
    if "://" not in h:
        h = "http://" + h
    return h.rstrip("/")


# Same env the brain bridge reads, so this probes exactly what the daemon would reach
# (on the VPS: OLLAMA_HOST=http://100.103.155.4:11434 -> we verify the Mac's Ollama over Tailscale).
OLLAMA_BASE = _resolve(os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_URL"), "http://127.0.0.1:11434")
LMSTUDIO_BASE = _resolve(os.environ.get("LMSTUDIO_URL"), "http://127.0.0.1:1234")
OLLAMA = OLLAMA_BASE + "/api/tags"
LMSTUDIO = LMSTUDIO_BASE + "/v1/models"


def _probe(url, timeout=1.5):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "ignore")
        return True, body  # full body — do NOT truncate; _models() must parse valid JSON
    except Exception as e:  # noqa
        return False, str(e)


def _models(body):
    try:
        d = json.loads(body)
        if isinstance(d, dict) and "models" in d:  # ollama
            return [m.get("name") for m in d.get("models", [])][:8]
        if isinstance(d, dict) and "data" in d:  # lmstudio/openai-shape
            return [m.get("id") for m in d.get("data", [])][:8]
    except Exception:
        pass
    return []


def _gen_probe(kind, base, model, timeout=25.0):
    """Actually ask the model to generate one token — catches dangling manifests
    (tags lists a model whose blob is missing → /api/generate 400). Returns (ok, detail)."""
    try:
        if kind == "ollama":
            body = json.dumps({"model": model, "prompt": "ok", "stream": False,
                               "options": {"num_predict": 1}}).encode()
            url = base + "/api/generate"
        else:
            body = json.dumps({"model": model, "messages": [{"role": "user", "content": "ok"}],
                               "max_tokens": 1}).encode()
            url = base + "/v1/chat/completions"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        txt = d.get("response") or (d.get("choices", [{}])[0].get("message", {}).get("content") if d.get("choices") else "")
        return (bool(txt) or "response" in d or "choices" in d), "generated ok"
    except urllib.error.HTTPError as e:  # noqa
        detail = e.read().decode("utf-8", "ignore")[:160] if hasattr(e, "read") else str(e)
        return False, f"HTTP {e.code}: {detail}"
    except Exception as e:  # noqa
        return False, f"{type(e).__name__}: {e}"


def _conv():
    try:
        with open(os.path.join(REPO, "data/prompt_brain/convergence_status.json")) as f:
            c = json.load(f)
        return {k: c.get(k) for k in ("state", "generation", "mean_score", "improver_online", "converged")}
    except Exception:
        return {}


def main():
    ollama_ok, ollama_body = _probe(OLLAMA)
    lm_ok, lm_body = _probe(LMSTUDIO)
    kind = base = None
    models = []
    if ollama_ok:
        kind, base, models = "ollama", OLLAMA_BASE, _models(ollama_body)
    elif lm_ok:
        kind, base, models = "lmstudio", LMSTUDIO_BASE, _models(lm_body)
    backend = f"{kind}:{base}" if kind else None

    backend_up = kind is not None
    has_model = bool(models)
    pref = os.environ.get("BRAIN_M1_MODEL", "").strip()
    chosen_model = pref if pref in models else (models[0] if models else None)

    # Actually generate — tags listing a model whose blob is missing still 400s on /api/generate.
    gen_ok, gen_detail = (False, "not attempted (no model)")
    if backend_up and has_model:
        gen_ok, gen_detail = _gen_probe(kind, base, chosen_model)

    if backend_up and has_model and gen_ok:
        verdict = "M1_READY"
    elif backend_up and has_model:
        verdict = "M1_MODEL_LOAD_FAILS"     # listed but generation fails (dangling manifest / missing blob)
    elif backend_up:
        verdict = "M1_BACKEND_UP_NO_MODEL"  # reachable but nothing to generate with
    else:
        verdict = "M1_PENDING_LOCAL_MODEL"
    ready = backend_up and has_model and gen_ok  # truly ready only if generation works

    # Cloud/K1 truth: are OPENAI/ANTHROPIC keys set in the environment?
    openai_set = bool(os.environ.get("OPENAI_API_KEY"))
    anthropic_set = bool(os.environ.get("ANTHROPIC_API_KEY"))

    result = {
        "schema": "brain-m1-readiness-v1",
        "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
        "verdict": verdict,
        "live_brain_available": ready,
        "local_backend": backend,
        "chosen_model": chosen_model,
        "generation_probe": {"ok": gen_ok, "detail": gen_detail},
        "local_models_detected": models,
        "probes": {"ollama": ollama_ok, "lmstudio": lm_ok, "ollama_url": OLLAMA_BASE, "lmstudio_url": LMSTUDIO_BASE},
        "current_convergence": _conv(),
        "cloud_k1": {
            "openai_api_key_set": openai_set,
            "anthropic_api_key_set": anthropic_set,
            "note": (
                "Cloud keys are NOT read by the brain generator today; K1 does not enable M1. "
                "Local model backend is the live-generation path. K1 covers Stripe + future cloud mesh."
            ),
        },
        "to_flip_m0_to_m1": (
            f"Live: {chosen_model} on {backend} generated successfully — the improver can produce candidates now."
            if ready
            else (f"Model '{chosen_model}' is LISTED but generation FAILED ({gen_detail}). Likely a dangling "
                  "manifest / missing blob or the served OLLAMA_MODELS store is incomplete. Re-pull into the served "
                  "store (`OLLAMA_MODELS=<served path> ollama pull <model>`) or point OLLAMA_MODELS at a complete store."
                  if verdict == "M1_MODEL_LOAD_FAILS"
                  else (f"Backend up ({backend}) but no models — pull one into the served store, then re-run."
                        if backend_up
                        else "Start Ollama (`ollama serve` + `ollama pull <model>`) or LM Studio on :1234, then re-run. No API key required."))
        ),
    }
    print(json.dumps(result, indent=2))
    print()
    print(f"BRAIN M1 READINESS: {verdict}"
          + (f" · backend {backend} · models {models}" if backend_up else " · no local model backend up"))
    print("  cloud K1: openai_key="
          f"{openai_set} anthropic_key={anthropic_set} (not required for M1; not wired to brain gen)")
    sys.exit(0)


if __name__ == "__main__":
    main()
