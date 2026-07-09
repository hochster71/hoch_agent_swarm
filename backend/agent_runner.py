import os
import sys
import json
import logging
import urllib.request
import urllib.error

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentRunner")

class AgentRunner:
    def __init__(self, ollama_url=None, default_model=None):
        # 127.0.0.1 explicitly: "localhost" resolves to ::1 on this host, hitting a second,
        # divergent Ollama daemon whose store rejects generate for several models (verified
        # 2026-07-06). The IPv4 daemon is the healthy one.
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        # Default model must be one that actually generates on this host (llama3 and
        # llama3.1:8b fail here — verified 2026-07-06). Env-overridable, honestly failing.
        self.default_model = default_model or os.environ.get("HOCH_DEFAULT_MODEL", "llama3.2:3b")
        logger.info(f"Initialized agent runner pointing to Ollama at: {self.ollama_url}")

    def query_ollama(self, prompt: str, system_prompt: str = None, model: str = None) -> str:
        """Route through ModelGateway — automatic failover across all live backends.
        MODEL_OFFLINE never acceptable: relay-001 is the always-on $0 backstop.
        Sources: binadit.com/tutorials/load-balancer-multiple-ollama-instances (2026-04),
                 localaimaster.com/blog/ollama-load-balancing (2026-04)
        """
        try:
            from backend.model_gateway import get_gateway
            gw = get_gateway()
            st = gw.status()
            logger.info(f"Gateway routing → '{st['primary']}' "
                        f"({st['alive_count']}/{len(st['backends'])} backends alive)")
            return gw.generate(prompt, system=system_prompt, model=model,
                               timeout=300)
        except Exception as e:
            logger.error(f"ModelGateway error: {e}")
            raise RuntimeError(f"MODEL_GATEWAY_ERROR: {e}") from e

    def execute_task(self, task_id: str, prompt: str, system_prompt: str = None, model: str = None, timeout_sec: float = 300.0,
                     task_class: str = None, domain: str = "software"):
        logger.info(f"Executing task {task_id} with TTL {timeout_sec}s...")

        # BRAIN wiring (2026-07-06): when a task_class is given and no explicit system
        # prompt overrides it, resolve the CURRENT champion for that class and ledger the
        # usage. Explicit system_prompt always wins (callers keep full control). Every
        # resolution — champion or fallback — is recorded in the runtime usage ledger.
        usage_id = None
        if task_class:
            try:
                from backend.factory.champion_loader import operating_prompt
                from backend.factory.runtime_ledger import record_usage
                res = operating_prompt(task_class, domain=domain, fallback=system_prompt)
                applied = res["source"] == "champion" and not system_prompt
                if applied:
                    system_prompt = res["prompt"]
                elif res["source"] == "champion":
                    # Ledger integrity: a resolved-but-overridden champion is NOT champion usage.
                    res = {**res, "source": "champion_overridden_by_explicit_system_prompt",
                           "prompt": system_prompt or ""}
                usage_id = record_usage(res, execution_surface="agent_runner",
                                        production_mutation_allowed=False)
                logger.info(f"BRAIN resolution for '{task_class}': {res['source']} "
                            f"(gene={res['provenance'].get('gene_id')}, usage={usage_id})")
            except Exception as e:
                logger.warning(f"Champion resolution skipped (non-fatal): {e}")
        
        import threading
        result_holder = {}
        
        def worker():
            try:
                result_holder["response"] = self.query_ollama(prompt, system_prompt, model)
                result_holder["status"] = "COMPLETED"
            except Exception as e:
                result_holder["error"] = str(e)
                result_holder["status"] = "FAILED"
        
        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=timeout_sec)
        
        if t.is_alive():
            logger.error(f"Task {task_id} exceeded ephemeral process lifetime TTL of {timeout_sec}s. Aborting.")
            return {
                "task_id": task_id,
                "status": "FAILED",
                "error": f"Execution exceeded ephemeral TTL limit of {timeout_sec} seconds."
            }
        
        if result_holder.get("status") == "FAILED":
            if usage_id:
                try:
                    from backend.factory.runtime_ledger import record_outcome
                    record_outcome(usage_id, {"execution_surface": "agent_runner",
                                              "task_id": task_id, "status": "FAILED",
                                              "error": result_holder.get("error", "")[:300]})
                except Exception:
                    pass
            return {
                "task_id": task_id,
                "status": "FAILED",
                "error": result_holder.get("error", "Task execution failed.")
            }
            
        logger.info(f"Task {task_id} completed successfully.")
        if usage_id:
            try:
                import hashlib
                from backend.factory.runtime_ledger import record_outcome
                resp = result_holder.get("response", "")
                record_outcome(usage_id, {
                    "execution_surface": "agent_runner", "task_id": task_id,
                    "status": "COMPLETED", "response_chars": len(resp),
                    "response_sha256": hashlib.sha256(resp.encode("utf-8")).hexdigest(),
                })
            except Exception:
                pass
        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "result": result_holder.get("response", ""),
            "brain_usage_id": usage_id,
        }

if __name__ == "__main__":
    runner = AgentRunner()
    if len(sys.argv) > 1:
        test_prompt = sys.argv[1]
    else:
        test_prompt = "Write a one-sentence greeting for the Hoch Agent Swarm."
    
    print("Running local test query...")
    result = runner.execute_task("test-01", test_prompt)
    print("\nResult:")
    print(json.dumps(result, indent=2))
