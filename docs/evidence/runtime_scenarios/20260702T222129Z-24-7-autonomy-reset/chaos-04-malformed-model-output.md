# Chaos Scenario 4: Malformed Model Output

* **Injected Failure**: Model output is returned with a raw exception string instead of valid JSON or Markdown.
* **Command Used**: Programmatically simulated in the Golden Harness evaluating a payload with raw error blocks.
* **Expected Response**: Output validator G-EVAL detects schema/field match failure, and the quality gate rejects the run.
* **Observed Response**: Gate output: `❌ G-EVAL failed: Deterministic pass rate is less than 100%`.
* **Adapter/Runtime State Transition**: Transitioned agent status to `FAILED`.
* **Task State Transition**: Task status marked as `failed` or queued for retry.
* **Pass/Fail Result**: **🟢 PASS**
* **Recovery Evidence**: Regulating model temperature/heuristics and rerunning the harness restored output quality values.
