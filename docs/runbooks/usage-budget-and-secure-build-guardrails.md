# Runbook: Usage Budget & Secure Build Guardrails (RC34)

## Purpose
This runbook guides operators on managing, monitoring, and auditing the **AG/ChatGPT Usage Budget** and **Secure Build Guardrails** designed to protect resources from quota burn and prevent security regressions.

## Budget & Guardrail Policies
The budget and secure build policies are defined in two YAML files:
- **Usage Budget Policy**: `/config/usage_budget_policy.yaml` (specifies limits on files changed, scripts added, and duration)
- **Secure Build Guardrails**: `/config/secure_build_guardrails.yaml` (lists blocked/high-risk actions and required checks)

## Operator Controls

### Running the Usage Check
To evaluate current cycle usage and risk:
```bash
bash scripts/ag_usage_budget_check.sh
```

### Running the Secure Build Check
To scan for staged credentials, db files, and port exposure:
```bash
bash scripts/secure_build_guardrail_check.sh
```

### Orchestrated Verification Run
To execute all local checks, including Playwright regression and mirror verification:
```bash
bash scripts/rc34_usage_guardrail_verify.sh
```
