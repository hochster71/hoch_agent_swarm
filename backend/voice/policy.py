"""Voice policy loader — fail-closed defaults, no paid providers by default."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "voice_policy.yaml"

# Hard fail-closed defaults if YAML is missing or unreadable
_DEFAULTS: Dict[str, Any] = {
    "policy_version": "1.0",
    "persona": "HELM Executive Mission Commander",
    "voice_enabled_default": False,
    "voice_mode": "local_tts",
    "paid_providers_allowed": False,
    "elevenlabs_enabled": False,
    "elevenlabs_model_id": "eleven_multilingual_v2",
    "speak_secrets": False,
    "require_operator_toggle": True,
    "max_events_per_hour": 30,
    "min_severity": "INFO",
    "daily_budget_usd": 0,
    "freshness_budget_seconds": 300,
    "allowed_modes": ["READ_ONLY", "STAGE_ONLY"],
    "doorstep_blocked_verbs": [
        "deploy",
        "deploy_prod",
        "git_push",
        "spend",
        "stripe_live",
        "provision_keys",
        "rotate_keys",
        "sign",
        "notarize",
        "app_store_submit",
        "move_money",
        "clear_release_go",
        "bypass_approval",
    ],
    "redact_patterns": [
        r"sk-[A-Za-z0-9]{10,}",
        r"pk_[A-Za-z0-9]{10,}",
        r"Bearer\s+[A-Za-z0-9._\-]{8,}",
        r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S+",
        r"/Users/[^\s]+",
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
    ],
    "max_speech_chars": 1200,
    "staging_dir": "artifacts/voice/staging",
    "audit_log": "data/runtime/voice_command_audit.jsonl",
}


def _parse_yaml_simple(text: str) -> Dict[str, Any]:
    """Minimal YAML subset parser (no PyYAML dependency required).

    Supports: top-level scalars, lists of scalars, nested only one level for
    policy keys used here. Falls back to defaults on parse failure.
    """
    out: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if current_list_key:
                val = line[4:].strip().strip("'\"")
                out.setdefault(current_list_key, []).append(val)
            continue
        if ":" in line and not line.startswith(" "):
            current_list_key = None
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                current_list_key = key
                out[key] = []
            elif rest.lower() in ("true", "false"):
                out[key] = rest.lower() == "true"
            else:
                try:
                    if "." in rest:
                        out[key] = float(rest)
                    else:
                        out[key] = int(rest)
                except ValueError:
                    out[key] = rest.strip("'\"")
    return out


@lru_cache(maxsize=1)
def load_voice_policy() -> Dict[str, Any]:
    policy = dict(_DEFAULTS)
    try:
        if POLICY_PATH.exists():
            loaded = _parse_yaml_simple(POLICY_PATH.read_text(encoding="utf-8"))
            if loaded:
                policy.update(loaded)
    except Exception:
        pass
    # Normalize types
    if not isinstance(policy.get("allowed_modes"), list):
        policy["allowed_modes"] = list(_DEFAULTS["allowed_modes"])
    if not isinstance(policy.get("doorstep_blocked_verbs"), list):
        policy["doorstep_blocked_verbs"] = list(_DEFAULTS["doorstep_blocked_verbs"])
    if not isinstance(policy.get("redact_patterns"), list):
        policy["redact_patterns"] = list(_DEFAULTS["redact_patterns"])
    return policy


def reload_voice_policy() -> Dict[str, Any]:
    load_voice_policy.cache_clear()
    return load_voice_policy()


def get_policy_public() -> Dict[str, Any]:
    """Safe subset for clients and Grok Voice tool discovery."""
    p = load_voice_policy()
    # ElevenLabs readiness without exposing secrets
    try:
        from backend.voice.elevenlabs_tts import elevenlabs_config_status

        el = elevenlabs_config_status()
    except Exception:
        el = {"ready": False, "status": "UNKNOWN", "key_present": False}
    return {
        "policy_version": p["policy_version"],
        "persona": p["persona"],
        "voice_enabled_default": bool(p["voice_enabled_default"]),
        "voice_mode": p["voice_mode"],
        "paid_providers_allowed": bool(p["paid_providers_allowed"]),
        "elevenlabs_enabled": bool(p.get("elevenlabs_enabled")),
        "elevenlabs_ready": bool(el.get("ready")),
        "elevenlabs_status": el.get("status"),
        "elevenlabs_key_present": bool(el.get("key_present")),
        "speak_secrets": bool(p["speak_secrets"]),
        "require_operator_toggle": bool(p["require_operator_toggle"]),
        "max_events_per_hour": int(p["max_events_per_hour"]),
        "min_severity": p["min_severity"],
        "daily_budget_usd": p["daily_budget_usd"],
        "freshness_budget_seconds": int(p["freshness_budget_seconds"]),
        "allowed_modes": list(p["allowed_modes"]),
        "doorstep_blocked_verbs": list(p["doorstep_blocked_verbs"]),
        "max_speech_chars": int(p["max_speech_chars"]),
        "tts_providers": {
            "local_tts": {"status": "AVAILABLE", "cost": 0},
            "elevenlabs": {
                "status": el.get("status"),
                "ready": el.get("ready"),
                "blocked_reasons": el.get("blocked_reasons"),
            },
            "grok_builtin": {
                "status": "EXTERNAL",
                "note": "Grok Voice Agents may provide its own TTS; HELM ElevenLabs is the fallback premium path",
            },
        },
        "doctrine": [
            "no_fake_green",
            "unknown_is_unknown",
            "stale_is_not_live",
            "doorstep_founder_only",
            "evidence_before_green",
            "paid_tts_fail_closed",
        ],
    }


def is_doorstep_verb(verb: str) -> bool:
    p = load_voice_policy()
    v = (verb or "").strip().lower().replace("-", "_").replace(" ", "_")
    blocked = {str(x).lower() for x in p.get("doorstep_blocked_verbs", [])}
    return v in blocked


def mode_allowed(mode: str) -> bool:
    p = load_voice_policy()
    return mode in set(p.get("allowed_modes") or [])


def compiled_redact_patterns() -> List[re.Pattern]:
    p = load_voice_policy()
    out: List[re.Pattern] = []
    for pat in p.get("redact_patterns") or []:
        try:
            out.append(re.compile(pat))
        except re.error:
            continue
    return out


def staging_dir() -> Path:
    p = load_voice_policy()
    path = ROOT / str(p.get("staging_dir") or "artifacts/voice/staging")
    path.mkdir(parents=True, exist_ok=True)
    return path


def audit_log_path() -> Path:
    p = load_voice_policy()
    path = ROOT / str(p.get("audit_log") or "data/runtime/voice_command_audit.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
