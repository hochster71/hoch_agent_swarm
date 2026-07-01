# HOCH HASF Soccer Platform Onboarding PERT Model

Below is the critical path schedule model to transition the soccer intelligence platform from intake to live production release.

```mermaid
gantt
  title Onboarding Pipeline Critical Path
  dateFormat X
  axisFormat %d
  section Onboarding
  Codebase Audit & Gap Mapping (T1)       :active, t1, 0, 5d
  Setup Env Config & Auth Gate (T2)       :after t1, t2, 10d
  Implement Stripe Tiers & Checkout (T3)  :after t2, t3, 15d
  Write Unit & E2E Playwright Tests (T4) :after t3, t4, 10d
  Deploy Staging & Production Release (T5):after t4, t5, 5d
```

## Task Definitions and Durations

| Task | Title | Expected Duration | Dependencies | Owner |
| --- | --- | --- | --- | --- |
| **T1** | Codebase Audit & Gap Mapping | 5 days | None | AI QA & Release Authority |
| **T2** | Setup Env Config & Auth Gate | 10 days | T1 | AI Security & Compliance Officer |
| **T3** | Implement Stripe Tiers & Checkout | 15 days | T2 | HASF Product Finance Manager |
| **T4** | Write Unit & E2E Playwright Tests | 10 days | T3 | AI QA & Release Authority |
| **T5** | Deploy Staging & Production Release | 5 days | T4 | AI Technical Director |
