# Host Listener and MBPro Hygiene Audit Report

This report records the host wildcard listener classifications, remediation actions, and current candidate node connectivity checks for the Hoch Agent Swarm (HAS) deployment.

## 1. Host Wildcard Listener Classification Table

The host listeners on wildcard interfaces (`*`) have been audited and classified:

| Process | PID | Port | Protocol | Owner | Expected/Unknown | HAS-related | Risk | Action | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ControlCenter` | 1084 | 5000 | TCP | `michaelhoch` | Expected | No | Low | KEEP | macOS AirPlay Receiver system service. |
| `ControlCenter` | 1084 | 7000 | TCP | `michaelhoch` | Expected | No | Low | KEEP | macOS AirPlay Receiver system service. |
| `Python` | 1750 | 8080 | TCP | `michaelhoch` | Expected | Legacy | Medium | STOP | Legacy `live_swarm.py` host listener. Unloaded and stopped. |
| `Python` | 1753 | 8810 | TCP | `michaelhoch` | Expected | No | Medium | RESTRICT | `family_dell_pull_server.py` local pull service. Should bind to 127.0.0.1. |
| `Python` | 1762 | 8820 | TCP | `michaelhoch` | Expected | No | Medium | RESTRICT | `family_neo_pull_server.py` local pull service. Should bind to 127.0.0.1. |
| `Python` | 1754 | 8830 | TCP | `michaelhoch` | Expected | No | Medium | RESTRICT | `family_imac_pull_server.py` local pull service. Should bind to 127.0.0.1. |
| `node` | 1795 | 8789 | TCP | `michaelhoch` | Expected | No | Low | KEEP | Mesh Studio development backend (`server/index.js`). |
| `Python` | 28598 | 8898 | TCP | `michaelhoch` | Expected | No | Medium | STOP | Host HTTP file server. Unloaded and stopped. |
| `lmlink-co` | 3490 | 40844 | TCP | `michaelhoch` | Expected | No | Low | KEEP | LM Studio Local Link connector daemon. |
| `Spotify` | 1240 | 52016 | TCP | `michaelhoch` | Expected | No | Low | KEEP | Spotify client local media connection listener. |
| `Spotify` | 1240 | 57621 | TCP | `michaelhoch` | Expected | No | Low | KEEP | Spotify client local media connection listener. |
| `rapportd` | 1023 | 49153 | TCP | `michaelhoch` | Expected | No | Low | KEEP | Apple device sharing and pairing system service. |

## 2. Actions Taken

1. **Stopped Legacy live-swarm.py (`*:8080`)**: Unloaded `com.hoch.live-swarm.plist` from launchd and confirmed port `8080` is now exclusively bound to `com.docker` on loopback `127.0.0.1`.
2. **Stopped console server (`*:8898`)**: Unloaded `com.hoch.agent.swarm.console.server.plist` from launchd and stopped the process.
3. **Confirmed host-level isolation**: Ports `8080` and `8898` no longer have wildcard host exposure.

## 3. HAS Gate Results

All local exposure and security compliance gates remain in a fully compliant posture:

* **Docker Network Exposure Check**: `PASS` (Loopback-only posture is enforced)
* **HTTPS UI/API Truth Alignment**: `PASS` (Proxy responding on loopback via TLS)
* **HTTP -> HTTPS Redirect**: `PASS` (HTTP requests redirected with `308 Permanent Redirect`)
* **HTTP/2 Support**: `PASS` (TLSv1.3 h2 negotiation verified)
* **Security Headers**: `PASS` (HSTS, X-Frame-Options, X-Content-Type-Options, CSP present and correct)

## 4. MBPro Node Status

* **Connectivity status**: `MBPRO_OLLAMA_OFFLINE`
* **Node configuration posture**:
```json
{
  "node_name": "mbpro",
  "host": "10.0.0.115",
  "status": "candidate_offline",
  "routing_enabled": false,
  "approval_required": true
}
```
* **Note**: No routing is active or enabled for this node.

## 5. Final Verifier Verdict

* **Verdict**: `BLOCKED`
* **Readiness Score**: `50.0`
* **Active Release Blocker**: `NO_ACTIVE_RELEASE_GO`

---

**Evidence Path**: `docs/evidence/audit/20260629-2228-host-listener-and-mbpro-hygiene.md`
