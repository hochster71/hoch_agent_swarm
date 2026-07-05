# Primary Host Strategy Decision Record

This document evaluates implementation strategy options for the 24h burn-in daemon execution.

---

## Strategy Options Evaluation

### 1. Dedicated HOCH-200 Host
* **Description**: Ubuntu Linux 22.04 LTS always-on bare metal host.
* **Pros**: Always-on capable, supports native systemd, secure LAN loopback only.
* **Cons**: Target IP and connection keys are currently unmapped.
* **Effort**: Low (once IP and keys are mapped).
* **Verdict**: **PRIMARY_HOST_STRATEGY_PENDING_FOUNDER_DECISION**

### 2. Existing LAN Host Candidate (Non-MacBook Pro)
* **Description**: Any other active machine on the local network sweep.
* **Pros**: Physically present on LAN, avoids public cloud dependencies.
* **Cons**: Device identities and credentials are unknown.
* **Effort**: Medium.
* **Verdict**: **PRIMARY_HOST_STRATEGY_PENDING_FOUNDER_DECISION**

### 3. New VPS / DigitalOcean Droplet
* **Description**: Fresh virtual server provisioned via droplet API.
* **Pros**: Clean isolation, guaranteed uptime, standard systemd environment.
* **Cons**: Needs DO API token, requires secure private tunnel configurations.
* **Effort**: Medium.
* **Verdict**: **PRIMARY_HOST_STRATEGY_PENDING_FOUNDER_DECISION**

### 4. Temporary MacBook Pro secondary proof
* **Description**: Running daemon on the developer MacBook Pro control node.
* **Pros**: Already validated in secondary test runs.
* **Cons**: Sleeps, battery-dependent, does not satisfy the primary always-on govern requirement.
* **Effort**: None.
* **Verdict**: **PRIMARY_HOST_STRATEGY_PENDING_FOUNDER_DECISION**

### 5. Defer primary burn-in
* **Description**: Pause burn-in progression until dedicated hardware is available.
* **Pros**: Avoids temporary or cloud-based workarounds.
* **Cons**: Delays validation timeline.
* **Effort**: None.
* **Verdict**: **PRIMARY_HOST_STRATEGY_PENDING_FOUNDER_DECISION**

---

## Summary Verdict

**PRIMARY_HOST_STRATEGY_PENDING_FOUNDER_DECISION**
Michael must formally select and authorize the target strategy option to unblock K5 access.
