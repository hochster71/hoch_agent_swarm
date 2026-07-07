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
    if not any(path.startswith(r) for r in WRITE_ROOTS):
        raise ValueError(f"v1 safety: writes limited to {WRITE_ROOTS}")
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {path}"


SYSTEM = (
    "You are a HOCH swarm worker agent. Complete ONE task using tools, then finish. "
    "Reply with EXACTLY ONE JSON object per turn and NOTHING else:\n"
    '  {"tool":"list_dir","path":"."}\n'
    '  {"tool":"read_file","path":"README.md"}\n'
    '  {"tool":"write_file","path":"docs/…","content":"…"}\n'
    '  {"tool":"finish","summary":"what you actually produced","artifacts":["docs/…"]}\n'
    "Rules: writes only under docs/ scratch/ artifacts/. Produce a REAL deliverable (a file), "
    "not a plan or a promise. Keep it tight and finish within a few steps."
)


def _gateway_generate(prompt: str, system: str) -> str:
    """Route through the hardened gateway (portable across Mac/relay). Falls back to a
    direct local OpenAI-compatible call if the gateway import fails."""
    try:
        from backend.model_gateway import get_gateway
        return get_gateway().generate(prompt, system=system, timeout=120)
    except Exception:
        from openai import OpenAI
        client = OpenAI(base_url=os.environ.get("AGENT_MODEL_BASE", "http://127.0.0.1:1234/v1"),
                        api_key=os.environ.get("AGENT_MODEL_KEY", "not-needed"))
        r = client.chat.completions.create(
            model=os.environ.get("AGENT_MODEL", "google/gemma-4-12b-qat"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=1500)
        return r.choices[0].message.content or ""


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

    for step in range(1, MAX_STEPS + 1):
        raw = _gateway_generate(convo, SYSTEM) or ""
        transcript.append({"step": step, "model_out": raw[:2000]})
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
    payload = {
        "task_id": tid, "task_name": tname, "task_class": tclass,
        "executed_at": _now(), "engine": "agent_executor.v1",
        "status": "SUCCESS" if ok else "INCOMPLETE",
        "summary": summary, "artifacts": sorted(set(a for a in artifacts if a)),
        "steps": len(transcript), "transcript": transcript,
    }
    ev_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "status": payload["status"],
        "summary": summary or "(no summary produced)",
        "artifacts": payload["artifacts"],
        "evidence_path": str(ev_path.relative_to(ROOT)),
        "input_hash": _sha(f"{tname}:{tclass}:{desc}"),
        "output_hash": _sha(json.dumps(payload, sort_keys=True)),
    }
