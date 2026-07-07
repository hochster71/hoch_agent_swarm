"""Real tool-using agent executor — the ENGINE the swarm was missing.

For the whole session the runner's "execute" step was a stub that wrote a fabricated
proof ("Generated code structure blueprints…") and DID nothing. This replaces it with an
actual agent that performs the task using tools, then returns REAL evidence (a full
transcript + real artifacts + real hashes).

Design:
  - Model-pluggable via the hardened model_gateway → auto-routes to whatever backend is
    alive (LM Studio / Ollama / relay). $0 and no external key required to start; upgrades
    to Claude/GPT automatically once provider keys are provisioned (R1).
  - ReAct loop: the model emits ONE JSON tool action per turn; we execute it and feed back
    the observation. Works with any text model (no function-calling API required).

Safety (v1 — deliberately bounded because this runs unattended):
  - Repo-scoped file tools only. NO arbitrary shell.
  - Writes restricted to docs/ , scratch/ , artifacts/ .
  - Bounded step count. Every step recorded as real evidence.
  - Genuinely unsafe / founder-gated tasks never reach here — DOORSTEP + the runner's
    policy gate stop them first.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "10"))
WRITE_ROOTS = ("docs/", "scratch/", "artifacts/")
MAX_OBS = 1500

# v2 code mode is OPT-IN. Default (unset) = safe file-only mode so the unattended daemon can
# never edit code or run shell. Set AGENT_ALLOW_CODE=1 to enable guarded code edits + shell.
ALLOW_CODE = os.environ.get("AGENT_ALLOW_CODE") == "1"
CMD_TIMEOUT = int(os.environ.get("AGENT_CMD_TIMEOUT", "120"))

# The agent may NEVER write these, even in code mode — control plane, secrets, the change-control
# guard, the runner/daemon that invoke it, and git internals. Protects the system from itself.
DENY_WRITE = (
    "scripts/baseline_guard.py", "scripts/ag_execution_daemon.py",
    "scripts/ag_execution_runner.py", "backend/agent_executor.py",
    "has_live_project_tracker/data/orchestration_bridge_control.json",
    "has_live_project_tracker/data/baseline_tag.txt", "has_live_project_tracker/data/ag_execution_policy.json",
    ".env", ".git/", ".secrets/", "config/", ".gitignore",
)
# First token allowlist for run_command. Read-only / test / lint only. git and python are
# further restricted below to safe subcommands. Anything else is refused.
_CMD_ALLOW = {"ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "echo", "true",
              "ruff", "pytest", "node", "npm", "diff", "sort", "uniq"}

# ─────────────────────────────────────────────────────────────────────────────
# COST GOVERNOR — three-tier difficulty router + hard monthly spend cap.
# Tier 0 (LOCAL)    : Ollama on the Mac. $0. Default for analysis / verify / docs.
# Tier 1 (CHEAP)    : DeepSeek / Gemini Flash — pennies/task. Default for code.
# Tier 2 (FRONTIER) : GPT-5.4 — dollars/task. Only for tasks flagged hard / escalated.
# The cap is FAIL-CLOSED: once the month's paid spend hits AGENT_MONTHLY_CAP_USD, every
# paid tier is disabled and work silently downgrades to the $0 local brain. It can never
# overspend unattended. Set the cap to 0 to forbid ALL paid calls (pure local/free).
# ─────────────────────────────────────────────────────────────────────────────
TIER_LOCAL, TIER_CHEAP, TIER_FRONTIER = 0, 1, 2
SPEND_LEDGER = ROOT / "has_live_project_tracker/data/spend_ledger.jsonl"


def _cap() -> float:
    """Monthly paid-spend ceiling in USD. 0 = forbid ALL paid calls (pure local/free).
    Read live (after _load_env) so .env or the shell can change it without a restart."""
    try:
        return float(os.environ.get("AGENT_MONTHLY_CAP_USD", "100"))
    except ValueError:
        return 100.0

# (input, output) USD per 1,000,000 tokens — July 2026 list prices. Local = free.
PRICING = {
    "local": (0.0, 0.0),
    "gemini-2.5-flash": (0.15, 0.60), "gemini-2.0-flash": (0.10, 0.40),
    "gemini-3.1-flash-lite": (0.10, 0.40),
    "deepseek-chat": (0.14, 0.28), "deepseek-reasoner": (0.55, 2.19),
    "gpt-4o-mini": (0.15, 0.60), "gpt-5-mini": (0.25, 2.00),
    "gpt-5.4": (2.50, 15.0), "gpt-4o": (2.50, 10.0),
    "grok-2-latest": (2.00, 10.0),
}


def _est_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def _price_of(model: str) -> tuple[float, float]:
    return PRICING.get(model, (0.0, 0.0))


def _is_paid(model: str) -> bool:
    return _price_of(model) != (0.0, 0.0)


def _month_key() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def _month_spend() -> float:
    if not SPEND_LEDGER.exists():
        return 0.0
    mk, tot = _month_key(), 0.0
    for line in SPEND_LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            r = json.loads(line)
            if r.get("month") == mk:
                tot += float(r.get("cost_usd", 0.0))
        except Exception:
            pass
    return tot


def _record_spend(model: str, in_tok: int, out_tok: int, cost: float, tid: str) -> None:
    SPEND_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(SPEND_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _now(), "month": _month_key(), "task_id": tid, "model": model,
            "in_tok": in_tok, "out_tok": out_tok, "cost_usd": round(cost, 6),
        }) + "\n")


def _cost_of(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = _price_of(model)
    return in_tok / 1_000_000 * pin + out_tok / 1_000_000 * pout


def _tier_for(task: dict) -> int:
    """Route by declared difficulty. Escalation (set by a retry) forces frontier."""
    if task.get("escalated") or task.get("hard") or task.get("difficulty") == "hard":
        return TIER_FRONTIER
    diff = (task.get("difficulty") or "").lower()
    tclass = (task.get("task_class") or "").lower()
    if diff == "medium" or tclass in ("code",):
        return TIER_CHEAP
    return TIER_LOCAL  # analysis / verify / docs / research run free by default


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _safe(path: str) -> Path:
    p = (ROOT / path).resolve()
    if p != ROOT and ROOT not in p.parents:
        raise ValueError(f"path escapes repo: {path}")
    return p


def _read_file(path: str) -> str:
    p = _safe(path)
    return p.read_text(encoding="utf-8", errors="ignore")[:8000] if p.exists() else f"(missing: {path})"


def _list_dir(path: str = ".") -> str:
    p = _safe(path)
    if not p.is_dir():
        return "(not a directory)"
    return "\n".join(sorted((x.name + ("/" if x.is_dir() else "")) for x in list(p.iterdir())[:200]))


def _write_file(path: str, content: str) -> str:
    if any(path == d.rstrip("/") or path.startswith(d) for d in DENY_WRITE):
        raise ValueError(f"protected path refused (control-plane/secrets/guard): {path}")
    if not ALLOW_CODE and not any(path.startswith(r) for r in WRITE_ROOTS):
        raise ValueError(f"safe mode: writes limited to {WRITE_ROOTS} (set AGENT_ALLOW_CODE=1 for code)")
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {path}"


def _run_command(cmd: str) -> str:
    """Guarded shell — only in code mode, only allowlisted read-only/test/lint commands,
    no chaining/redirect/subshell. Never commits or mutates git/secrets/control-plane."""
    if not ALLOW_CODE:
        return "run_command disabled in safe mode (AGENT_ALLOW_CODE=1 to enable)."
    if any(ch in cmd for ch in ("|", ">", "<", "&", ";", "`", "\n")) or "$(" in cmd or "&&" in cmd or "||" in cmd:
        return "refused: shell metacharacters / chaining / redirection are not allowed."
    parts = cmd.split()
    if not parts:
        return "empty command."
    head = parts[0]
    if head in ("python", "python3", ".venv/bin/python", ".venv/bin/python3"):
        if not (len(parts) >= 3 and parts[1] == "-m" and parts[2] in ("py_compile", "pytest")):
            return "refused: python only permitted as '-m py_compile' or '-m pytest'."
    elif head == "git":
        if len(parts) < 2 or parts[1] not in ("status", "diff", "log", "show", "ls-files", "rev-parse", "branch"):
            return "refused: only read-only git subcommands (status/diff/log/show/ls-files) allowed."
    elif head not in _CMD_ALLOW:
        return f"refused: '{head}' is not in the command allowlist."
    import subprocess
    try:
        r = subprocess.run(parts, cwd=str(ROOT), capture_output=True, text=True, timeout=CMD_TIMEOUT)
        out = (r.stdout + ("\n" + r.stderr if r.stderr else ""))[:MAX_OBS]
        return out or f"(exit {r.returncode}, no output)"
    except Exception as e:
        return f"command error: {e}"


def _system() -> str:
    s = ("You are a HOCH swarm worker agent. Complete ONE task using tools, then finish. "
         "Reply with EXACTLY ONE JSON object per turn and NOTHING else:\n"
         '  {"tool":"list_dir","path":"."}\n'
         '  {"tool":"read_file","path":"README.md"}\n'
         '  {"tool":"write_file","path":"...","content":"..."}\n'
         '  {"tool":"finish","summary":"what you actually produced","artifacts":["..."]}\n')
    if ALLOW_CODE:
        s += ('  {"tool":"run_command","command":"pytest tests/..."}\n'
              "CODE MODE: you may write source files and run ALLOWLISTED commands only "
              "(pytest, python -m py_compile, ruff, git status/diff/log, ls/cat/grep/find). "
              "ALWAYS verify your edits compile / pass tests before you finish. You may NOT write "
              "secrets, config/, .env, the control plane, or the guard/daemon/runner; those are refused.\n")
    else:
        s += "Rules: writes only under docs/ scratch/ artifacts/.\n"
    s += "Produce a REAL deliverable (a file / a verified change), not a plan or a promise. "
    s += "Keep it tight and finish within a few steps."
    return s


def _load_env() -> None:
    """Load provider keys from .env into the process env (the loop/runner run as their own
    processes and don't inherit the shell's .env)."""
    envf = ROOT / ".env"
    if not envf.exists():
        return
    for line in envf.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            _KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
                     "GEMINI_API_KEY", "XAI_API_KEY", "DEEPSEEK_API_KEY")
            # provider keys + any AGENT_* config (cap, model overrides, brain force) from .env
            if (k in _KEYS or k.startswith("AGENT_")) and not os.environ.get(k):
                os.environ[k] = v


def _order_for_tier(tier: int) -> list[str]:
    """Candidate brains for a difficulty tier, cheapest-capable first. Within a tier we still
    fall through on error. Anthropic is NEVER auto-selected (its Console is extra money the
    founder opted out of); use AGENT_BRAIN=anthropic to force it."""
    forced = os.environ.get("AGENT_BRAIN", "").lower()
    if forced in ("gemini", "deepseek", "openai", "openai_frontier", "xai", "anthropic", "local"):
        return [forced]
    if tier >= TIER_FRONTIER:
        return ["openai_frontier", "deepseek", "gemini", "local"]
    if tier == TIER_CHEAP:
        return ["deepseek", "gemini", "openai", "local"]
    return ["local", "gemini"]  # tier 0: free local first, free-tier Gemini as backstop


def _gateway_generate(prompt: str, system: str, tier: int = TIER_LOCAL) -> tuple[str, dict]:
    """Tier-routed brain call with a fail-closed monthly cost cap.
    Returns (text, meta) where meta = {model, cost_usd, in_tok, out_tok}. Paid tiers are
    skipped once the month's spend reaches MONTHLY_CAP_USD — work then runs on the $0 local brain."""
    _load_env()
    keys = {
        "gemini": os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"),
        "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "openai_frontier": os.environ.get("OPENAI_API_KEY"),
        "xai": os.environ.get("XAI_API_KEY"),
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "local": "local",
    }
    models = {
        "gemini": os.environ.get("AGENT_GEMINI_MODEL", "gemini-2.5-flash"),
        "deepseek": os.environ.get("AGENT_DEEPSEEK_MODEL", "deepseek-chat"),
        "openai": os.environ.get("AGENT_OPENAI_MODEL", "gpt-4o-mini"),
        "openai_frontier": os.environ.get("AGENT_OPENAI_FRONTIER_MODEL", "gpt-5.4"),
        "xai": os.environ.get("AGENT_XAI_MODEL", "grok-2-latest"),
        "anthropic": os.environ.get("AGENT_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        "local": "local",
    }

    def _openai_compat(base_url, key, model):
        from openai import OpenAI
        kw = {"api_key": key}
        if base_url:
            kw["base_url"] = base_url
        return (OpenAI(**kw).chat.completions.create(
            model=model, temperature=0.1, max_tokens=1500,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        ).choices[0].message.content or "")

    def _call(name):
        m = models[name]
        if name == "gemini":
            return _openai_compat("https://generativelanguage.googleapis.com/v1beta/openai/", keys[name], m)
        if name == "deepseek":
            return _openai_compat("https://api.deepseek.com", keys[name], m)
        if name == "xai":
            return _openai_compat("https://api.x.ai/v1", keys[name], m)
        if name in ("openai", "openai_frontier"):
            return _openai_compat(None, keys[name], m)
        if name == "anthropic":
            import anthropic
            r = anthropic.Anthropic(api_key=keys[name]).messages.create(
                model=m, max_tokens=1500, system=system, messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in r.content if getattr(b, "type", None) == "text")
        raise RuntimeError("no direct call for local")

    in_tok = _est_tokens(system) + _est_tokens(prompt)
    spent = _month_spend()
    cap = _cap()
    for name in _order_for_tier(tier):
        if name == "local":
            try:
                from backend.model_gateway import get_gateway
                out = get_gateway().generate(prompt, system=system, timeout=120)
                if out:
                    return out, {"model": "local", "cost_usd": 0.0, "in_tok": in_tok,
                                 "out_tok": _est_tokens(out)}
            except Exception:
                pass
            continue
        if not keys.get(name):
            continue
        model = models[name]
        # FAIL-CLOSED CAP: never start a paid call that could exceed the month's budget.
        if _is_paid(model) and (cap <= 0 or spent >= cap):
            print(f"[cost-cap] month spend ${spent:.2f} ≥ cap ${cap:.2f} — "
                  f"skipping paid {name}, downgrading to local", flush=True)
            continue
        try:
            out = _call(name)
            if out:
                out_tok = _est_tokens(out)
                cost = _cost_of(model, in_tok, out_tok)
                if cost > 0:
                    _record_spend(model, in_tok, out_tok, cost, os.environ.get("_AGENT_TID", "?"))
                return out, {"model": model, "cost_usd": cost, "in_tok": in_tok, "out_tok": out_tok}
        except Exception as e:
            print(f"[agent_executor] {name} failed ({str(e)[:90]}); next brain", flush=True)
    return "", {"model": "none", "cost_usd": 0.0, "in_tok": in_tok, "out_tok": 0}


def execute_task(task: dict) -> dict:
    """Actually perform the task. Returns real evidence — never a fabricated proof."""
    tname = task.get("task_name", "")
    tclass = task.get("task_class", "")
    desc = task.get("description", "") or tname
    tid = task.get("task_id", "task")

    convo = f"TASK: {tname}\nCLASS: {tclass}\nDETAIL: {desc}\nComplete it now. First action:"
    transcript: list[dict] = []
    artifacts: list[str] = []
    summary = ""
    ok = False
    _system_prompt = _system()
    tier = _tier_for(task)
    os.environ["_AGENT_TID"] = str(tid)
    task_cost = 0.0
    models_used: list[str] = []

    for step in range(1, MAX_STEPS + 1):
        raw, meta = _gateway_generate(convo, _system_prompt, tier)
        raw = raw or ""
        task_cost += meta.get("cost_usd", 0.0)
        if meta.get("model"):
            models_used.append(meta["model"])
        transcript.append({"step": step, "model": meta.get("model"),
                           "cost_usd": round(meta.get("cost_usd", 0.0), 6), "model_out": raw[:2000]})
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            convo += "\n(assistant gave no JSON)\nRespond with ONE JSON tool object:"
            continue
        try:
            action = json.loads(m.group(0))
        except Exception:
            convo += "\n(invalid JSON)\nRespond with ONE valid JSON tool object:"
            continue
        tool = action.get("tool")
        try:
            if tool == "read_file":
                obs = _read_file(action["path"])
            elif tool == "list_dir":
                obs = _list_dir(action.get("path", "."))
            elif tool == "write_file":
                obs = _write_file(action["path"], action.get("content", ""))
                artifacts.append(action["path"])
            elif tool == "run_command":
                obs = _run_command(action.get("command", ""))
            elif tool == "finish":
                summary = action.get("summary", "")
                artifacts += [a for a in action.get("artifacts", []) if a]
                ok = True
                break
            else:
                obs = f"unknown tool: {tool}"
        except Exception as e:
            obs = f"tool error: {e}"
        transcript.append({"step": step, "tool": tool, "observation": obs[:MAX_OBS]})
        convo += f"\nACTION: {json.dumps(action)[:400]}\nOBSERVATION: {obs[:MAX_OBS]}\nNext action:"

    ev_dir = ROOT / "docs/evidence/runtime"
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_path = ev_dir / f"agent_exec_{tid}.json"
    tier_name = {TIER_LOCAL: "local", TIER_CHEAP: "cheap", TIER_FRONTIER: "frontier"}[tier]
    payload = {
        "task_id": tid, "task_name": tname, "task_class": tclass,
        "executed_at": _now(), "engine": "agent_executor.v2",
        "status": "SUCCESS" if ok else "INCOMPLETE",
        "tier": tier_name, "models_used": sorted(set(models_used)),
        "task_cost_usd": round(task_cost, 6), "month_spend_usd": round(_month_spend(), 4),
        "month_cap_usd": _cap(),
        "summary": summary, "artifacts": sorted(set(a for a in artifacts if a)),
        "steps": len(transcript), "transcript": transcript,
    }
    ev_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "status": payload["status"],
        "summary": summary or "(no summary produced)",
        "artifacts": payload["artifacts"],
        "evidence_path": str(ev_path.relative_to(ROOT)),
        "tier": tier_name, "task_cost_usd": round(task_cost, 6),
        "month_spend_usd": round(_month_spend(), 4), "month_cap_usd": _cap(),
        "input_hash": _sha(f"{tname}:{tclass}:{desc}"),
        "output_hash": _sha(json.dumps(payload, sort_keys=True)),
    }
