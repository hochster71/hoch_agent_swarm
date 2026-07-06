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
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OLLAMA = "http://127.0.0.1:11434/api/tags"
LMSTUDIO = "http://127.0.0.1:1234/v1/models"


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
    backend = None
    models = []
    if ollama_ok:
        backend, models = "ollama:11434", _models(ollama_body)
    elif lm_ok:
        backend, models = "lmstudio:1234", _models(lm_body)

    backend_up = backend is not None
    has_model = bool(models)
    if backend_up and has_model:
        verdict = "M1_READY"
    elif backend_up:
        verdict = "M1_BACKEND_UP_NO_MODEL"  # reachable but nothing to generate with
    else:
        verdict = "M1_PENDING_LOCAL_MODEL"
    ready = backend_up and has_model  # generation-ready only with a model present

    # Cloud/K1 truth: are OPENAI/ANTHROPIC keys set in the environment?
    openai_set = bool(os.environ.get("OPENAI_API_KEY"))
    anthropic_set = bool(os.environ.get("ANTHROPIC_API_KEY"))

    result = {
        "schema": "brain-m1-readiness-v1",
        "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
        "verdict": verdict,
        "live_brain_available": ready,
        "local_backend": backend,
        "local_models_detected": models,
        "probes": {"ollama_11434": ollama_ok, "lmstudio_1234": lm_ok},
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
            "A local backend is reachable WITH a model — the improver can generate live candidates now."
            if ready
            else (f"Ollama/LM Studio is up ({backend}) but has NO model loaded — run `ollama pull <model>` "
                  "(e.g. llama3.1) or load a model in LM Studio, then re-run. No API key required."
                  if backend_up
                  else "Start Ollama (`ollama serve` + `ollama pull <model>`) or LM Studio (load a model on :1234), "
                       "then re-run. No API key required.")
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
