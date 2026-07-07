#!/usr/bin/env python3
"""MODEL AUTO-UPGRADE STATION.

Keeps HAS on the best *currently-available* model per tier, automatically.
  - Queries each keyed provider for its live model list.
  - Ranks by family + version (auto-adopts newer versions: gpt-5.4 -> gpt-5.5 -> ... with no code change).
  - SMOKE-TESTS the top pick before promoting it (consistent: never promote a broken model).
  - Writes model_registry.json (read by agent_executor). Keeps last-known-good on failure.
  - Records every change in an audit ledger (improving + auditable).

Run on a schedule (weekly / on demand): python3 scripts/model_upgrade.py
The tier router reads the registry, so upgrades take effect with zero code edits.
"""
from __future__ import annotations
import datetime, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REGISTRY = ROOT / "has_live_project_tracker/data/model_registry.json"
AUDIT = ROOT / "has_live_project_tracker/data/model_upgrade_audit.jsonl"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _ver(mid: str) -> float:
    """Extract a comparable version number from a model id (higher = newer)."""
    m = re.search(r"(\d+(?:\.\d+)?)", mid)
    return float(m.group(1)) if m else 0.0


def _rank_openai(ids, kind):
    """kind: 'frontier' (big) or 'cheap' (mini). Return best id or None."""
    bad = ("embed", "whisper", "tts", "audio", "realtime", "image", "dall", "moderation",
           "transcribe", "search", "vision-preview", "instruct")
    ids = [i for i in ids if not any(b in i for b in bad)]
    if kind == "cheap":
        pool = [i for i in ids if ("mini" in i or "nano" in i) and i.startswith(("gpt-",))]
    else:
        pool = [i for i in ids if i.startswith(("gpt-5", "gpt-4.1", "gpt-4o", "o3", "o4"))
                and "mini" not in i and "nano" not in i]
    if not pool:
        return None
    # prefer alias (no trailing date) then highest version
    def key(i):
        dated = 1 if re.search(r"\d{4}-\d{2}-\d{2}", i) else 0     # aliases (undated) preferred -> 0
        fam = 2 if i.startswith("gpt-5") else (1 if i.startswith(("gpt-4.1", "gpt-4o", "o3", "o4")) else 0)
        return (fam, _ver(i), -dated)
    return sorted(pool, key=key, reverse=True)[0]


def _list_openai(key):
    from openai import OpenAI
    return [m.id for m in OpenAI(api_key=key).models.list().data]


def _smoke(provider, model, key, base=None):
    """Return True if the model answers a trivial prompt."""
    try:
        from openai import OpenAI
        kw = {"api_key": key}
        if base:
            kw["base_url"] = base
        newer = model.startswith(("gpt-5", "o1", "o3", "o4"))
        p = {"model": model, "messages": [{"role": "user", "content": "Reply with exactly: OK"}]}
        if newer:
            p["max_completion_tokens"] = 5
        else:
            p["temperature"] = 0; p["max_tokens"] = 5
        out = OpenAI(**kw).chat.completions.create(**p).choices[0].message.content or ""
        return "OK" in out.upper()
    except Exception as e:
        print(f"  smoke fail {model}: {str(e)[:70]}")
        return False


def _load_env():
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def resolve():
    _load_env()
    prev = {}
    try:
        prev = json.loads(REGISTRY.read_text())
    except Exception:
        pass
    reg = {"resolved_at": _now(), "tiers": dict(prev.get("tiers", {}))}
    changes = []
    ok = os.environ.get("OPENAI_API_KEY")
    gk = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    if ok:
        try:
            ids = _list_openai(ok)
            for kind, envname in (("frontier", "frontier"), ("cheap", "cheap")):
                pick = _rank_openai(ids, kind)
                if pick and _smoke("openai", pick, ok):
                    old = (prev.get("tiers", {}).get(envname) or {}).get("model")
                    reg["tiers"][envname] = {"provider": "openai", "model": pick, "verified": True, "at": _now()}
                    if pick != old:
                        changes.append({"tier": envname, "from": old, "to": pick})
                    print(f"  {kind}: openai -> {pick}  ✓")
                elif pick:
                    print(f"  {kind}: {pick} failed smoke — keeping last-known-good")
        except Exception as e:
            print(f"  openai list failed ({str(e)[:70]}) — keeping registry")

    # Gemini: verify the configured flash/pro if the key is billing-enabled (else leave as bonus)
    if gk:
        gm = os.environ.get("AGENT_GEMINI_MODEL", "gemini-2.5-flash")
        base = "https://generativelanguage.googleapis.com/v1beta/openai/"
        if _smoke("gemini", gm, gk, base):
            reg["tiers"]["gemini"] = {"provider": "gemini", "model": gm, "verified": True, "at": _now()}
            print(f"  gemini: {gm}  ✓ (billing OK)")
        else:
            reg["tiers"]["gemini"] = {"provider": "gemini", "model": gm, "verified": False, "at": _now(),
                                      "note": "smoke failed (free-tier 429 or no billing) — bonus only"}
            print(f"  gemini: {gm}  ✗ (free-tier/no billing — used only as fallback)")

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2))
    if changes:
        with open(AUDIT, "a") as f:
            for c in changes:
                f.write(json.dumps({"ts": _now(), **c}) + "\n")
        print(f"UPGRADED: {changes}")
    else:
        print("no changes — already on best available")
    return reg


if __name__ == "__main__":
    print(f"[{_now()}] MODEL AUTO-UPGRADE resolving best available per tier…")
    r = resolve()
    print(json.dumps(r.get("tiers", {}), indent=2))
