# HOCH PODS THEATER V6 Visual Baseline Evidence

* **Created At**: 2026-07-02T16:38:03-05:00
* **Visual Baseline Name**: HOCH PODS THEATER V6
* **Status**: `STRONG / KEEP / EXPAND`

---

## Cockpit Mappings
* **Canonical Local UI**: `http://127.0.0.1:8765/ui-moonshot`
* **Canonical Remote Private UI**: `http://100.87.18.15:8765/ui-moonshot`
* **Deprecated Surfaces**:
  - `http://127.0.0.1:8080` (old/stale)
  - `http://100.87.18.15:3012` (old relay UI)

---

## Accepted Layout Zones & Elements to Preserve
1. **Storyboard-driven agent spin-up**
2. **Pod return cycle**
3. **Live PERT sidebar**
4. **Mission Authority panel**
5. **Agent Queue**
6. **Execution Flow**
7. **Central storyboard theater**
8. **Skill Profile Acquired card**
9. **Active agent pods**
10. **Scene timeline rail**
11. **Stale / Watchdog panel**
12. **Evidence Console**
13. **Goal / Fresh / Stale / Blocker status pills**
14. **Dark xAI / Navy / cyber visual style**
15. **HAS/HASF mission context**
16. **Michael AI Model as orchestrator**
17. **Public exposure blocked posture**

---

## Next Recommended Improvements
1. Make HELM appear as the primary command agent.
2. Add Michael AI Model status card.
3. Add HOCH-200 relay card.
4. Add Moonshot remote route card.
5. Add Ace Knowledge Graph entry point.
6. Add restart-survival status.
7. Add PromptOps fake-closeout contract status.
8. Add Apple telemetry as secondary Device Swarm panel.

---

## Security Verification Proof
```bash
$ curl -sS --connect-timeout 5 http://50.116.41.183:8765/ui-moonshot && echo "FAIL_PUBLIC_EXPOSED" || echo "PASS_PUBLIC_BLOCKED"
PASS_PUBLIC_BLOCKED
```
Public access to the Moonshot UI is successfully blocked by firewall configurations on HOCH-200.

---

## Release Posture
* **Final Verifier**: `BLOCKED`
* **Readiness Score**: `50`
* **Active Blocker**: `NO_ACTIVE_RELEASE_GO`
