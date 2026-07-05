# AG Execution Policy

This document outlines the safety boundaries, classification rules, and doctrine limits enforced by the HAS/HASF autonomous execution engine.

## Policy Categories

1. **Allowed Internal / Documentation / Test Tasks**:
   - Local read operations, file parsing, documentation drafting, and test suite execution.
   - Restricted to risk levels **R2** or below.

2. **Blocked Categories**:
   - **Monetization**: Zero autonomous access to Stripe sandbox/live keys or billing paths.
   - **Releases**: No release packaging or production deployment without explicit founder signature.
   - **External Outreach & Investor Engagement**: Prohibited under private-first doctrine.
   - **Destructive Actions**: Hard blocked (preventing database truncations or directory wipes).

3. **Approval-Required Tasks**:
   - Policy change or runtime tier promotion modifications require manual founder verification.
