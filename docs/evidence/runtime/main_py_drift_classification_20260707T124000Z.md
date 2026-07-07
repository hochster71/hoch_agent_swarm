# Main Py Drift Classification

## Context
During independent verification of the Mission Commander truth upgrade, `backend/main.py` was found to be dirty with prototype homemesh routes and a `build_live_state` argument change from a previous session.

## Verdict
These changes represent a separate homemesh telemetry package and are not needed or related to the VPS relay dashboard package. To keep the relay package clean and minimal, we are restoring `backend/main.py` to HEAD.
