"""Guarded EXECUTE Builder lane — Claude (Opus) that actually builds inside HELM.

Runs the `claude` CLI (Claude Code) through HELM's CouncilDispatchGateway, so the same
guardrails that cover every model apply here too: frontier grant, cost cap, ledger,
local_only environment. On top of the gateway, this module adds SAFE-AUTONOMY rails for
write access:

  • plan (default) is READ-ONLY — Claude analyzes and proposes, edits nothing.
  • execute is APPROVED-ONLY — the caller must pass mode='execute' explicitly.
  • snapshot-before-mutate — a recoverable patch of the working tree is saved first.
  • frozen-target guard — the 17 bound audit files must stay byte-intact; if execute
    touches any, they are reverted and the build is reported FAILED (fail-closed).
  • irreversible actions stay founder-gated — the doctrine prompt forbids deploy / publish /
    git push / money, and `acceptEdits` permission mode auto-accepts file EDITS only (it does
    not auto-run shell), so the lane cannot autonomously ship or spend.

Nothing here bypasses a gate; it composes on top of them. Founder-gated until CLI_CLAUDE is
granted (helm_enable_claude_lane.sh).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
_MANIFEST = ROOT / "docs/evidence/audit/bridge_verification/verification_manifest.json"
_SNAP_DIR = ROOT / "recovered_sources" / "build_snapshots"


def _frozen_hashes() -> Dict[str, str]:
    try:
        return json.loads(_MANIFEST.read_text()).get("expected_hashes", {})
    except Exception:
        return {}


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _frozen_changed() -> List[str]:
    """Which frozen-target files (if any) currently diverge from their bound hash."""
    return [f for f, h in _frozen_hashes().items() if _sha(ROOT / f) != h]


def _snapshot() -> str:
    """Save a recoverable patch of the current working tree before any mutation.
    Returns the snapshot path (or a note). Never disturbs the tree."""
    _SNAP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    patch = _SNAP_DIR / f"pre_build_{ts}.patch"
    try:
        diff = subprocess.run(["git", "diff", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=60).stdout
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=30).stdout.strip()
        patch.write_text(f"# HELM build snapshot {ts}\n# HEAD {head}\n# restore working tree: "
                         f"git apply -R {patch.name}\n{diff}")
        return str(patch.relative_to(ROOT))
    except Exception as e:
        return f"snapshot_unavailable: {str(e)[:120]}"


def _revert_frozen(files: List[str]) -> None:
    """Restore frozen-target files to their committed bytes (fail-closed rollback)."""
    for f in files:
        try:
            subprocess.run(["git", "checkout", "--", f], cwd=ROOT, timeout=30)
        except Exception:
            pass


_DOCTRINE = (
    "You are the HELM Builder — Claude (Opus) — working INSIDE the HELM repo at {root}.\n"
    "SAFE-AUTONOMY RULES (hard, non-negotiable):\n"
    "1. Work only within this repo. NEVER touch ~/.ssh, Keychain, /System, /Library, browser "
    "profiles, ~/.helm, or any secret/credential file.\n"
    "2. NEVER edit the frozen verification-target files (must stay byte-intact): {frozen}.\n"
    "3. Do NOT deploy, publish, git push, submit to any store, or move money — those are "
    "FOUNDER-gated. Make code/file changes only; leave irreversible external actions for the "
    "founder and say what you'd hand off.\n"
    "4. Snapshot exists; if you are unsure or a change is risky, STOP and explain instead of "
    "guessing. Prefer the narrowest change that works.\n"
    "5. When done, summarize exactly what you changed (files + why) so it can be reviewed.\n"
)


def _framed(task: str) -> str:
    from backend.dispatch.council_router import _ground  # grounded HELM STATE (no cycle)
    frozen = ", ".join(list(_frozen_hashes().keys())[:6]) + " …(17 files)"
    doctrine = _DOCTRINE.format(root=str(ROOT), frozen=frozen)
    return (f"{doctrine}\n=== HELM STATE (source of truth) ===\n{_ground()}\n\n"
            f"=== BUILD TASK ===\n{task}")


def build(task: str, *, mode: str = "plan", pert_node: str = "COUNCIL",
          timeout: int = 900) -> Dict[str, Any]:
    """Dispatch the Claude Builder lane to plan (read-only) or execute (approved) a build.

    mode='plan'   → claude --permission-mode plan (analyzes, edits nothing). DEFAULT.
    mode='execute'→ claude --permission-mode acceptEdits (auto-accepts file EDITS only),
                    with snapshot-before + frozen-target guard + rollback.
    """
    from scripts.council.gateway import GatewayRequest, DispatchType
    from backend.dispatch.guarded_council import _gateway

    task = (task or "").strip()
    if not task:
        return {"ok": False, "status": "EMPTY_TASK"}
    mode = mode.lower()
    if mode not in ("plan", "execute"):
        mode = "plan"

    import os
    os.environ.pop("ANTHROPIC_API_KEY", None)  # Builder uses the flat Max plan, not API billing
    framed = _framed(task)
    perm = "plan" if mode == "plan" else "acceptEdits"
    argv = ["claude", "-p", framed, "--permission-mode", perm, "--add-dir", str(ROOT)]

    snapshot = None
    if mode == "execute":
        snapshot = _snapshot()  # recoverable undo before any write

    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    req = GatewayRequest(
        task_id=f"COUNCIL-BUILD-{mode.upper()}-{ts}",
        pert_node=pert_node,
        caller_identity="helm_council_ui",
        dispatch_type=DispatchType.CLI_CLAUDE,
        prompt=framed,
        argv=argv,
        scope="read-only" if mode == "plan" else "execute",
        environment="local_only",
        frontier_required=True,
        frontier_justification=f"Founder-approved guarded Builder lane ({mode})",
        per_task_cap_usd=1.00,          # builds are bigger than chat; still well under monthly cap
        timeout_seconds=timeout,
        cwd=str(ROOT),
        metadata={"lane": "builder", "mode": mode, "model": "claude-opus"},
    )
    try:
        r = _gateway().dispatch(req)
    except Exception as e:
        return {"ok": False, "status": "GATEWAY_ERROR", "mode": mode, "message": str(e)[:300],
                "snapshot": snapshot}

    out = {"mode": mode, "status": r.status, "decision": r.decision_status,
           "cost": r.estimated_cost, "text": (r.output or "").strip(),
           "blocks": r.blocks, "snapshot": snapshot, "dispatch_id": r.dispatch_id}

    if not (r.status == "COMPLETED" and r.decision_status == "ALLOWED"):
        reason = ", ".join(r.blocks) if r.blocks else (r.stderr or "").strip()[:200] or r.status
        return {"ok": False, "message": reason, **out}

    if mode == "execute":
        changed_frozen = _frozen_changed()
        if changed_frozen:
            _revert_frozen(changed_frozen)              # fail-closed: protect the audit invariant
            out["frozen_violation"] = changed_frozen
            out["ok"] = False
            out["status"] = "ROLLED_BACK"
            out["message"] = (f"Build touched frozen audit target ({', '.join(changed_frozen)}) — "
                              f"reverted those files. Change rejected to preserve the pending audit.")
            _record_build(out)
            return out
        out["frozen_intact"] = True
    out["ok"] = True
    _record_build(out)
    return out


def _record_build(out: Dict[str, Any]) -> None:
    try:
        # HELM-GOV | extends: N6 emitter (guarded_build) | edr: EDR-0006-R4 | why: a build decision
        #          | is a material decision — it must carry a Proof Record via the single gate.
        from backend.helm_runtime.governed_emit import emit_governed
        emit_governed(type="COUNCIL_BUILD", producer="builder", mission_id="COUNCIL",
                      authority="guarded_build:builder_lane",
                      explanation=f"build {out.get('mode')} -> {out.get('status')}",
                      inputs={"mode": out.get("mode"), "status": out.get("status"),
                              "frozen_violation": bool(out.get("frozen_violation"))},
                      proof_command="backend.dispatch.guarded_build (guarded execute)",
                      environment="guarded_build",
                      payload={"mode": out.get("mode"), "status": out.get("status"),
                               "cost": out.get("cost", 0.0),
                               "frozen_violation": bool(out.get("frozen_violation"))})
    except Exception:
        pass
