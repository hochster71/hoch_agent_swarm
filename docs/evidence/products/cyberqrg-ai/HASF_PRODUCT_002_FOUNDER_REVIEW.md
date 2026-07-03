# HASF Product 002 Vetting Gated State Lock

To ensure safety and robust control under L3 Quality Maturity, Product 002: **CyberQRG-AI** is locked to **Phase 1** planning/roadmap tasks. No high-risk actions (R2+) may run without explicit founder review and approval.

---

## 1. Locked Risk Budget

| Parameter | Gated Status | Restriction Details |
|---|---|---|
| **Capacity Tier** | `light` | Only model queries and markdown text generation are permitted. |
| **Risk Budget** | `R0 - R1` | Limit to security analysis profile, utility scoring, and roadmap formulation. |
| **Allowed Actions** | `query_light_model`, `query_heavy_model`, `write_markdown_evidence`, `log_json_state` | All other actions are blocked by the Policy Enforcement Point. |
| **Blocked Actions (R2+)** | `spawn_agent`, `git_push`, `stage_deployment`, `run_arbitrary_script` | Locked. Cannot be executed autonomously. |

---

## 2. Founder Override Gate
To transition Product 002 from a planned roadmap state (R0/R1) to active implementation (R2+), the founder must provide an explicit approval override flag in the task payload.
