# Real-Cycle Diagnosis Report

This document analyzes why the autonomy daemon validator reported only simulated cycles, and details the steps required to transition to real-cycle execution safely.

---

## 1. Why Cycles Were Classified as Simulated

The daemon script (`scripts/ag_execution_daemon.py`) determines simulation status via the environment variable `DAEMON_TEST_MODE`:
- By default, if the variable is unset or set to `true`, the daemon runs in test-mode (`simulated: true`).
- In test-mode, the daemon increments simulated cycle counts and does not count toward the 24h burn-in wall-clock or real-cycle progression metrics.

---

## 2. Requirements for Producing Real Cycles

To transition the daemon to real-cycle mode:
1. Export the environment variable `DAEMON_TEST_MODE=false` before starting.
2. Ensure that `allow_ag_execution` remains `true` in `orchestration_bridge_control.json`.
3. Ensure that `operator_hold_active` is `false` in `ag_operator_hold.json`.

---

## 3. Safety and Blocker Analysis

- **Are real cycles safe without K1-K6 credentials?**
  Yes. The policy configuration in `ag_execution_policy.json` will block any task requiring external credentials or performing gated operations (such as App Store uploads or live reasoning calls). Local-only tasks can be processed safely.
- **Can local real tasks run without external secrets?**
  Yes. We can queue internal verification tasks that only read repository files, check checksums, or run local Python audits.
- **Recommended Safe Real Task Type**: Tasks with prefixes `verify_`, `lint_`, or `run_test` (e.g. `verify_local_system_hygiene`), classified under the risk tier `R1`.
