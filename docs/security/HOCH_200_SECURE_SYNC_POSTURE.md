# Secure Remote Sync Posture — HOCH-200

---

## 1. Safe Sync Policy
* **Approved Sync Path**: [secure_sync_hoch200.sh](file:///Users/michaelhoch/hoch_agent_swarm/scripts/secure_sync_hoch200.sh) is the sole approved sync path.
* **Prohibited Parameters**: `StrictHostKeyChecking=no` is prohibited except documented emergency break-glass.
* **Break-glass usage**: Must be documented as evidence debt.
* **Verification**: Pinned keys in `known_hosts` or `StrictHostKeyChecking=accept-new` minimum.
* **Deploy Identity**: Dedicated deploy user instead of `root` remains a long-term target.
* **Egress Bounds**: No secrets, provider keys, or private signing keys synced.
