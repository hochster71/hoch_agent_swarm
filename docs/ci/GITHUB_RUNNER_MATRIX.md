# GitHub Runner Matrix

* **Document Version**: 1.0.0
* **Goal**: Establish a dual-runner QA lane model to ensure comprehensive, secure, and clean build validation.

---

## Runner Matrix

| Runner | Platform | Purpose | Mapped Checks & Tests | Excluded Checks | Reason for Exclusion |
|---|---|---|---|---|---|
| **macOS Runner** | macOS (Self-hosted) | Hardware and local environment compatibility | - Apple local telemetry tests (pmset)<br>- Safari/WebKit adjacent checks<br>- Workspace visual hygiene | - None | - Requires access to local hardware capabilities |
| **Linux Runner** | Ubuntu (GitHub-hosted) | Standard CI/CD compilation and gates | - Python backend unit tests<br>- Michael AI unit tests<br>- HELM status tests<br>- Static safety gates (host paths, hardcoded status)<br>- Anti-fake validation<br>- Frontend npm build | - Apple local telemetry execution<br>- VPS relay live checks<br>- Tailscale routes | - Lack of Apple hardware<br>- Lack of private environment secrets (Tailscale/SSH keys) in public actions |
| **Local / Manual** | Local Host / VPS | Real production & relay verification | - HOCH-200 live SSH verification<br>- Tailscale-only relay proof<br>- Moonshot tunnel validation<br>- Public exposure block checks | - None | - Requires active connection to private VPS and Tailscale tunnel |

---

## Action Plan on Failure
1. **Linux Runner Failure**: Indicates a logic regression in python code, a compilation error in frontend, or a safety violation (e.g. host path contamination). Fix codebase before merge.
2. **macOS Runner Failure**: Indicates an integration issue with the local hardware collector, or visual drift in workspace templates.
3. **Local/Manual Failure**: Indicates a VPS relay disconnect, public port misconfiguration, or Docker daemon state issue.
