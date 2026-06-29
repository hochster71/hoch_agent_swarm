# Docker Role Image Separation Evidence

This evidence artifact verifies that the FastAPI API and the Autonomy/Readiness Daemon Worker services run as distinct role-specific Docker images.

## Metrics
- **Timestamp**: 2026-06-29T18:44:00Z
- **API Image ID**: `sha256:cc2c4f7ce731daa83d07576108696f007e2ad6fb82e4fae5353b508def509dde`
- **Worker Image ID**: `sha256:058de0e8dea524e2f0cf58012c71c837b33edfc8a5f5f16eac8d4efca59a5e21`
- **Role Image Separation**: PASS
- **API Role Label**: `org.hoch.role=api`
- **Worker Role Label**: `org.hoch.role=worker`
- **API Marker File**: `/app/.has-role-api` (PASS)
- **Worker Marker File**: `/app/.has-role-worker` (PASS)
- **Non-root Execution User**: `appuser` (PASS)

## Verification Log
```
==================================================
DOCKER ROLE SEPARATION CHECK
==================================================
API Image ID:    sha256:cc2c4f7ce731daa83d07576108696f007e2ad6fb82e4fae5353b508def509dde
Worker Image ID: sha256:058de0e8dea524e2f0cf58012c71c837b33edfc8a5f5f16eac8d4efca59a5e21
[PASS] has-api and has-worker have distinct image IDs.
[PASS] Label checks passed (API: api, Worker: worker)
[PASS] Role marker file checks passed.
[PASS] Non-root user checks passed.
[SUCCESS] Docker role image separation successfully verified.
```
