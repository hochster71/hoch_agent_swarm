#!/usr/bin/env python3
"""HELM fires the independent verification — Claude/HELM dispatches Grok, not the founder.

Composes the verification ask from the frozen brief and dispatches it to the AUDITOR
role (bound to xai/grok) through the live gateway, then writes the returned verdict to
docs/evidence/audit/bridge_verification/GROK_VERDICT_<UTC>/verdict.md.

Fail-closed and founder-gated: if HELM_DISPATCH_ENABLED is unset or XAI_API_KEY is
absent, it prints exactly what the founder must enable once (never asks them to run
Grok by hand). No secret is printed.

Usage:  set -a; . ~/.helm/helm.env; set +a; export HELM_DISPATCH_ENABLED=1
        python3 scripts/helm_fire_verification.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PKG = ROOT / "docs" / "evidence" / "audit" / "bridge_verification"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def build_prompt() -> str:
    brief = _read(PKG / "GROK_VERIFICATION_BRIEF.md")
    runv = _read(PKG / "RUN_VERIFICATION.md")
    return (
        "You are the HELM Auditor (independent). Verify the HELM Runtime Bridge + "
        "Dispatch Gateway against the ratified Constitution, bound to verification_target_id "
        "d8d5139a62e186bfb5e4e9fb5c7a453d2cfbe9ee79805aedec2947170eec6c64. First confirm the "
        "manifest hashes match the working tree (else stop: AUDIT_TARGET_DIVERGENCE). Then "
        "verify the 10 checks and emit a verdict per check + overall in "
        "{VERIFIED, VERIFIED_WITH_LIMITATIONS, FAILED} with evidence paths.\n\n"
        "=== BRIEF ===\n" + brief + "\n\n=== RUN_VERIFICATION ===\n" + runv
    )


def main() -> int:
    from backend.dispatch import dispatch, dispatch_enabled
    from backend.helm_runtime.dispatch_gateway import DispatchNotEnabledError

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        result = dispatch(role="auditor", capability="verification", prompt=build_prompt())
    except DispatchNotEnabledError as e:
        print(f"[fail-closed] HELM cannot fire the auditor yet: {e}")
        print("  Founder enables ONCE (not you running Grok by hand):")
        print("    1) put XAI_API_KEY in ~/.helm/helm.env")
        print("    2) set -a; . ~/.helm/helm.env; set +a; export HELM_DISPATCH_ENABLED=1")
        print("    3) re-run: python3 scripts/helm_fire_verification.py")
        return 3
    out = PKG / f"GROK_VERDICT_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "verdict.md").write_text(
        f"# Grok verdict — dispatched by HELM {ts}\n\n"
        f"provider={result.get('provider')} model={result.get('model')}\n\n"
        f"{result.get('text','')}\n", encoding="utf-8")
    print(f"HELM fired the auditor ({result.get('provider')}/{result.get('model')}). "
          f"Verdict → {out/'verdict.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
