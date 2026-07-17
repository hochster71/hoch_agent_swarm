# SWARM-3 verification notes

## Guard holder
holder = swarm/nist-matrix
Only shared file touched: backend/helm_live_api.py (2-line router-registration block,
matching SWARM-1's health_router pattern). Lease srclease-2359e739 acquired via
`guarded_edit acquire ... --seconds 300` before the edit, edit applied, write recorded
via `SourceLeaseManager.record_own_write`.

## Lease-release note (environment limitation, not a coordination conflict)
`guarded_edit release` failed in THIS sandboxed session with EPERM on unlink:
    PermissionError: [Errno 1] Operation not permitted: '.../coordination/source_leases/backend_helm_live_api.py.<hash>.lock'
Diagnosed as a sandbox-wide restriction, not a lease-specific or file-specific issue:
`os.unlink()` was denied on every path tested in this mount (coordination/leases/,
coordination/, backend/helm/, and repo root), including a throwaway file created and
immediately unlinked in the same process. Nothing else in this deliverable required
delete/unlink. The lease was acquired with `--seconds 300`; `source_lease.py`'s
`acquire()` reclaims any expired lease automatically for the next acquirer (its own
`unlink` call happens in the acquiring agent's own environment, not this one), so this
self-heals without intervention once the lease's `expires_at` passes
(2026-07-15T16:18:49Z). No commit, force-delete, or manual lock-file surgery was
performed to work around this — per doctrine, "never force."

Three empty probe files created while diagnosing the unlink restriction could not be
cleaned up for the same reason and are left for a human/agent with real delete
permission to remove:
  _probe_root.tmp
  coordination/_probe.tmp
  coordination/leases/_probe.tmp

## Live-system contact
The live API on 127.0.0.1:8770 (Phase-C soak host) was NOT reachable from this sandbox
(different network namespace — connection refused, not a route bug) and was never
targeted for start/stop/restart/rebind. Verification instead used a throwaway instance
of the SAME `backend.helm_live_api:app` bound to 127.0.0.1:18770 inside this sandbox,
booted and killed within a single bash invocation, confirmed via `ps aux` to leave no
stray process afterward.

## Route verification (sandboxed instance, port 18770)
  GET /api/v1/helm/nist   -> 200  (16120 bytes)  -> nist_api_response.json
  GET /nist               -> 200  (8022 bytes)   -> nist_ui_response.html
  GET /api/v1/helm/chain  -> 200  (4674 bytes)   -> chain_response.json   (AU-9 evidence pointer)
  GET /api/v1/helm/authority -> 200 (2265 bytes) -> authority_response.json (AU-10 evidence pointer)
  GET /api/v1/helm/wall   -> 200  (3704 bytes)   -> wall_response.json    (CA-7/SC-7/etc evidence pointer)

## Matrix snapshot (this environment, this commit)
COVERED 8 / PARTIAL 4 / UNVERIFIED 0 / total 12
See matrix_cli_summary.txt and nist_api_response.json for the full row-by-row detail.
