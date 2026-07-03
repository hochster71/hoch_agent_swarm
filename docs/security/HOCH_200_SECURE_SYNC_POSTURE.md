# Secure Remote Sync Posture — HOCH-200

---

## 1. Safe Sync Policy
* Transitioning away from `StrictHostKeyChecking=no`.
* Use `StrictHostKeyChecking=accept-new` or pinned SSH host keys in `known_hosts` to avoid man-in-the-middle attacks.
* Long-term path: Dedicated deploy user instead of `root`.
