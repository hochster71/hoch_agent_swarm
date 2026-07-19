"""HELM Voice Executive — orchestration-backed voice interface.

Voice is the executive interface, not the intelligence.
All live claims must be observed; unknown remains UNKNOWN.
"""

from backend.voice.policy import load_voice_policy, get_policy_public
from backend.voice.sanitizer import sanitize_for_speech
from backend.voice.commands import COMMAND_REGISTRY, resolve_command
from backend.voice.briefing import build_executive_brief, execute_voice_command

# Unambiguous forward name for the VOICE-scoped brief. The canonical unified HELM brief
# is backend.helm_executive_brief.build_executive_brief. `build_executive_brief` is kept
# here as a back-compat alias so existing imports keep working (no breakage).
build_voice_brief = build_executive_brief

__all__ = [
    "load_voice_policy",
    "get_policy_public",
    "sanitize_for_speech",
    "COMMAND_REGISTRY",
    "resolve_command",
    "build_executive_brief",
    "build_voice_brief",
    "execute_voice_command",
]
