# Chaos Scenario 5: Corrupted Task Queue

* **Injected Failure**: Task queue JSON contains malformed characters (e.g. `[` character omitted at the start).
* **Command Used**: Manually edited `helm_task_queue.json` to insert bad control characters.
* **Expected Response**: Heartbeat truth freshness gate fails immediately due to JSON load exception.
* **Observed Response**: Gate output: `❌ Malformed JSON in helm_task_queue.json: Expecting value: line 1 column 1 (char 0)`.
* **Adapter/Runtime State Transition**: Watchdog service loops detect error, log the crash state, and block execution.
* **Task State Transition**: Blocks task dequeuing.
* **Pass/Fail Result**: **🟢 PASS**
* **Recovery Evidence**: Restoring correct JSON syntax inside the queue file resolved the exception.
