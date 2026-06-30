import json
import time
import uuid
import re
import logging
import concurrent.futures
from pathlib import Path
from backend.runtime_execution_store import (
    now_iso,
    list_model_providers_db,
    get_model_provider_db,
    get_service_node_leases,
    persist_multi_model_run_db
)
from backend.inference_gateway import (
    scan_for_secrets,
    get_hash,
    send_openai_compatible_chat,
    send_ollama_chat,
    send_lm_studio_chat,
    send_localai_chat
)

logger = logging.getLogger("MultiModelOrchestrator")

def compute_jaccard_similarity(text1: str, text2: str) -> float:
    # Tokenize: find word characters and lowercase them
    words1 = set(re.findall(r"\w+", text1.lower()))
    words2 = set(re.findall(r"\w+", text2.lower()))
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    return len(words1.intersection(words2)) / len(words1.union(words2))

def evaluate_consensus(responses: list[dict]) -> dict:
    """
    Takes a list of model responses:
    [
        {"model_provider_id": "...", "content": "...", "latency_ms": ..., "status": "success"},
        ...
    ]
    Returns:
    {
        "consensus_response": str,
        "consensus_agreement_score": float,
        "dissenters": list[dict],
        "individual_similarities": dict
    }
    """
    successful = [r for r in responses if r.get("status") == "success"]
    if not successful:
        return {
            "consensus_response": "Error: All model providers failed during swarm reasoning execution.",
            "consensus_agreement_score": 0.0,
            "dissenters": [],
            "individual_similarities": {}
        }
        
    if len(successful) == 1:
        return {
            "consensus_response": successful[0]["content"],
            "consensus_agreement_score": 1.0,
            "dissenters": [],
            "individual_similarities": {successful[0]["model_provider_id"]: 1.0}
        }
        
    # Calculate pairwise similarities
    n = len(successful)
    sims = {}
    for i in range(n):
        for j in range(i, n):
            p1 = successful[i]["model_provider_id"]
            p2 = successful[j]["model_provider_id"]
            if i == j:
                s = 1.0
            else:
                s = compute_jaccard_similarity(successful[i]["content"], successful[j]["content"])
            sims[(p1, p2)] = s
            sims[(p2, p1)] = s
            
    # Compute average similarity for each response to all others
    avg_sims = {}
    for i in range(n):
        p1 = successful[i]["model_provider_id"]
        total_s = 0.0
        for j in range(n):
            p2 = successful[j]["model_provider_id"]
            total_s += sims[(p1, p2)]
        avg_sims[p1] = total_s / n
        
    # Consensus is the one with highest average similarity to all others
    consensus_provider_id = max(avg_sims, key=avg_sims.get)
    consensus_idx = next(idx for idx, r in enumerate(successful) if r["model_provider_id"] == consensus_provider_id)
    consensus_response = successful[consensus_idx]["content"]
    
    # Consensus agreement score is the average of all pairwise similarities
    pairwise_sum = 0.0
    pair_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            p1 = successful[i]["model_provider_id"]
            p2 = successful[j]["model_provider_id"]
            pairwise_sum += sims[(p1, p2)]
            pair_count += 1
    consensus_agreement_score = (pairwise_sum / pair_count) if pair_count > 0 else 1.0
    
    # Identify dissenters: similarity to consensus response is < 0.5
    dissenters = []
    for r in successful:
        p_id = r["model_provider_id"]
        sim_to_consensus = sims[(p_id, consensus_provider_id)]
        if sim_to_consensus < 0.5:
            dissenters.append({
                "model_provider_id": p_id,
                "content": r["content"],
                "similarity_to_consensus": sim_to_consensus
            })
            
    return {
        "consensus_response": consensus_response,
        "consensus_agreement_score": consensus_agreement_score,
        "dissenters": dissenters,
        "individual_similarities": avg_sims
    }

def execute_single_inference(provider: dict, model_id: str, messages: list[dict], options: dict) -> dict:
    start_time = time.perf_counter()
    p_id = provider["model_provider_id"]
    try:
        ptype = provider.get("provider_type", "openai_compatible")
        if ptype == "ollama":
            res = send_ollama_chat(provider, model_id, messages, options)
        elif ptype == "lm_studio":
            res = send_lm_studio_chat(provider, model_id, messages, options)
        elif ptype == "localai":
            res = send_localai_chat(provider, model_id, messages, options)
        else:
            res = send_openai_compatible_chat(provider, model_id, messages, options)
            
        latency = (time.perf_counter() - start_time) * 1000.0
        return {
            "model_provider_id": p_id,
            "model_id": model_id,
            "status": "success",
            "content": res["content"],
            "latency_ms": latency,
            "token_usage": res.get("usage", {}),
            "error_message": None
        }
    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000.0
        return {
            "model_provider_id": p_id,
            "model_id": model_id,
            "status": "failed",
            "content": f"Error: {e}",
            "latency_ms": latency,
            "token_usage": {},
            "error_message": str(e)
        }

def execute_multi_model_inference(
    prompt: str,
    provider_ids: list[str] = None,
    options: dict = None
) -> dict:
    """
    Dispatches parallel chat completions across selected/eligible approved model providers.
    """
    if options is None:
        options = {}
        
    messages = [{"role": "user", "content": prompt}]
    has_secrets = scan_for_secrets(messages)
    
    # 1. Fetch and resolve model providers
    all_providers = list_model_providers_db()
    leases = {l["node_id"]: l for l in get_service_node_leases()}
    
    selected_providers = []
    for p in all_providers:
        # If explicit list is provided, filter by it
        if provider_ids is not None:
            if p["model_provider_id"] not in provider_ids:
                continue
        
        # Invariants check
        if not p["approved_for_inference"]:
            continue
        if p["health_status"] not in ["available", "degraded"]:
            continue
            
        # Device lease check
        if p["node_id"]:
            lease = leases.get(p["node_id"])
            if not lease:
                continue
            if lease["availability"] in ["sleeping", "offline"]:
                continue
                
        selected_providers.append(p)
        
    if not selected_providers:
        raise ValueError("No eligible, approved, and healthy model providers found matching the request criteria.")
        
    # 2. Sensitive Context / Safety validation
    if has_secrets:
        untrusted = [p["model_provider_id"] for p in selected_providers if not p.get("trusted_for_sensitive_context")]
        if untrusted:
            raise ValueError(f"Inference request blocked: Prompt contains secrets but these selected providers are untrusted for sensitive context: {untrusted}")
            
    # 3. Dispatch Parallel Queries
    results = []
    created_at = now_iso()
    start_all = time.perf_counter()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_providers)) as executor:
        futures = {}
        for p in selected_providers:
            model_id = p.get("default_model") or "gemma-4-12b"
            futures[executor.submit(execute_single_inference, p, model_id, messages, options)] = p
            
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            
    latency_all = (time.perf_counter() - start_all) * 1000.0
    completed_at = now_iso()
    
    # 4. Evaluate Consensus
    consensus = evaluate_consensus(results)
    
    # 5. Persist to Database & Log Evidence
    run_id = f"MM-{uuid.uuid4().hex[:6].upper()}"
    prompt_hash = get_hash(prompt)
    
    run_data = {
        "multi_model_run_id": run_id,
        "prompt_hash": prompt_hash,
        "consensus_agreement_score": consensus["consensus_agreement_score"],
        "consensus_response_preview": consensus["consensus_response"][:100],
        "status": "success" if any(r["status"] == "success" for r in results) else "failed",
        "created_at": created_at,
        "completed_at": completed_at,
        "latency_ms": latency_all,
        "metadata": {
            "options": options,
            "responses": results,
            "consensus_agreement_score": consensus["consensus_agreement_score"],
            "dissenters": consensus["dissenters"],
            "individual_similarities": consensus["individual_similarities"]
        }
    }
    
    evidence_path = write_multi_model_evidence(run_id, run_data)
    run_data["evidence_path"] = evidence_path
    
    persist_multi_model_run_db(run_id, run_data)
    
    return {
        "multi_model_run_id": run_id,
        "status": run_data["status"],
        "consensus_response": consensus["consensus_response"],
        "consensus_agreement_score": consensus["consensus_agreement_score"],
        "dissenters": consensus["dissenters"],
        "responses": results,
        "latency_ms": latency_all,
        "evidence_path": evidence_path
    }

def write_multi_model_evidence(run_id: str, data: dict) -> str:
    from backend.runtime_paths import optional_ag_scratch_root
    workspace_root = optional_ag_scratch_root()
    evidence_dir = workspace_root / "artifacts" / "multi_model"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    evidence_path = evidence_dir / f"{run_id}.json"
    
    # Redact prompts/responses from permanent JSON logs to keep zero secrets leakage
    evidence_data = {
        "multi_model_run_id": run_id,
        "prompt_hash": data.get("prompt_hash"),
        "consensus_agreement_score": data.get("consensus_agreement_score"),
        "status": data.get("status"),
        "created_at": data.get("created_at"),
        "completed_at": data.get("completed_at"),
        "latency_ms": data.get("latency_ms"),
        "model_feed": [
            {
                "model_provider_id": r["model_provider_id"],
                "model_id": r["model_id"],
                "status": r["status"],
                "latency_ms": r["latency_ms"],
                "error_message": r["error_message"]
            } for r in data.get("metadata", {}).get("responses", [])
        ],
        "consensus_dissenters": [
            {
                "model_provider_id": d["model_provider_id"],
                "similarity_to_consensus": d["similarity_to_consensus"]
            } for d in data.get("metadata", {}).get("dissenters", [])
        ]
    }
    
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2)
        
    return str(evidence_path)
