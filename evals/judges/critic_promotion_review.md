# Critic Rubric: Promotion & Drift Review

Use this rubric to verify promotion requests before upgrading the runtime gate level (e.g. promoting to Rung 3).

## Rubric Checklist

1. **Promotion Criteria Integrity**:
   - Verify that all criteria specified in the promotion schema are satisfied (e.g. minimum number of successful consecutive runs).
   - Check that no manual intervention or prompt injections occurred.

2. **Policy Drift Detection**:
   - Compare the current `api_budget_policy.json` and `provider_data_egress_policy.json` against base templates.
   - Flag any unauthorized changes or policy relaxation.

3. **Cryptographic Validation**:
   - Ensure all previous evidence packages are correctly signed and sealed.
