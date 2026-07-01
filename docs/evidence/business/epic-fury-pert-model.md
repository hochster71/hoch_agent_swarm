# Epic Fury Onboarding PERT Model (RC41)

This document establishes the PERT / CPM network and estimate metrics for onboarding **Epic Fury 2026** into the HASF release pipeline.

## 1. Work breakdown Structure (WBS) & Estimations

We define six core pipeline stages for the onboarding and deployment process:

| Stage ID | Stage Title | Optimistic (O) | Likely (M) | Pessimistic (P) | Expected Time ($T_E$) |
| --- | --- | --- | --- | --- | --- |
| **S1** | Source Discovery | 2 mins | 5 mins | 10 mins | 5.33 mins |
| **S2** | Audit & Analysis | 5 mins | 10 mins | 20 mins | 10.83 mins |
| **S3** | Environment Setup | 5 mins | 8 mins | 15 mins | 8.67 mins |
| **S4** | CI Verification | 10 mins | 15 mins | 30 mins | 16.67 mins |
| **S5** | PERT Integration | 5 mins | 10 mins | 15 mins | 10.00 mins |
| **S6** | Pipeline Visuals | 10 mins | 20 mins | 40 mins | 21.67 mins |

## 2. CPM Path Analysis
* **Critical Path**: `S1 -> S2 -> S4 -> S6`
* **Total Expected Onboarding Time**: $73.5$ minutes
* **Slack Time**: $0.0$ minutes (on critical path)
