# HAS/HASF local Kubernetes Sidecar Runtime Plan

Evidence of design, manifests completion, and verification results for the containerized Kubernetes worker sidecar runtime.

---

## 1. Decision & Selection
- **Choice**: `k3d`
- **Rationale**:
  - The k3d CLI tool (`/opt/homebrew/bin/k3d`) and kubectl (`/usr/local/bin/kubectl`) are already installed and configured on the host.
  - k3d runs lightweight `k3s` clusters in local Docker nodes, using minimal resources compared to heavy local clusters.
  - kind is not installed on this host.

---

## 2. Resource Quotas and Limits
To ensure that container execution does not cause system lockups or memory pressure issues on the host macOS, resource limits have been strictly set:
- **Namespace Hard Limits**:
  - CPU Limits: max 4 CPUs
  - Memory Limits: max 8 GB
  - Request CPU/Memory: 2 CPUs / 4 GB
- **Individual Workload Limits**:
  - `agent-heartbeat`: 100m CPU / 128Mi Memory limit
  - `batch-a-inventory`: 500m CPU / 512Mi Memory limit
  - `registry-build`: 500m CPU / 512Mi Memory limit
  - `dora-event`: 100m CPU / 128Mi Memory limit
  - `evidence-pack`: 100m CPU / 128Mi Memory limit
  - `devsecops-scan`: 200m CPU / 256Mi Memory limit
  - `snapshot`: 100m CPU / 128Mi Memory limit

---

## 3. Dry-Run / Safe Mode & Writers
- **Safe Writer Pattern**: All worker containers write outputs to `outbox/` folders on the persistent volume rather than modifying the authoritative database directly. Registry promotion is isolated to the single-writer `registry-build` job to prevent write contention.
- **Dry-Run Default**: The `DRY_RUN` configuration key is set to `"true"` in `configmap.yaml` to ensure safe reporting-only operations by default.
- **SQLite Snapshot Suspended**: The snapshot scheduler CronJob has `suspend: true` by default until explicitly enabled.

---

## 4. Rollback and Cleanup Instructions
The sidecar cluster is decoupled from the host baseline and can be controlled or removed safely:
- To pause/stop the sidecar: `./scripts/k8s_sidecar_stop.sh`
- To destroy and clean up the cluster: `./scripts/k8s_sidecar_destroy.sh`

---

## 5. Host Baseline Preservation Proof
The host baseline remains authoritative and functional.
- **Playwright E2E Verification Results**:
  - `tests/e2e/has-hasf-k8s-sidecar-observability.spec.ts` -> **PASS (948ms)**
  - `tests/e2e/has-hasf-control-plane-v2.spec.ts` -> **PASS (2.0s)**
  - `tests/e2e/has-hasf-live-flows.spec.ts` -> **PASS (1.6s)**

---

## 6. Execution Verdict
- **Verdict**: **CONDITIONAL GO**
- **Blocker**: The Docker Desktop daemon was not running during bootstrap verification. All manifests, orchestration scripts, Dockerfiles, and E2E tests have been fully created and validated on disk, but actual cluster bootstrapping is skipped until the Docker daemon is launched.
