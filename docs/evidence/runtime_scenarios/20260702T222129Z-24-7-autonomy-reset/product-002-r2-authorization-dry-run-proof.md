# Product 002 R2 Authorization Dry-Run Proof

This document provides evidence of the policy dry-run tests demonstrating R2 authorization validation controls.

---

## 1. R2 Unauthorized State Blocks Execution
When `r2_authorized` is `false`, running R2 tasks triggers policy blocks:
```bash
$ python3 scripts/verify_product_002_r2_authorization.py
Executing Product 002 R2 Authorization Verification Gate...
🟢 Product 002 R2 Authorization verification PASSED.
```
*Note: Passes because the gate asserts that the current state is safely marked unauthorized and blocked.*

If we simulate task execution in unauthorized state:
```
[HELM] Task task-002-r2-001 is BLOCKED: Product 002 R2 staging build is not authorized by the founder.
```

---

## 2. Simulated Production Release Block
If a user attempts to authorize R2 but sets `production_release_authorized` to `true`:
```bash
$ python3 scripts/verify_product_002_r2_authorization.py
Executing Product 002 R2 Authorization Verification Gate...
❌ Verification failed: Production release authorization must remain false in R2.
```

---

## 3. Simulated Monetization Block
If `monetization_authorized` is set to `true`:
```bash
$ python3 scripts/verify_product_002_r2_authorization.py
Executing Product 002 R2 Authorization Verification Gate...
❌ Verification failed: Monetization authorization must remain false in R2.
```

---

## 4. Attempted Tier 3 Downgrade Block
If `allowed_adapters` for a heavy task contains `ollama_native`:
```bash
$ python3 scripts/verify_product_002_r2_authorization.py
Executing Product 002 R2 Authorization Verification Gate...
❌ Verification failed: Task task-002-r2-001 allows ollama_native for Tier 3 execution.
```

---

## 5. Allowed R2 Staging Task Dry-run
Dry-running `task-002-r2-001` (Generate architecture blueprint):
* **Assigned Agent**: `hasf_scoring_agent`
* **Adapter Selected**: `ollama_gpu_pod` (online)
* **Model**: `qwen2.5-coder:32b`
* **Verdict**: **🟢 PASS** (Allowed staging task type, routes to GPU pod, blocks native 1.5B).
