# Orchestration Bridge Kill Switch Proof

---

## 1. Temporary Enablement Window
* **Window Start**: `2026-07-03T14:09:10Z`
* **Window End**: `2026-07-03T14:09:15Z`

---

## 2. Block Demonstration Logs
1. `orchestration_bridge_enabled = false`:
   - Observed behavior: Bridge run aborted immediately. "Bridge disabled via kill switch control file." logged.
2. `allow_provider_api_calls = false`:
   - Observed behavior: OpenAI reasoning adapter initialized in mock dry-run mode; no outbound REST calls attempted.
3. `allow_ag_execution = false`:
   - Observed behavior: Task decomposition runs successfully, but no command/file actions executed via AG adapter.
4. `allow_founder_gated_execution = false`:
   - Observed behavior: Critical risk task routing was suspended; marked as BLOCKED pending human spot-check.

---

## 3. Verified Restored Dark-Ship State
* **Timestamp**: `2026-07-03T14:09:16Z`
* **State Config**:
  ```json
  {
    "orchestration_bridge_enabled": false,
    "max_concurrent_missions": 1,
    "allow_provider_api_calls": false,
    "allow_ag_execution": false,
    "allow_founder_gated_execution": false
  }
  ```
All flags successfully restored.
