# Runbook: QA/Audit PERT Alignment (RC39)

This runbook outlines how to operate and maintain the audit-grade alignment features in the HAS/HASF PERT Command Center.

## 1. Goal Completion Calculation (Formula)
- **Calculation Logic**: Goal Completion is computed using a weighted sum of completed workstreams:
  $$\text{Goal Completion} = \sum_{t \in \text{Completed Tasks}} \text{Weight}(t)$$
- **Weights Configuration**:
  - `W1` - `W3`, `W5`, `W7` - `W8`, `W10`, `W13` - `W14`: **6.0%** each
  - `W4`, `W6`, `W9`, `W11`: **7.0%** each
  - `W15`: **8.0%**
  - `W12` (Monetization Sidecar): **10.0%** (Currently **PENDING**)
- If the Monetization Sidecar (`W12`) is not completed, the maximum goal completion score is capped at **90.0%**.

## 2. Monetization Readiness Verification
- **Separation of Concerns**:
  - **Evidence Coverage** represents the percentage of required evidence logs present.
  - **Stripe Sandbox State** represents whether Stripe test configurations are finalized.
- **Formulas**:
  - $$\text{Evidence Coverage} = \frac{\text{Present Required Logs}}{\text{Total Required Logs}} \times 100\%$$
  - If Stripe Sandbox is `NOT_CONFIGURED`, the Monetization Readiness score is capped at:
    $$\text{Monetization Readiness} = \text{Evidence Coverage} \times 0.5$$
- Since Stripe keys must remain unconfigured local secrets per security rules, the Monetization Readiness is dynamically capped at **50.0%** when evidence is 100%.

## 3. Worker Metrics Monitoring
- Worker nodes are monitored dynamically through Tailscale and classified into:
  1. **Visible Tailnet Devices**: Total devices found in tailnet.
  2. **Build Capable Workers**: Nodes allowed to run builds (`michaels-macbook-pro`).
  3. **Relay Registry Workers**: Nodes acting as VPS routing agents (`hoch-relay-001`).
  4. **Monitor-Only Clients**: Nodes with read-only visibility (`iphone-15-pro-max`).
  5. **Offline Clients**: Nodes that are disconnected.

## 4. Playwright Test Telemetry
- Test telemetry parses the live JSON test report (`artifacts/qa/playwright-antigravity-runtime.json`) dynamically.
- If the file is missing or unreadable, the status reverts to `UNKNOWN`.
