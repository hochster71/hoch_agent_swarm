from __future__ import annotations
import hashlib
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

OLLAMA_HOST = "http://10.0.0.241:11434"
REPORT_PATH = Path("artifacts/qa/model_lifecycle/latest_model_lifecycle_report.json")
QUARANTINE_PATH = Path("artifacts/qa/model_lifecycle/model_quarantine.json")
DELETE_CANDIDATES_PATH = Path("artifacts/qa/model_lifecycle/delete_candidates.json")
DELETE_LOG_PATH = Path("artifacts/qa/model_lifecycle/delete_log.jsonl")

PROTECTED_PATTERNS = [
    "nomic-embed",
    "embed",
    "hasf-router",
    "hasf-master",
    "hasf-memory",
    "hasf-policy",
    "hasf-evidence",
]

TASKS = [
    {
        "id": "json_router",
        "category": "routing",
        "prompt": "Return ONLY valid JSON with keys decision and reason. Decide whether this task is coding, cyber, qa, or general: 'Run SAST and explain failures'.",
        "required": ['"decision"', '"reason"'],
        "forbidden": ["```", "Here is", "I think"],
        "max_seconds": 20,
    },
    {
        "id": "qa_audit",
        "category": "qa",
        "prompt": "You are QA Auditor. Produce exactly 5 concise checks for validating a FastAPI endpoint. Include the word evidence once.",
        "required": ["evidence", "FastAPI"],
        "forbidden": ["as an ai", "cannot"],
        "max_seconds": 35,
    },
    {
        "id": "debug_reasoning",
        "category": "coding",
        "prompt": "A Python function returns None because a branch has no return statement. Give the likely bug and one fix in under 80 words.",
        "required": ["return", "None"],
        "forbidden": ["maybe quantum", "impossible"],
        "max_seconds": 35,
    },
    {
        "id": "cyber_conmon",
        "category": "cyber",
        "prompt": "Give 4 evidence artifacts for continuous monitoring of an AI agent runtime. Keep it concise.",
        "required": ["log", "scan", "audit"],
        "forbidden": ["ignore security", "disable"],
        "max_seconds": 35,
    },
]

def now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def http_json(method: str, url: str, payload: Optional[dict] = None, timeout: int = 45) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read(20_000_000)
        return json.loads(raw.decode("utf-8", "ignore"))

def list_ollama_models() -> List[str]:
    data = http_json("GET", f"{OLLAMA_HOST}/api/tags", timeout=10)
    models = []
    for item in data.get("models", []):
        name = item.get("name") or item.get("model")
        if name:
            models.append(str(name))
    return sorted(set(models))

def is_protected(model: str) -> bool:
    m = model.lower()
    return any(p in m for p in PROTECTED_PATTERNS)

def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

def run_model(model: str, prompt: str, timeout: int) -> Dict[str, Any]:
    started = time.time()
    try:
        data = http_json(
            "POST",
            f"{OLLAMA_HOST}/api/generate",
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 256,
                },
            },
            timeout=timeout,
        )
        elapsed = time.time() - started
        return {
            "ok": True,
            "latency_seconds": round(elapsed, 3),
            "response": str(data.get("response", "")),
            "error": None,
        }
    except Exception as exc:
        elapsed = time.time() - started
        return {
            "ok": False,
            "latency_seconds": round(elapsed, 3),
            "response": "",
            "error": str(exc),
        }

def score_response(task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    text = result.get("response", "")
    low = text.lower()
    required = task.get("required", [])
    forbidden = task.get("forbidden", [])
    req_hits = [r for r in required if r.lower() in low]
    forb_hits = [f for f in forbidden if f.lower() in low]
    valid_json = True
    if task["id"] == "json_router":
        try:
            parsed = json.loads(text)
            valid_json = isinstance(parsed, dict) and "decision" in parsed and "reason" in parsed
        except Exception:
            valid_json = False
    score = 0.0
    if result.get("ok"):
        score += 0.25
    if required:
        score += 0.45 * (len(req_hits) / len(required))
    else:
        score += 0.45
    if not forb_hits:
        score += 0.15
    if result.get("latency_seconds", 999) <= task.get("max_seconds", 35):
        score += 0.10
    if task["id"] == "json_router" and valid_json:
        score += 0.05
    elif task["id"] != "json_router":
        score += 0.05
    passed = score >= 0.75 and result.get("ok") and not forb_hits and (task["id"] != "json_router" or valid_json)
    return {
        "task_id": task["id"],
        "category": task["category"],
        "passed": passed,
        "score": round(score, 3),
        "required_hits": req_hits,
        "forbidden_hits": forb_hits,
        "valid_json": valid_json,
        "latency_seconds": result.get("latency_seconds"),
        "error": result.get("error"),
        "prompt_hash": prompt_hash(task["prompt"]),
        "response_excerpt": text[:500],
    }

def classify_model(model: str, task_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if is_protected(model):
        return {
            "state": "PROTECTED",
            "reason": "Protected dependency or embedding/router/policy/memory model.",
        }
    total = len(task_results)
    passed = len([r for r in task_results if r["passed"]])
    avg = sum(r["score"] for r in task_results) / max(total, 1)
    pass_rate = passed / max(total, 1)
    if pass_rate >= 0.80 and avg >= 0.80:
        return {"state": "PASS", "reason": f"pass_rate={pass_rate:.2f}, avg={avg:.2f}"}
    if pass_rate >= 0.50 or avg >= 0.60:
        return {"state": "TRAINABLE", "reason": f"Near miss: pass_rate={pass_rate:.2f}, avg={avg:.2f}"}
    return {"state": "QUARANTINE", "reason": f"Failed threshold: pass_rate={pass_rate:.2f}, avg={avg:.2f}"}

def evaluate_models(limit: int = 999, models: Optional[List[str]] = None) -> Dict[str, Any]:
    if models is None:
        models = list_ollama_models()
    models = models[:limit]
    results = []
    for model in models:
        if is_protected(model):
            task_results = []
            state = "PROTECTED"
            reason = "Protected dependency or embedding/router/policy/memory model."
        else:
            task_results = []
            for task in TASKS:
                raw = run_model(model, task["prompt"], task.get("max_seconds", 35) + 10)
                task_results.append(score_response(task, raw))
            cls = classify_model(model, task_results)
            state = cls["state"]
            reason = cls["reason"]
        results.append({
            "model": model,
            "state": state,
            "reason": reason,
            "protected": is_protected(model),
            "task_results": task_results,
        })
    quarantine = [r for r in results if r["state"] == "QUARANTINE"]
    trainable = [r for r in results if r["state"] == "TRAINABLE"]
    passed = [r for r in results if r["state"] in {"PASS", "PROTECTED"}]
    payload = {
        "schema": "hoch.model_lifecycle.v1",
        "generated_at": now_z(),
        "ollama_host": OLLAMA_HOST,
        "policy": {
            "delete_requires": "QUARANTINE plus explicit operator approval.",
            "protected_patterns": PROTECTED_PATTERNS,
            "test_count": len(TASKS),
        },
        "summary": {
            "tested": len(results),
            "pass_or_protected": len(passed),
            "trainable": len(trainable),
            "quarantine": len(quarantine),
        },
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    QUARANTINE_PATH.write_text(json.dumps({
        "generated_at": now_z(),
        "models": [{"model": r["model"], "reason": r["reason"]} for r in quarantine],
    }, indent=2), encoding="utf-8")
    DELETE_CANDIDATES_PATH.write_text(json.dumps({
        "generated_at": now_z(),
        "requires_operator_approval": True,
        "models": [{"model": r["model"], "reason": r["reason"]} for r in quarantine],
    }, indent=2), encoding="utf-8")
    return payload

def delete_model(model: str, approval: str) -> Dict[str, Any]:
    if approval != f"DELETE {model}":
        return {
            "truth": "REJECTED",
            "reason": f"Approval phrase must be exactly: DELETE {model}",
            "model": model,
            "deleted": False,
        }
    if is_protected(model):
        return {
            "truth": "REJECTED",
            "reason": "Protected model cannot be deleted by lifecycle gate.",
            "model": model,
            "deleted": False,
        }
    if not DELETE_CANDIDATES_PATH.exists():
        return {
            "truth": "REJECTED",
            "reason": "No delete candidate file exists. Run evaluation first.",
            "model": model,
            "deleted": False,
        }
    candidates = json.loads(DELETE_CANDIDATES_PATH.read_text(encoding="utf-8"))
    candidate_names = {m["model"] for m in candidates.get("models", [])}
    if model not in candidate_names:
        return {
            "truth": "REJECTED",
            "reason": "Model is not in delete candidates.",
            "model": model,
            "deleted": False,
        }
    try:
        http_json("DELETE", f"{OLLAMA_HOST}/api/delete", {"name": model}, timeout=30)
        out = {
            "truth": "DELETED",
            "model": model,
            "deleted": True,
            "deleted_at": now_z(),
        }
    except Exception as exc:
        out = {
            "truth": "DELETE_FAILED",
            "model": model,
            "deleted": False,
            "error": str(exc),
            "deleted_at": now_z(),
        }
    DELETE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DELETE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(out) + "\n")
    return out
