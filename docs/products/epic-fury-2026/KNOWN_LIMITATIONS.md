# Known Limitations - Epic Fury 2026

* **Run ID**: 20260702T233000Z-epic-fury-2026-hasf-vetting

---

## 1. Documented Limitations

### Local Dev Server Dependency for E2E Tests
* **Description**: E2E tests target a local server instance running at `http://localhost:3003`.
* **Mitigation**: The test runner verifies port availability before execution.

### Stripe Sandbox Only
* **Description**: Live Stripe charging remains blocked by default. Testing operates solely in Stripe sandbox/test mode using mock price/customer tokens.
* **Mitigation**: Sandbox configuration must be validated in staging before production rollout.

### Fallback Security Scanning
* **Description**: Native binaries for Gitleaks, Semgrep, Trivy, and Syft are unavailable on the local host. Vetting relies on Python/Node-based fallbacks.
* **Mitigation**: Ensure remote/CI pipelines execute full binary checks prior to merging.
