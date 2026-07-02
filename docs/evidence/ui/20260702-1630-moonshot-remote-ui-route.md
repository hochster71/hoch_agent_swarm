# Moonshot Remote UI Promotion Evidence

## Local Moonshot UI Proof
* **Canonical URL**: `http://127.0.0.1:8765/ui-moonshot`
* **Local Listener**: `python3 -m uvicorn backend.pert_server:app --port 8765`
* **Local Health Check**: Responds with `HTTP/1.1 200 OK` (or `405 Method Not Allowed` on `HEAD` checks).

## Remote Route Method
* **Mechanism**: SSH reverse tunnel forwarding local port `8765` to the remote Tailscale IP listener.
* **Command**: `ssh -N -f -R 100.87.18.15:8765:127.0.0.1:8765 root@50.116.41.183`
* **SSHD Configuration**: Added `GatewayPorts clientspecified` on the remote VPS `/etc/ssh/sshd_config` to allow explicit binding to the private Tailscale interface.

## Remote Tailscale URL
* **URL**: `http://100.87.18.15:8765/ui-moonshot`
* **Status**: **🟢 REACHABLE** (confirmed by check script and HTTP response header validations).

## Public Exposure Blocked Proof
* **Public Port Target**: `http://50.116.41.183:8765/ui-moonshot`
* **Audited Status**: **🟢 BLOCKED / TIMEOUT** (connection timed out after 5 seconds).

## Deprecated Surfaces
* **Old Cockpit UI Port**: `http://127.0.0.1:8080` (deprecated/unapproved for primary cockpit tasks).
* **Old Relay UI Surface**: `http://100.87.18.15:3012` (deprecated for frontend access).

## Runtime Truth Signals
The following signals have been updated in the Swarm Ledger database `swarm_ledger.db` under table `runtime_truth_signals`:
* `canonical_ui_url` = `http://127.0.0.1:8765/ui-moonshot`
* `canonical_ui_name` = `Moonshot UI`
* `canonical_remote_ui_url` = `http://100.87.18.15:8765/ui-moonshot`
* `old_local_ui_8080` = `deprecated`
* `old_relay_ui_3012` = `deprecated`
* `moonshot_remote_ui_status` = `active/private`
* `moonshot_remote_ui_public_exposure` = `blocked`

## Gate Results
* `moonshot_remote_ui_gate.sh`: **🟢 PASS** (all reachability, public blocking, and DB truth alignments verified successfully).

## Remaining Risks
* Tunnel connection could terminate if SSH session drops. (Monitored by `scripts/moonshot_remote_tunnel_check.sh`).

## Rollback / Stop Command
* **Command**: `bash scripts/moonshot_remote_tunnel_stop.sh`
