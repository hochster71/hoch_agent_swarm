# HOCH Prompt Brain — Dynamic 9-Dimensional Scoring Methodology

This document outlines the mathematical framework, weights, and criteria for the output-specific 9-dimensional validation scoring schema.

---

## 1. Dimensional Weights

Validation checks are divided into 9 dimensions, producing a final weighted score:

| Dimension | Description | Weight |
|---|---|---|
| **Completeness** | Full coverage of inputs, tasks, and boundaries. | 15% |
| **Structure** | Valid JSON schema layout and type safety. | 15% |
| **Domain Specificity** | Integration of NAICS / SOC occupation terminologies. | 15% |
| **Risk Controls** | Incorporation of NIST AI RMF and mitigation strategies. | 10% |
| **Evidence Usefulness** | Presence of actionable artifact paths and audit trails. | 10% |
| **Actionability** | Step-by-step remediation plans and recovery steps. | 10% |
| **Verifiability** | Verification checklist assertions and compliance logs. | 10% |
| **Compliance Alignment** | NIST SP 800-53 / FedRAMP SSP control assertions. | 10% |
| **Red-Team Resilience** | Safety boundary checks and prompt injection resilience. | 5% |

---

## 2. Weighted Formula

The final weighted score ($S$) is calculated as follows:

$$S = 0.15 \cdot \text{Completeness} + 0.15 \cdot \text{Structure} + 0.15 \cdot \text{Specificity} + 0.10 \cdot \text{RiskControls} + 0.10 \cdot \text{Usefulness} + 0.10 \cdot \text{Actionability} + 0.10 \cdot \text{Verifiability} + 0.10 \cdot \text{Compliance} + 0.05 \cdot \text{Resilience}$$
