"""Council Router — HELM assigns the mission to the lane that owns it.

The founder does NOT pick a model. HELM classifies each ask into a capability,
resolves the capability → owning role → provider binding, and dispatches to that
member autonomously. For missions that need the whole brain, `orchestrate()` runs
the governed chain: Orchestrator plans → Builder solves → Auditor verifies.

Everything is fail-closed (a lane whose provider isn't enabled returns BLOCKED, never
a fake answer) and every hop is recorded on the event bus. No brand is hard-coded in
callers — routing is by capability, exactly as the Constitution requires.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.helm_runtime.capability_registry import route_capability
from backend.dispatch.live_gateway import autoload_env
from backend.dispatch.guarded_council import guarded_dispatch, guarded_ready, model_for

# --- Lane classification -------------------------------------------------------
# Capability → the ask-shapes that belong to it. First match wins; the registry
# then resolves capability → role → provider. Keep this brand-free.
# Capabilities that belong to the LOCAL brain (no frontier/cloud call). Privacy wins:
# these are checked FIRST so private data never leaves the machine, whatever the task.
LOCAL_CAPS = {"local_private"}

_LANE_SIGNALS: List[Tuple[str, List[str]]] = [
    ("local_private", [
        r"\bprivate\b", r"\bpersonal\b", r"\bconfidential", r"\bsensitive\b",
        r"\bmy (family|home|kids|health|medical|finances|financ|taxes|bank)",
        r"\bfamily\b", r"\bhousehold\b", r"\boffline\b", r"\bon[\s-]?device",
        r"\bkeep (it|this)? ?local", r"\bdon'?t send (it|this)? ?(to )?(the )?cloud",
        r"\blocal(ly)? only\b", r"\bno cloud\b", r"\bprivately\b",
    ]),
    ("verification", [
        r"\bverif", r"\baudit", r"\bred[\s-]?team", r"\badversar", r"\bregression",
        r"\bsecurity\b", r"\bpen[\s-]?test", r"\bprove\b", r"\battack\b", r"\bassur",
        r"\bcheck (that|whether|if)\b", r"\bconfirm\b", r"\bvalidate the",
    ]),
    ("architecture", [
        r"\barchitect", r"\bdesign (the|a|an) (system|api|schema|module|service)",
        r"\bedr\b", r"\bengineering decision", r"\btrade[\s-]?off",
    ]),
    ("python", [
        r"\bwrite (code|a script|a function|python|tests?|the|a|an|this)\b",
        r"\bimplement\b", r"\bcode\b", r"\brefactor",
        r"\bfix (the|a|this) (bug|test|error)", r"\bbuild (the|a|an)\b",
        r"\bpytest", r"\bunit test", r"\bwebhook", r"\bhandler\b",
        r"\bendpoint", r"\bfunction\b", r"\bscript\b", r"\bwire (up|the)\b",
    ]),
    ("planning", [
        r"\bplan\b", r"\bdecompos", r"\bsequence\b", r"\broadmap", r"\bnext (\d+ )?(steps|tasks)",
        r"\bprioriti", r"\bschedule\b", r"\bwhat should we do", r"\bhow do we (get|move)",
        r"\bstrateg", r"\bcoordinate",
    ]),
]

_LANE_HUMAN = {
    "planning": "Orchestrator lane (planning / decomposition)",
    "decomposition": "Orchestrator lane (decomposition)",
    "architecture": "Builder lane (architecture)",
    "python": "Builder lane (engineering)",
    "testing": "Builder lane (testing)",
    "verification": "Auditor lane (independent verification)",
    "red_team": "Auditor lane (red team)",
    "local_private": "Local lane (private data — never leaves the machine)",
}


def classify(prompt: str) -> Tuple[str, str]:
    """Infer the owning capability for an ask. Returns (capability, reason).

    Defaults to `planning` (Orchestrator) when nothing else matches — an unclassified
    mission is a planning problem: HELM asks the Chief of Staff to break it down.
    """
    text = (prompt or "").lower()
    for capability, patterns in _LANE_SIGNALS:
        for pat in patterns:
            if re.search(pat, text):
                return capability, f"matched lane signal /{pat}/ → {capability}"
    return "planning", "no specific lane signal; defaulting to Orchestrator planning lane"


def _resolve_lane(capability: str) -> Dict[str, Any]:
    """capability → role (via registry). Adds a human label. No provider call yet.

    LOCAL_CAPS short-circuit the registry: the local brain is a provider-lane, not a
    frontier role, so it's resolved directly to provider=local (privacy-preserving).
    """
    if capability in LOCAL_CAPS:
        return {"capability": capability, "resolved": True, "role": "local",
                "provider": "local", "all_roles": ["local"],
                "lane": _LANE_HUMAN.get(capability, capability), "reason": None}
    r = route_capability(capability)
    role = r.get("role") if r.get("resolved") else None
    return {
        "capability": capability,
        "resolved": bool(role),
        "role": role,
        "all_roles": r.get("all_roles", []),
        "lane": _LANE_HUMAN.get(capability, capability),
        "reason": r.get("reason"),
    }


_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]

_ANTI_FABRICATION = (
    "STRICT RULES — you are a HELM council lane, not a chatbot:\n"
    "• Answer ONLY from the HELM STATE below and the founder's message. Treat HELM STATE as "
    "the single source of truth.\n"
    "• Do NOT invent owners, people's names, teams, dates, companies, versions, file names, "
    "or external facts. HELM has no 'Jenna', 'Carlos', 'Release Engineer', etc. Owners are "
    "roles: orchestrator / builder / auditor / founder.\n"
    "• Reference PERT nodes by their exact id (e.g. N3_VERIFY). If something is not in HELM "
    "STATE, say 'not in state / UNKNOWN' — never fill the gap with plausible fiction.\n"
    "• Be concise. No invented tables of fake people. Grounded facts only.\n"
    # HELM-GOV | extends: council lane prompt | doctrine: Governance-before-Capability
    #          | edr: EDR-0006-R4 | why: every lane decision must be explainable + evidence-bound.
    "• GOVERNANCE: for any recommendation or decision, state (a) the authority/rule it rests on and "
    "(b) the HELM STATE evidence it derives from. If you cannot cite evidence, say UNKNOWN — "
    "unknown is preferable to unsupported certainty. Governance before capability; no fake green.\n"
)


def _ground() -> str:
    """Compact, factual HELM STATE block from the real runtime files — so lanes reason over
    facts instead of confabulating. Truncated + fail-open (missing file → omitted, never faked)."""
    import json
    parts = []
    try:
        g = json.loads((_ROOT / "coordination/goal/helm_goal.json").read_text())
        parts.append("GOAL: " + (g.get("statement", "")[:600]))
    except Exception:
        pass
    try:
        p = json.loads((_ROOT / "coordination/goal/helm_pert.json").read_text())
        legend = p.get("status_legend", {})
        rows = []
        done = tot = 0.0
        for n in p.get("nodes", []):
            st = n.get("status", "PENDING")
            w = legend.get(st, 0.0)
            done += w; tot += 1
            rows.append(f"  {n.get('id')}: {st} — {(n.get('label') or n.get('name') or '')[:60]}")
        pct = (100.0 * done / tot) if tot else 0.0
        parts.append(f"PERT NODES (status; ~{pct:.1f}% to GOAL):\n" + "\n".join(rows))
    except Exception:
        pass
    try:
        m = json.loads((_ROOT / "coordination/goal/mission_state.json").read_text())
        mis = m.get("mission", {})
        parts.append(f"ACTIVE MISSION: {mis.get('id','?')} — {(mis.get('north_star') or '')[:200]}")
    except Exception:
        pass
    # FACTORIES — the machines that ship/monetize. Health matters for any gap analysis.
    try:
        f = json.loads((_ROOT / "coordination/council/factory_registry.json").read_text()).get("factories", {})
        rows = [f"  {k}: health={v.get('health')} readiness={v.get('readiness')} — {v.get('name')}"
                for k, v in f.items()]
        ready = sum(1 for v in f.values() if v.get("readiness") == "READY")
        parts.append(f"FACTORIES ({ready}/{len(f)} READY — the rest are DEGRADED/NOT_READY and are real gaps):\n"
                     + "\n".join(rows))
    except Exception:
        pass
    # AUDIT swarm status (assurance layer).
    try:
        a = json.loads((_ROOT / "coordination/goal/audit_status.json").read_text())
        parts.append(f"AUDITS: {a.get('green',0)}/{a.get('total_controllable','?')} GREEN, state={a.get('state')} "
                     f"(controllable audits not yet green are gaps). Externally-gated: {a.get('externally_gated')}")
    except Exception:
        parts.append("AUDITS: audit swarm not run to GREEN yet (0 verified) — a gap.")
    # N3 verification honesty caveat + external milestones.
    parts.append("VERIFICATION CAVEAT: N3_VERIFY = Grok evidence-REVIEW (VERIFIED), NOT independent "
                 "re-execution; full independent re-execution / ATO is a separate (externally-gated) bar.")
    try:
        from backend.helm_executive_brief import build_executive_brief as _b
        ext = _b().get("sections", {}).get("external_milestones", {}).get("data", {})
        parts.append(f"EXTERNAL MILESTONES: release={ext.get('release')}, revenue={ext.get('revenue')} "
                     "(no verified first SETTLED dollar until revenue=SETTLED; release blocked on Apple).")
    except Exception:
        pass
    return "\n\n".join(parts) if parts else "(HELM STATE unavailable)"


def _frame(persona: str, prompt: str) -> str:
    """Wrap a lane's prompt with anti-fabrication rules + grounded HELM STATE + persona."""
    persona_line = (persona + "\n\n") if persona else ""
    return (f"{persona_line}{_ANTI_FABRICATION}\n=== HELM STATE (source of truth) ===\n"
            f"{_ground()}\n\n=== FOUNDER MESSAGE ===\n{prompt}")


# ── Constitutional Runtime: every council decision carries a Proof Record ─────────────────────
# HELM-GOV | extends: N6 dispatch emitter (_record) | doctrine: Governance-before-Capability
#          | edr: EDR-0006-R4 | why: each COUNCIL_* decision is stamped with a Proof Record via the
#          | single gate (govern_decision) so the decision is provable without log reconstruction.
#          | Council routing/dispatch is a DETERMINISTIC derivation of prompt + registry + policy —
#          | hence evidence_class=DERIVED (honest; we govern the DECISION, not the model's answer).
_GIT_COMMIT: Optional[str] = None


def _git_commit() -> str:
    global _GIT_COMMIT
    if _GIT_COMMIT is None:
        try:
            import subprocess
            _GIT_COMMIT = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(_ROOT), capture_output=True, text=True, timeout=3
            ).stdout.strip() or "UNKNOWN"
        except Exception:
            _GIT_COMMIT = "UNKNOWN"
    return _GIT_COMMIT


def _sha256(obj: Any) -> str:
    import hashlib, json as _json
    return "sha256:" + hashlib.sha256(_json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _proof_record(kind: str, payload: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """Build the Proof Record for a council decision. Fields are REAL values (no theater):
    inputs/outputs are hashed, the tested commit is read from git, and evidence_class reflects that
    the routing decision is mechanically DERIVED from HELM STATE + the capability registry."""
    inp = _sha256(payload)
    pr = {
        "authorized": {"authority": "capability_registry+gateway_policy",
                       "decision_id": correlation_id, "gate": "govern_decision"},
        "explanation": f"{kind}: {payload.get('capability') or payload.get('role') or 'council decision'}",
        "trace": {"correlation_id": correlation_id, "input_digests": [inp]},
        "proven": {"proof_command": "backend.dispatch.council_router.classify+_resolve_lane",
                   "exit_code": 0, "evidence_hash": _sha256({"kind": kind, "payload": payload})},
        "reproducibility": {"tested_commit": _git_commit(), "environment": "helm_runtime.council_router"},
        "evidence_class": "DERIVED",
    }
    pr["audit"] = {"record_hash": _sha256(pr), "prev_hash": None}
    return pr


def _record(kind: str, payload: Dict[str, Any]) -> str:
    """Publish a governed council decision. Returns its governance_state (never raises)."""
    try:
        import uuid
        from backend.helm_runtime.extensions.constitutional_gate import (
            govern_decision, publish_governed_event)

        cid = str(uuid.uuid4())
        pr = _proof_record(kind, payload, cid)
        gov = govern_decision(pr)
        pr["governance_state"] = gov.governance_state
        publish_governed_event(type=kind, producer="council_router", mission_id="COUNCIL",
                               correlation_id=cid, payload={**payload, "governance_state": gov.governance_state},
                               proof_record=pr)
        return gov.governance_state
    except Exception:
        return "UNKNOWN"  # event bus is best-effort; never block a dispatch on telemetry


def solve(prompt: str, *, hint_capability: Optional[str] = None) -> Dict[str, Any]:
    """Autonomous single-lane solve. HELM picks the lane, routes, and returns the answer.

    Never raises for a disabled lane — returns a BLOCKED status the UI can render honestly.
    """
    autoload_env()
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_prompt"}

    if hint_capability:
        capability, reason = hint_capability, f"caller hinted capability={hint_capability}"
    else:
        capability, reason = classify(prompt)
    lane = _resolve_lane(capability)
    routing = {"capability": capability, "classification_reason": reason, **lane}

    if not lane["resolved"]:
        _record("COUNCIL_ROUTE_UNRESOLVED", {"capability": capability})
        return {"ok": False, "status": "UNROUTABLE", "routing": routing,
                "message": f"No lane advertises capability {capability!r}."}

    role = lane["role"]
    gr = guarded_dispatch(role, _frame("", prompt))  # guarded gateway + grounded HELM STATE
    if not gr["ok"]:
        _record("COUNCIL_LANE_BLOCKED", {"role": role, "capability": capability,
                                         "status": gr.get("status"), "model": gr.get("model")})
        return {"ok": False, "status": gr.get("status"), "routing": routing,
                "model": gr.get("model"), "message": gr.get("message"),
                "howto": "guarded local path: ensure Ollama is running and the lane model is pulled"}
    _record("COUNCIL_SOLVED", {"role": role, "capability": capability,
                               "provider": gr.get("provider"), "model": gr.get("model"),
                               "cost": gr.get("cost", 0.0), "prompt_chars": len(prompt)})
    return {"ok": True, "status": "SOLVED", "routing": routing,
            "provider": gr.get("provider"), "model": gr.get("model"),
            "text": gr.get("text", ""), "cost": gr.get("cost"), "latency_ms": gr.get("latency_ms")}


def orchestrate(prompt: str) -> Dict[str, Any]:
    """Full-brain governed chain: Orchestrator plans → Builder solves → Auditor verifies.

    Each hop degrades honestly: if a lane's provider isn't enabled, that hop is marked
    BLOCKED and the chain continues with what IS available. HELM decides; models advise.
    """
    autoload_env()
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_prompt"}

    steps: List[Dict[str, Any]] = []

    # 1) Orchestrator plans the mission.
    plan = solve(
        f"You are the HELM Orchestrator (Chief of Staff). Decompose this mission into a "
        f"concrete ordered plan; for each step name the owning lane (builder/auditor) and "
        f"the dependency. Mission:\n\n{prompt}",
        hint_capability="planning",
    )
    steps.append({"phase": "PLAN", "lane": "Orchestrator", **plan})

    # 2) Builder solves against the plan (or the raw mission if planning was blocked).
    build_context = plan.get("text") if plan.get("ok") else prompt
    build = solve(
        f"You are the HELM Builder. Execute the engineering work for this mission. "
        f"Produce the concrete artifact (code / design / decision) the plan calls for.\n\n"
        f"Mission:\n{prompt}\n\nPlan:\n{build_context}",
        hint_capability="python",
    )
    steps.append({"phase": "BUILD", "lane": "Builder", **build})

    # 3) Auditor verifies the builder's output.
    audit_target = build.get("text") if build.get("ok") else "(no builder output — lane blocked)"
    audit = solve(
        f"You are the HELM Auditor. Independently verify the following work against the "
        f"mission. State VERIFIED / VERIFIED_WITH_LIMITATIONS / REJECTED with reasons. Do not "
        f"rubber-stamp.\n\nMission:\n{prompt}\n\nWork to verify:\n{audit_target}",
        hint_capability="verification",
    )
    steps.append({"phase": "VERIFY", "lane": "Auditor", **audit})

    enabled = [s["phase"] for s in steps if s.get("ok")]
    blocked = [s["phase"] for s in steps if not s.get("ok")]
    _record("COUNCIL_ORCHESTRATED", {"enabled": enabled, "blocked": blocked})
    return {"ok": bool(enabled), "mode": "orchestrate", "steps": steps,
            "enabled_phases": enabled, "blocked_phases": blocked}


# Each lane's owning capability + how to address it in a conversation.
_LANE_VOICE = [
    ("orchestrator", "planning",      "Orchestrator",
     "You are the HELM Orchestrator (Chief of Staff). Answer as the planner: sequence, "
     "dependencies, next moves. Be concise and conversational."),
    ("builder",      "python",         "Builder",
     "You are the HELM Builder (engineer). Answer as the one who builds it: concrete, "
     "technical, buildable. Be concise and conversational."),
    ("auditor",      "verification",   "Auditor",
     "You are the HELM Auditor (independent). Answer skeptically: what would you need to "
     "verify this, what could be wrong. Be concise and conversational."),
    ("local",        "local_private",  "Local",
     "You are the HELM Local brain (private, on-device). Answer plainly; nothing leaves "
     "the machine. Be concise and conversational."),
]


def _dispatch_member(role: str, capability: str, prompt: str) -> Dict[str, Any]:
    """Fire one member's local model through the guarded gateway, grounded in HELM STATE."""
    return guarded_dispatch(role, _frame("", prompt))


def council_chat(prompt: str, *, mode: str = "auto", history: Optional[list] = None) -> Dict[str, Any]:
    """Converse with the council in one thread.

    mode='auto'  → HELM routes to the single lane that owns the ask (default).
    mode='all'   → the whole council answers; each member speaks in its own lane voice.
    History (prior turns) is prepended so the conversation has continuity.
    """
    autoload_env()
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_prompt"}

    ctx = ""
    for turn in (history or [])[-6:]:  # last few turns for continuity
        who = turn.get("who", "Founder"); txt = (turn.get("text") or "")[:800]
        ctx += f"{who}: {txt}\n"
    framed = (ctx + f"Founder: {prompt}") if ctx else prompt

    if mode == "all":
        replies = []
        for role, cap, name, persona in _LANE_VOICE:
            r = _dispatch_member(role, cap, f"{persona}\n\n{framed}")
            replies.append({"member": name, "role": role, **r})
        answered = [x["member"] for x in replies if x["ok"]]
        _record("COUNCIL_CHAT_ALL", {"answered": answered,
                 "blocked": [x["member"] for x in replies if not x["ok"]]})
        return {"ok": bool(answered), "mode": "all", "replies": replies}

    # auto: route to the owning lane, answer in that member's voice
    res = solve(framed)
    member = None
    for role, cap, name, _ in _LANE_VOICE:
        if res.get("routing", {}).get("role") == role:
            member = name
    return {"ok": res.get("ok", False), "mode": "auto",
            "replies": [{"member": member or "HELM", "role": res.get("routing", {}).get("role"),
                         "status": res.get("status"), "ok": res.get("ok", False),
                         "provider": res.get("provider"), "model": res.get("model"),
                         "text": res.get("text"), "message": res.get("message"),
                         "routing": res.get("routing")}]}


def council_status() -> Dict[str, Any]:
    """Live per-lane readiness — the guarded local council. Each lane runs a local model
    through HELM's CouncilDispatchGateway (local-first, cost-capped, ledgered). READY when
    the gateway authorizes LOCAL_OLLAMA (Ollama installed + policy allows)."""
    gr = guarded_ready()
    ready = bool(gr.get("ready"))
    lanes = [
        ("orchestrator", "planning",      "Orchestrator", "Plans & sequences — local reasoning model"),
        ("builder",      "python",         "Builder",      "Engineers the solution — local coder model"),
        ("auditor",      "verification",   "Auditor",      "Independently verifies — local critical model"),
        ("local",        "local_private",  "Local",        "Private-data lane — general local model, on-device"),
    ]
    from backend.dispatch.guarded_council import provider_for
    members = []
    for role, cap, name, mandate in lanes:
        prov = provider_for(role)
        members.append({
            "role": role, "provider": f"{prov}·guarded", "owns_capability": cap,
            "display_name": name, "mandate": mandate, "model": model_for(role),
            "ready": ready, "status": "READY" if ready else "BLOCKED_EXTERNAL",
        })
    return {"schema": "HELM_COUNCIL_STATUS_v1", "members": members,
            "ready_count": sum(1 for m in members if m["ready"]), "total": len(members),
            "guarded": True, "reason": gr.get("reason"),
            "note": "guarded local dispatch via CouncilDispatchGateway — local-first, cost-capped, ledgered"}


# ── AUTONOMOUS CROSS-MODEL SCORING ───────────────────────────────────────────
# One task in → HELM fans it to every lane/model, collects each answer, then the
# Auditor lane scores them all against HELM doctrine + real runtime state.
# No founder paste-in required: this is the autonomous path (GOAL: autonomy).

_SCORE_RUBRIC = """HELM COUNCIL — CROSS-MODEL RESPONSE SCORING (autonomous run)

You are the HELM Auditor. Score the responses below against HELM doctrine. Do NOT rewrite
the answers — score them.

ORIGINAL TASK THEY ANSWERED:
@@TASK@@

RESPONSES TO SCORE:
@@BLOCKS@@

SCORING RULES (binding):
1. Score each response on the 7 axes, 0-5 each (35 max -> report as /100).
2. Every score needs a one-line justification CITING SPECIFIC TEXT from that response.
   A score without a cited reason is invalid — mark it UNSCORED rather than guessing.
3. Verify claims against the real HELM STATE given to you above. A confident claim that
   contradicts that state scores 0 on Evidence Fidelity AND Grounding Accuracy —
   confidence is not credit.
4. SELF-SCORING CONFLICT: if a response came from your own model, mark that row
   "SELF-SCORED — DISCOUNT" and say so plainly.
5. If you cannot verify something, write UNKNOWN. Never invent a file path, metric,
   person, or command output to justify a score.

THE 7 AXES (0-5 each):
1 EVIDENCE FIDELITY      0=claims with no traceable artifact | 5=every claim ties to a real path/output
2 NO-FAKE-GREEN          0=asserts DONE/green without proof  | 5=honest UNKNOWN/PARTIAL/BLOCKED_EXTERNAL, separates controllable vs externally-gated
3 GROUNDING ACCURACY     0=invents state                     | 5=matches real PERT nodes, factories, audits, milestones
4 ACTIONABILITY          0=plan-shaped prose                 | 5=runnable script/command/file, drives to the founder's last click
5 GOVERNANCE COMPLIANCE  0=breaks frozen target/gates/secrets| 5=respects frozen target, EDR path, founder gates, guarded dispatch, no plaintext secrets
6 REASONING QUALITY      0=hand-waves, misses root cause     | 5=correct causal chain, real root cause, states its own uncertainty
7 LANE / COST FIT        0=frontier burned on trivial/private| 5=right lane (local for private data, frontier only where justified)

REQUIRED OUTPUT — exactly these five sections:
1. SCORECARD — table: model x 7 axes x total /100, one-line verdict each.
2. RANKING — best to worst, with the single deciding factor for each position.
3. DISAGREEMENTS — every material contradiction between the models. Who said what, and
   WHICH ONE THE ARTIFACTS SUPPORT. If unsettled: UNRESOLVED + the evidence that would settle it.
4. SYNTHESIS — the best combined answer from the strongest VERIFIED parts, citing source model per part.
5. RECOMMENDED ACTION — the single next step for HELM, with its founder gate named (if any).

VERDICT BANDS: 90-100 AUTHORITATIVE | 75-89 SOUND | 60-74 USABLE_WITH_CORRECTIONS |
40-59 WEAK | <40 REJECT. Fabrication or a governance breach = automatic REJECT regardless of total.
"""


def score_council(task: str, *, responses: Optional[Dict[str, str]] = None,
                  timeout: int = 420) -> Dict[str, Any]:
    """Autonomous cross-model scoring.

    responses=None  → HELM fans `task` to EVERY lane now, collects each model's answer,
                      then scores them (fully autonomous; no paste-in).
    responses={...} → score supplied answers instead (e.g. pasted ChatGPT 5.6 output),
                      keyed by model name.
    """
    autoload_env()
    task = (task or "").strip()
    if not task:
        return {"ok": False, "error": "empty_task"}

    collected: List[Dict[str, Any]] = []
    if responses:
        for name, text in responses.items():
            collected.append({"member": name, "role": "supplied", "ok": True,
                              "text": (text or ""), "model": name})
    else:
        for role, cap, name, persona in _LANE_VOICE:
            r = _dispatch_member(role, cap, f"{persona}\n\n{task}")
            collected.append({"member": name, "role": role, **r})

    answered = [c for c in collected if c.get("ok") and (c.get("text") or "").strip()]
    if not answered:
        return {"ok": False, "error": "no_responses", "responses": collected,
                "note": "every lane blocked or empty — nothing to score (no fake green)"}

    blocks = "\n\n".join(
        f"### {c.get('member')}  (lane={c.get('role','?')}, model={c.get('model','?')})\n"
        f"{(c.get('text') or '')[:6000]}"
        for c in answered
    )
    brief = _SCORE_RUBRIC.replace("@@TASK@@", task[:2500]).replace("@@BLOCKS@@", blocks)

    # The Auditor lane owns assurance by design (Grok per role_bindings).
    verdict = guarded_dispatch("auditor", _frame("", brief), pert_node="COUNCIL_SCORE",
                               timeout=timeout)

    out = {
        "ok": bool(verdict.get("ok")),
        "task": task,
        "scored_count": len(answered),
        "models": [{"member": c.get("member"), "role": c.get("role"),
                    "model": c.get("model"), "ok": bool(c.get("ok")),
                    "chars": len((c.get("text") or ""))} for c in collected],
        "responses": collected,
        "scorecard": verdict.get("text") or "",
        "scorer": {"lane": "auditor", "model": verdict.get("model"),
                   "provider": verdict.get("provider")},
        "autonomous": responses is None,
    }
    if not verdict.get("ok"):
        out["error"] = verdict.get("error") or verdict.get("blocked") or "auditor_blocked"
        out["note"] = "responses collected but scoring blocked — reported honestly, not faked"

    _record("COUNCIL_SCORE", {
        "task": task[:300], "scored": [c.get("member") for c in answered],
        "scorer_model": verdict.get("model"), "ok": bool(verdict.get("ok")),
        "autonomous": responses is None,
    })
    return out
