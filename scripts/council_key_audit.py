#!/usr/bin/env python3
"""Audit all council/provider API keys in .env: presence + live validation. Never prints key values."""
import os, sys, urllib.request
# REQ-ES-003: this diagnostic probes provider endpoints with credentials.
# The guard makes those probes fail CLOSED unless a gateway context is active.
import sys as _sys; from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
from scripts.council.gateway import ensure_guard
ensure_guard()

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

PROVIDERS = [
    ("OPENAI_API_KEY",     "https://api.openai.com/v1/models",                    "bearer"),
    ("ANTHROPIC_API_KEY",  "https://api.anthropic.com/v1/models",                 "anthropic"),
    ("GOOGLE_API_KEY",     "https://generativelanguage.googleapis.com/v1beta/models?key={k}", "query"),
    ("XAI_API_KEY",        "https://api.x.ai/v1/models",                          "bearer"),
    ("CEREBRAS_API_KEY",   "https://api.cerebras.ai/v1/models",                   "bearer"),
    ("GROQ_API_KEY",       "https://api.groq.com/openai/v1/models",               "bearer"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/models",                 "bearer"),
    ("DEEPSEEK_API_KEY",   "https://api.deepseek.com/v1/models",                  "bearer"),
]

def load_env(path):
    env, dups = {}, {}
    try:
        for ln in open(path):
            ln = ln.strip()
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1)
                dups[k] = dups.get(k, 0) + 1
                env[k] = v.strip()  # last one wins (matches dotenv behavior)
    except FileNotFoundError:
        sys.exit(f"no .env at {path}")
    return env, {k: c for k, c in dups.items() if c > 1}

def probe(url, key, auth):
    req = urllib.request.Request(url.format(k=key))
    req.add_header("User-Agent", "Mozilla/5.0")
    if auth == "bearer":
        req.add_header("Authorization", f"Bearer {key}")
    elif auth == "anthropic":
        req.add_header("x-api-key", key)
        req.add_header("anthropic-version", "2023-06-01")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"ERR {type(e).__name__}"

env, dups = load_env(ENV_PATH)
print(f"{'KEY':<22}{'STATUS':<12}NOTE")
fails = 0
for name, url, auth in PROVIDERS:
    key = env.get(name, "")
    if not key:
        print(f"{name:<22}{'MISSING':<12}not in .env")
        fails += 1
        continue
    code = probe(url, key, auth)
    ok = code == 200
    if not ok:
        fails += 1
    note = f"len={len(key)}" + (f"  ⚠ {dups[name]} duplicate lines in .env" if name in dups else "")
    print(f"{name:<22}{('🟢 200' if ok else f'🔴 {code}'):<12}{note}")
if dups:
    print(f"\nduplicate .env entries (last wins): {', '.join(f'{k}×{c}' for k, c in dups.items())}")
sys.exit(1 if fails else 0)
