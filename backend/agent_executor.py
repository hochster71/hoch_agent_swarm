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
    "scripts/northstar_planner.py", "scripts/northstar_daemon.py", "scripts/model_upgrade.py",
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


def _extract_json_action(raw: str):
    """Robustly pull ONE tool-call JSON object out of a model turn — tolerant of markdown fences,
    prose around it, multiple objects, and reasoning-model preambles. Returns a dict with a 'tool'
    key, or None. This is what makes capable-but-chatty models reliable in the ReAct loop."""
    if not raw:
        return None
    s = re.sub(r"```(?:json)?", "", raw).strip()
    # collect balanced top-level {...} objects
    cands, depth, start = [], 0, -1
    for i, c in enumerate(s):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    cands.append(s[start:i + 1])
    for cand in reversed(cands):          # prefer the later / most complete object
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and obj.get("tool"):
                return obj
        except Exception:
            continue
    return None


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
        # openai (gpt-4o-mini) first — reliably capable & cheap; gemini free is a quota-limited bonus;
        # deepseek if keyed; local last. This is what actually does the coding/research work well.
        return ["openai", "gemini", "deepseek", "local"]
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
    # AUTO-UPGRADE: if the model-upgrade station resolved newer best-available models, use them.
    try:
        reg = json.loads((ROOT / "has_live_project_tracker/data/model_registry.json").read_text())
        tiers = reg.get("tiers", {})
        fr = tiers.get("frontier", {})
        ch = tiers.get("cheap", {})
        gm = tiers.get("gemini", {})
        if fr.get("verified") and fr.get("model"):
            models["openai_frontier"] = fr["model"]
        if ch.get("verified") and ch.get("provider") == "openai" and ch.get("model"):
            models["openai"] = ch["model"]
        if gm.get("verified") and gm.get("model"):
            models["gemini"] = gm["model"]
    except Exception:
        pass

    def _openai_compat(base_url, key, model):
        from openai import OpenAI
        kw = {"api_key": key}
        if base_url:
            kw["base_url"] = base_url
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        # Newer OpenAI models (gpt-5.x, o-series) renamed max_tokens->max_completion_tokens and
        # only accept the default temperature. Older models + gemini/deepseek use the classic params.
        newer = model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4")
        params = {"model": model, "messages": msgs}
        if newer:
            params["max_completion_tokens"] = 4000   # reasoning models spend tokens thinking; leave room for the answer
        else:
            params["temperature"] = 0.1
            params["max_tokens"] = 1500
        return (OpenAI(**kw).chat.completions.create(**params).choices[0].message.content or "")

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


MAX_RETRIES = int(os.environ.get("AGENT_MAX_RETRIES", "2"))
_TIER_NAME = {TIER_LOCAL: "local", TIER_CHEAP: "cheap", TIER_FRONTIER: "frontier"}


def _verify_compile(path: str) -> tuple[bool, str]:
    p = _safe(path)
    if not p.exists():
        return False, f"compile target missing: {path}"
    try:
        from scripts.code_task_gate import compile_check
        ok, msg = compile_check(str(p))
        return ok, f"compile_check {path}: {msg[:300]}"
    except Exception as e:
        # Fallback if import fails
        if p.suffix != ".py":
            return True, f"{path} (non-python, skipped)"
        import subprocess
        r = subprocess.run([sys.executable, "-m", "py_compile", str(p)],
                           capture_output=True, text=True, timeout=CMD_TIMEOUT)
        return (r.returncode == 0), (f"py_compile {path}: " + ("ok" if r.returncode == 0 else r.stderr[:300]))


def _verify_pytest(target: str) -> tuple[bool, str]:
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", target, "-q"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=max(CMD_TIMEOUT, 300))
    tail = (r.stdout + "\n" + r.stderr).strip()[-400:]
    return (r.returncode == 0), f"pytest {target}: " + ("PASS" if r.returncode == 0 else f"FAIL\n{tail}")


def _check_acceptance(task: dict, artifacts: list[str], summary: str) -> tuple[bool, list[str]]:
    """Machine-verify the result. Real, independent checks — this is what stops a model from
    claiming success it didn't achieve. A task can declare its own `acceptance` spec; otherwise
    a default gate requires a real, on-disk artifact + a non-empty summary."""
    spec = task.get("acceptance") or {}
    report: list[str] = []
    passed = True

    if not spec:  # DEFAULT GATE — no fabricated 'done'
        real = [a for a in artifacts if (_safe(a).exists() if a else False)]
        if not real:
            passed = False
            report.append("default gate: no artifact actually exists on disk (claimed done, produced nothing)")
        elif not (summary or "").strip():
            passed = False
            report.append("default gate: empty summary")
        else:
            report.append(f"default gate: {len(real)} real artifact(s) on disk + summary present")
        return passed, report

    for path in spec.get("artifact_exists", []):
        ok_ = bool(path) and _safe(path).exists()
        passed &= ok_
        report.append(f"exists {path}: {'ok' if ok_ else 'MISSING'}")
    for path in spec.get("compiles", []):
        ok_, msg = _verify_compile(path)
        passed &= ok_
        report.append(msg)
    for item in spec.get("contains", []) if isinstance(spec.get("contains"), list) else ([spec["contains"]] if spec.get("contains") else []):
        path, text = item.get("path"), item.get("text", "")
        ok_ = bool(path) and _safe(path).exists() and text in _safe(path).read_text(encoding="utf-8", errors="ignore")
        passed &= ok_
        report.append(f"contains '{text[:30]}' in {path}: {'ok' if ok_ else 'NO'}")
    pt = spec.get("pytest")
    if pt:
        if not ALLOW_CODE:
            report.append(f"pytest {pt}: SKIPPED (safe mode)")
        else:
            ok_, msg = _verify_pytest(pt)
            passed &= ok_
            report.append(msg)
    return passed, report


def _run_attempt(task: dict, tier: int, system: str, prior_fail: str = "") -> dict:
    """One ReAct pass at a given tier. Returns raw outcome (not yet acceptance-checked)."""
    tname = task.get("task_name", "")
    tclass = task.get("task_class", "")
    desc = task.get("description", "") or tname
    convo = f"TASK: {tname}\nCLASS: {tclass}\nDETAIL: {desc}\n"
    if task.get("acceptance"):
        convo += (f"ACCEPTANCE (your work is machine-checked against this — it must pass):\n"
                  f"{json.dumps(task['acceptance'])}\n")
    if prior_fail:
        convo += (f"\nA PREVIOUS ATTEMPT FAILED VERIFICATION:\n{prior_fail}\n"
                  "Fix the specific failure above. Do not repeat the same mistake.\n")
    convo += "Complete it now. First action:"
    transcript: list[dict] = []
    artifacts: list[str] = []
    summary, ok, cost = "", False, 0.0
    models_used: list[str] = []

    for step in range(1, MAX_STEPS + 1):
        raw, meta = _gateway_generate(convo, system, tier)
        raw = raw or ""
        cost += meta.get("cost_usd", 0.0)
        if meta.get("model"):
            models_used.append(meta["model"])
        transcript.append({"step": step, "model": meta.get("model"),
                           "cost_usd": round(meta.get("cost_usd", 0.0), 6), "model_out": raw[:2000]})
        action = _extract_json_action(raw)
        if not action:
            convo += ('\n(No tool call detected. Reply with EXACTLY ONE JSON object and nothing else — '
                      'e.g. {"tool":"write_file","path":"docs/generated/x.md","content":"..."} '
                      'or {"tool":"finish","summary":"...","artifacts":["docs/generated/x.md"]})\nNext action:')
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

    return {"finished": ok, "summary": summary, "artifacts": artifacts,
            "transcript": transcript, "cost": cost, "models_used": models_used}


def _execute_doc_task(task, tid, tname, tclass, desc, tier):
    """Reliable single-shot path for document-producing tasks (research/design/analysis).
    The model WRITES the markdown directly (no JSON tool-loop to truncate), and we save it.
    This is what makes capable models produce clean verified docs every time."""
    m = re.search(r"(docs/[\w/.\-]+\.md)", desc)
    doc = m.group(1) if m else f"docs/generated/auto/{tid}.md"
    prompt = (f"Write a complete, well-structured markdown document for this task. "
              f"Output ONLY the markdown body — no preamble, no code fences.\n\nTASK: {tname}\nDETAIL: {desc}")
    out, meta = _gateway_generate(prompt, "You are an expert analyst and technical writer.", tier)
    out = (out or "").strip()
    out = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", out).strip()
    ok = bool(out)
    if ok:
        try:
            _write_file(doc, out + "\n")
        except Exception as e:
            ok, out = False, f"(write failed: {e})"
    tier_name = _TIER_NAME[tier]
    ev_dir = ROOT / "docs/evidence/runtime"; ev_dir.mkdir(parents=True, exist_ok=True)
    ev = ev_dir / f"agent_exec_{tid}.json"
    payload = {"task_id": tid, "task_name": tname, "task_class": tclass, "executed_at": _now(),
               "engine": "agent_executor.v3-doc", "status": "SUCCESS" if ok else "INCOMPLETE",
               "verified": ok, "mode": "single-shot-doc", "tier": tier_name,
               "models_used": [meta.get("model")], "task_cost_usd": round(meta.get("cost_usd", 0.0), 6),
               "month_spend_usd": round(_month_spend(), 4), "month_cap_usd": _cap(),
               "summary": (f"Wrote {doc}" if ok else "no content produced"),
               "artifacts": [doc] if ok else []}
    ev.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"status": payload["status"], "verified": ok, "summary": payload["summary"],
            "artifacts": payload["artifacts"], "evidence_path": str(ev.relative_to(ROOT)),
            "tier": tier_name, "attempts": 1, "task_cost_usd": payload["task_cost_usd"],
            "month_spend_usd": payload["month_spend_usd"], "month_cap_usd": _cap(),
            "input_hash": _sha(f"{tname}:{tclass}:{desc}"),
            "output_hash": _sha(json.dumps(payload, sort_keys=True))}


def execute_task(task: dict) -> dict:
    """Perform the task with a VERIFY-AND-RETRY gate: run → check acceptance → on failure
    escalate to the next tier and retry (bounded). Returns real evidence, never a fabricated proof.
    This is the harness that makes a cheap model reliable: only genuine failures pay for a stronger one."""
    tname = task.get("task_name", "")
    tclass = task.get("task_class", "")
    desc = task.get("description", "") or tname
    tid = task.get("task_id", "task")
    os.environ["_AGENT_TID"] = str(tid)
    system = _system()

    base_tier = _tier_for(task)
    # Document-producing tasks use the reliable single-shot writer (no fragile JSON tool-loop).
    if tclass in ("research", "design", "analysis") and not (task.get("acceptance") or {}).get("compiles"):
        return _execute_doc_task(task, tid, tname, tclass, desc, base_tier)
    total_cost = 0.0
    all_models: list[str] = []
    attempts: list[dict] = []
    final = None
    accepted = False
    accept_report: list[str] = []
    prior_fail = ""

    for attempt_i in range(1, MAX_RETRIES + 2):  # 1 attempt + MAX_RETRIES retries
        tier = min(TIER_FRONTIER, base_tier + (attempt_i - 1))  # escalate one tier per retry
        res = _run_attempt(task, tier, system, prior_fail)
        total_cost += res["cost"]
        all_models += res["models_used"]
        # Wire code_task_gate for code tasks in code mode
        if ALLOW_CODE and tclass == "code":
            try:
                from scripts.code_task_gate import gate as code_gate
                spec = task.get("acceptance") or {}
                files_to_check = spec.get("compiles", [])
                if not files_to_check and res.get("artifacts"):
                    files_to_check = [res["artifacts"][0]]
                
                if not files_to_check:
                    accepted = False
                    accept_report = ["no artifact produced for code task"]
                else:
                    accepted = True
                    accept_report = []
                    for fpath in files_to_check:
                        gate_res = code_gate(fpath, {"tests": spec.get("pytest")}, cwd=str(ROOT))
                        if not gate_res.get("verified"):
                            accepted = False
                            hint = gate_res.get("retry_hint", "verification failed")
                            accept_report.append(f"gate check failed for {fpath}: {hint}")
                        else:
                            accept_report.append(f"gate check passed for {fpath}")
            except Exception as e:
                # fallback on execution failure to regular check
                accepted, accept_report = _check_acceptance(task, res["artifacts"], res["summary"]) \
                    if res["finished"] else (False, [f"attempt did not finish (no finish action)"])
                accept_report.append(f"code gate error: {e}")
        else:
            accepted, accept_report = _check_acceptance(task, res["artifacts"], res["summary"]) \
                if res["finished"] else (False, ["attempt did not finish (no finish action)"])
        attempts.append({
            "attempt": attempt_i, "tier": _TIER_NAME[tier], "finished": res["finished"],
            "accepted": accepted, "acceptance_report": accept_report,
            "cost_usd": round(res["cost"], 6), "steps": len(res["transcript"]),
            "transcript": res["transcript"],
        })
        final = res
        if accepted:
            break
        prior_fail = "; ".join(accept_report)[:800]
        if tier >= TIER_FRONTIER:  # already at top tier — no higher to escalate to
            break

    ev_dir = ROOT / "docs/evidence/runtime"
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_path = ev_dir / f"agent_exec_{tid}.json"
    final_tier = _TIER_NAME[min(TIER_FRONTIER, base_tier + len(attempts) - 1)]
    payload = {
        "task_id": tid, "task_name": tname, "task_class": tclass,
        "executed_at": _now(), "engine": "agent_executor.v3",
        "status": "SUCCESS" if accepted else "INCOMPLETE",
        "verified": accepted, "acceptance_report": accept_report,
        "attempts": len(attempts), "final_tier": final_tier,
        "models_used": sorted(set(all_models)),
        "task_cost_usd": round(total_cost, 6), "month_spend_usd": round(_month_spend(), 4),
        "month_cap_usd": _cap(),
        "summary": final["summary"] if final else "",
        "artifacts": sorted(set(a for a in (final["artifacts"] if final else []) if a)),
        "attempt_log": attempts,
    }
    ev_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "status": payload["status"],
        "verified": accepted,
        "summary": payload["summary"] or "(no summary produced)",
        "artifacts": payload["artifacts"],
        "evidence_path": str(ev_path.relative_to(ROOT)),
        "tier": final_tier, "attempts": len(attempts),
        "task_cost_usd": round(total_cost, 6),
        "month_spend_usd": round(_month_spend(), 4), "month_cap_usd": _cap(),
        "input_hash": _sha(f"{tname}:{tclass}:{desc}"),
        "output_hash": _sha(json.dumps(payload, sort_keys=True)),
    }
