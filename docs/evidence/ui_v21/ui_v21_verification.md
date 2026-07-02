# UI V2.1 Verification Evidence

- Timestamp UTC: 2026-07-02T18:09:24Z
- Route: http://127.0.0.1:8765/ui-v2
- Server PID: 83903
- Watchdog PID: 75271
- Tabs: Command, Pods, Revenue, Evidence, PERT, Watchdog

## Smoke Test
=== VERIFY UI V2.1 ROUTE ===
UI_V21_ROUTE: PASS

=== VERIFY API JSON ===
API_JSON: PASS

=== VERIFY CRITICAL TELEMETRY ===
global_verify: FRESH age=42.1 reason=None
hoch_pods_runtime_state: FRESH age=42.0 reason=None
hoch_pod_schedule: FRESH age=42.0 reason=None
CRITICAL_TELEMETRY: PASS

=== VERIFY WATCHDOG ===
WATCHDOG: PASS pid=75271

UI_V21_SMOKE: PASS

## Watchdog Tail
[2026-07-02T17:58:35Z] HAS telemetry watchdog refresh start
LIVE_TELEMETRY_REFRESH: PASS
LIVE_TELEMETRY_FRESHNESS: PASS
[2026-07-02T17:58:35Z] HAS telemetry watchdog refresh complete

[2026-07-02T18:03:38Z] HAS telemetry watchdog refresh start
LIVE_TELEMETRY_REFRESH: PASS
LIVE_TELEMETRY_FRESHNESS: PASS
[2026-07-02T18:03:38Z] HAS telemetry watchdog refresh complete

[2026-07-02T18:08:40Z] HAS telemetry watchdog refresh start
LIVE_TELEMETRY_REFRESH: PASS
LIVE_TELEMETRY_FRESHNESS: PASS
[2026-07-02T18:08:40Z] HAS telemetry watchdog refresh complete

