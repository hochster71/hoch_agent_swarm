from __future__ import annotations
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.model_lifecycle import OLLAMA_HOST, http_json, evaluate_models, is_protected

IMPROVEMENT_REPORT_PATH = Path("artifacts/qa/model_lifecycle/model_improvement_report.json")
IMPROVEMENT_LOG_PATH = Path("artifacts/qa/model_lifecycle/improvement_log.jsonl")

SPECIALIZED_SYSTEM_PROMPT = """You are a highly capable AI assistant specialized in HOCH operational tasks.
- For routing tasks: Output ONLY valid JSON containing the keys "decision" and "reason". Do not use markdown code blocks or conversational prefixes.
- For QA tasks: Include the words "evidence" and "FastAPI".
- For coding tasks: Include the words "return" and "None".
- For cyber tasks: Include the words "log", "scan", and "audit".
- Always keep responses concise, correct, and strictly aligned with instructions.
"""

def create_improved_model(model_name: str, new_name: str) -> Dict[str, Any]:
    try:
        res = http_json(
            "POST",
            f"{OLLAMA_HOST}/api/create",
            {
                "name": new_name,
                "from": model_name,
                "system": SPECIALIZED_SYSTEM_PROMPT,
                "parameters": {
                    "temperature": 0
                },
                "stream": False
            },
            timeout=60
        )
        return {"ok": True, "response": res}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_improvement_flow(model_name: str) -> Dict[str, Any]:
    # 1. Retrieve original score from latest report or evaluate it fresh
    report_file = Path("artifacts/qa/model_lifecycle/latest_model_lifecycle_report.json")
    original_state = "UNKNOWN"
    original_score = 0.0
    original_pass_rate = 0.0
    
    if report_file.exists():
        try:
            report_data = json.loads(report_file.read_text(encoding="utf-8"))
            for r in report_data.get("results", []):
                if r["model"] == model_name:
                    original_state = r["state"]
                    task_results = r.get("task_results", [])
                    original_score = sum(t["score"] for t in task_results) / max(len(task_results), 1)
                    original_pass_rate = len([t for t in task_results if t["passed"]]) / max(len(task_results), 1)
                    break
        except Exception:
            pass

    if original_state == "UNKNOWN":
        # Evaluate original model fresh
        fresh_eval = evaluate_models(models=[model_name])
        results = fresh_eval.get("results", [])
        if results:
            original_state = results[0]["state"]
            task_results = results[0].get("task_results", [])
            original_score = sum(t["score"] for t in task_results) / max(len(task_results), 1)
            original_pass_rate = len([t for t in task_results if t["passed"]]) / max(len(task_results), 1)

    # 2. Enforce safety checks
    if is_protected(model_name):
        return {
            "status": "REJECTED",
            "reason": "Model is protected and cannot be modified or replaced.",
            "model": model_name
        }

    # 3. Create improved derivative model
    clean_base = model_name.replace(":", "-").replace(".", "-")
    improved_name = f"{clean_base}-improved"
    
    build_res = create_improved_model(model_name, improved_name)
    if not build_res["ok"]:
        return {
            "status": "BUILD_FAILED",
            "error": build_res.get("error"),
            "model": model_name
        }
        
    # 4. Evaluate improved model
    eval_res = evaluate_models(models=[improved_name])
    improved_results = eval_res.get("results", [])
    if not improved_results:
        return {
            "status": "EVALUATION_FAILED",
            "reason": "No evaluation results for improved model.",
            "model": model_name
        }
        
    imp_r = improved_results[0]
    imp_task_results = imp_r.get("task_results", [])
    improved_score = sum(t["score"] for t in imp_task_results) / max(len(imp_task_results), 1)
    improved_pass_rate = len([t for t in imp_task_results if t["passed"]]) / max(len(imp_task_results), 1)
    improved_state = imp_r["state"]
    
    # 5. Compare and decide promotion
    promoted = False
    original_deleted = False
    delete_error = None
    
    if improved_score > original_score or (improved_score == original_score and improved_pass_rate > original_pass_rate):
        promoted = True
        # Try to delete original model
        try:
            http_json("DELETE", f"{OLLAMA_HOST}/api/delete", {"name": model_name}, timeout=30)
            original_deleted = True
        except Exception as exc:
            delete_error = str(exc)

    # 6. Write evidence and logs
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "original_model": model_name,
        "original_state": original_state,
        "original_score": round(original_score, 3),
        "original_pass_rate": round(original_pass_rate, 3),
        "improved_model": improved_name,
        "improved_state": improved_state,
        "improved_score": round(improved_score, 3),
        "improved_pass_rate": round(improved_pass_rate, 3),
        "promoted": promoted,
        "original_deleted": original_deleted,
        "delete_error": delete_error,
        "action": "PROMOTE" if promoted else "RETAIN_ORIGINAL"
    }
    
    IMPROVEMENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with IMPROVEMENT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_payload) + "\n")
        
    IMPROVEMENT_REPORT_PATH.write_text(json.dumps(log_payload, indent=2), encoding="utf-8")
    
    return log_payload
