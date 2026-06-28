# Prompt Library Governance Review
**Document Type:** QA Addendum — Prompt Library Access Review  
**Date:** 2026-06-26  
**Reviewed by:** HOCH QA Test Strategy Architect  
**Status:** READ-ONLY — No library mutation during review  
**Working directory:** `/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm`  

> **IMPORTANT:** This review is an **addendum** to `qa_test_strategy.md`. The prompt library is classified as a **read-only controlled knowledge source** pending full approval workflow implementation.

---

## Library Location

| Item | Value |
|---|---|
| **Primary path** | `/Users/michaelhoch/hoch_agent_swarm_prompt_library` |
| **Repository reference** | `michaelhoch/hoch_agent_swarm_prompt_library` (GitHub) |
| **Snapshot ZIP** | `/Users/michaelhoch/hoch_agent_swarm_prompt_library.zip` |
| **Backend copy (read-only)** | `backend/prompt_library.json` (copied 2026-06-26) |
| **Access policy** | READ-ONLY — no agent write or mutation permitted |

---

## File Inventory

| File | SHA-256 | Size | Status |
|---|---|---|---|
| `hoch_agent_swarm_prompt_library.json` | `2ebbfb4229d91ce19c77fec1ae81acdc98f8a3fa23f915799a121477d9e639f8` | 77,219 B | ✅ CLEAN |
| `hoch_agent_swarm_prompt_library.md` | `cafe5095364e7bf2815cd13e98e4eb9174575c92e49dfa36667c116415faebb9` | 80,266 B | ✅ CLEAN |
| `hoch_agent_swarm_prompt_library.csv` | `eef1a64487ccdce2a63e2bca39c75f73e4173d91f7da4a4159ca41af5058cd18` | 64,731 B | ✅ CLEAN |
| `hoch_agent_swarm_prompt_library.html` | `5f120b52fee74c66646bc3daf0f74d0a9f0c5cd99c7fbf543d541579ffc491a9` | 135,803 B | ✅ CLEAN |
| `hoch_agent_swarm_prompt_manifest.json` | `ded56c884595f90bf4d9556a7d94421644652473c6e431cf9fb0434273ee710d` | 79,705 B | ✅ CLEAN |

**Total files:** 5 | **Total size:** 437,724 bytes | **Mutations:** 0 — library untouched

---

## Prompt Categories

**Total prompts:** 103 across **20 categories**

| Category (raw) | Mapped | Count | Dominant Risk |
|---|---|---|---|
| Audit | AUDIT | 15 | LOW |
| Industry Specialized | UNKNOWN | 15 | LOW–HIGH |
| DevSecOps | DEVSECOPS | 13 | LOW–HIGH |
| QA | QA | 12 | LOW–HIGH |
| DAST | DAST | 9 | MEDIUM–HIGH |
| SAST | SAST | 8 | MEDIUM |
| Operations | OPERATIONS | 7 | LOW |
| Coding | CODING | 5 | LOW |
| Security Architecture | ARCHITECTURE | 3 | LOW |
| AI / ML Systems | ARCHITECTURE | 2 | HIGH |
| Vulnerability Management | CYBERSECURITY | 2 | LOW–MEDIUM |
| Data Security | CYBERSECURITY | 2 | MEDIUM |
| Detection Engineering | CYBERSECURITY | 2 | LOW |
| Governance | GOVERNANCE | 2 | LOW |
| Incident Response | GOVERNANCE | 1 | LOW |
| Privacy | GOVERNANCE | 1 | LOW |
| Cloud Security | DEVSECOPS | 1 | HIGH |
| Supply Chain | SUPPLY_CHAIN | 1 | LOW |
| Legal / Compliance | GOVERNANCE | 1 | LOW |
| UX Security | QA | 1 | LOW |

**Industries represented:** 16 (All Industries 62, DoD/National Security 4, AI/ML Systems 4, Federal Civilian 3, Healthcare 3, Financial Services 3, Energy/Utilities 3, Manufacturing/OT 3, Retail/E-commerce 3, SaaS/Cloud 3, and others)

---

## Prompt Quality Findings

### Strengths
- All 103 prompts have consistent 7-field schema: `id`, `category`, `industry`, `title`, `mission`, `outputs`, `prompt`
- Every prompt begins "You are the HOCH [Agent Role]..." — well-formed persona framing
- Each prompt specifies concrete `outputs` — no open-ended instructions
- Later prompts (from THREAT-002 onward) include a 7-point structured output template: (1) facts, (2) assumptions, (3) risks, (4) actions, (5) tests, (6) decision, (7) evidence artifacts
- Security prompts are written as auditors and reviewers, not as attackers — appropriate defensive framing

### Gaps
- No `risk_level` or `requires_approval` field in source JSON — must be computed at load time
- No `last_reviewed_at` timestamp — all prompts treated as unreviewed until stamped
- No `intended_agents` field — which swarm agents may use each prompt is undefined
- No SHA-256 per prompt entry in manifest — hash tracking must be added at ingestion
- "Industry Specialized" category needs disambiguation to canonical mapped category

---

## Security / Safety Findings

### Risk Scan Summary

| Tool | Result |
|---|---|
| `grep -RIn` (16 keyword patterns) | 171 lines flagged |
| Python word-boundary re-scan | 0 BLOCKED, 13 HIGH, 7 MEDIUM, 83 LOW |
| Initial false positives | 4 (DAN as substring in compound words) |

> **NOTE:** The raw grep scan log (`prompt_library_risk_scan.log`) contains 171 lines of pattern matches. After word-boundary disambiguation, none constitute actual jailbreak instructions. The log is preserved as raw evidence and must NOT be used for blocking decisions without word-boundary verification.

### Final Classification (word-boundary verified)

| Risk | Count | Execution |
|---|---|---|
| **HIGH** | 13 | Gated — human approval required before execution |
| **MEDIUM** | 7 | Allowed with logged rationale |
| **LOW** | 83 | Allowed with provenance logging |
| **BLOCKED** | 0 | No hard-blocked prompts found |

### HIGH-Risk Prompts — Human Approval Required

| ID | Title | Risk Reason |
|---|---|---|
| AI-001 | AI Model Risk QA Agent | Jailbreak resistance testing (sensitive scope) |
| AI-002 | AI App Code Security Agent | Data exfiltration path analysis |
| MOB-QA-001 | Mobile App Security QA | Jailbreak/root behavior testing |
| AIRT-016 | Red Team Prompt Agent | Red team attack scenario generation |
| AUD-003 | Continuous Monitoring Auditor | Network scan scope |
| DEV-003 | Secrets Detection Agent | Credential exposure theme |
| DEV-004 | Container Security Agent | Network scan scope |
| DEV-006 | IaC Security Agent | Network scan scope |
| DOD-002 | RMF Package Agent | Network scan scope |
| RET-001 | E-commerce Abuse Tester | Exploit execution theme |
| IAM-009 | Cloud IAM Auditor | Privilege escalation analysis |
| BREAK-021 | Build Breaker Agent | Network scan + CI disruption scope |
| RATE-026 | API Rate Limit Abuse Agent | Brute force / enumeration theme |

### MEDIUM-Risk Prompts — Allowed With Logged Rationale

| ID | Title | Risk Reason |
|---|---|---|
| SAST-001 | Static Code Security Reviewer | Auth bypass + secret pattern references |
| DAST-002 | API DAST Agent | Injection theme |
| DAST-003 | Authentication Flow Tester | Bypass theme |
| DOD-003 | Mission Software Secure Code Agent | Secret + injection references |
| DBSEC-010 | Database Security Agent | Delete + injection theme |
| AUTHZ-027 | Authorization Matrix Agent | Bypass + privilege theme |
| IND-015 | RAG Security Agent | Injection + bypass theme |

### Safety Note on Jailbreak References

The 3 prompts flagged for `jailbreak` keyword all use it in a **defensive context**:
- AI-001: "jailbreak *resistance*" — evaluating model defense, not attacking
- MOB-QA-001: "jailbreak/root *behavior*" — standard iOS/Android security assessment
- AIRT-016: "jailbreak, and policy bypass *testing*" — supervised red-team scenario generation

**Classification:** HIGH (requires approval) — not BLOCKED.

**Finding: 0 actual jailbreak instructions found. Library is clean and well-formed.**

---

## Agent Usage Policy

Agents may use the prompt library only under this policy:

| Rule | Policy |
|---|---|
| 1 | Prompt library is **read-only** by default. No agent may write, modify, or delete library files. |
| 2 | Agents may **search and retrieve** prompts by id, category, industry, title, or mission keyword. |
| 3 | Agents may **not execute prompts blindly**. A prompt must be explicitly selected, classified, and logged before use. |
| 4 | Agents must select prompts by **category, mission alignment, and risk level** — not arbitrary retrieval. |
| 5 | For **HIGH-risk** actions, agent must surface selected prompt ID, title, and risk rationale to operator before use. |
| 6 | Any prompt involving deletion, credentials, external network calls, exploit testing, scanning, deployment, or production changes **requires human approval** via `POST /api/v1/prompts/approve`. |
| 7 | Prompt output must be treated as **advisory** until validated by a human or downstream gate. |
| 8 | Every prompt use must be **logged to the swarm ledger** with: prompt ID, hash, category, agent, mission, timestamp, approver. |
| 9 | **Prompt provenance** must include: file path, prompt SHA-256, category, selected agent, timestamp. |
| 10 | Prompts containing actual jailbreak instructions, bypass commands, credential exposure code, destructive commands, or unsafe automation language are **BLOCKED** without security officer approval and audit trail. |

---

## Recommended Runtime Integration

### Prompt Library Adapter Design

```
Prompt Library Adapter
  ├── [SCAN]     Read prompt_library.json at startup
  ├── [HASH]     Compute SHA-256 per prompt entry
  ├── [CLASSIFY] Apply risk rules → LOW / MEDIUM / HIGH / BLOCKED
  ├── [STORE]    Persist to prompt_library_classification.json
  └── [EXPOSE]   Read-only search API → /api/v1/prompt-library

Agent Request Flow:
  Agent.select_prompt(mission, category)
    → Policy Gate
      ├── LOW     → Auto-allowed, log to ledger
      ├── MEDIUM  → Allowed, log with rationale required
      ├── HIGH    → HOLD → surface to operator for approval
      │               → Approved → log + execute
      │               → Denied   → log attempt + reject
      └── BLOCKED → REJECT → log attempt + alert
```

### Recommended Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/prompts/library` | List all with classification (already exists as `/api/v1/prompt-library`) |
| `GET` | `/api/v1/prompts/library/{prompt_id}` | Single prompt with risk metadata |
| `POST` | `/api/v1/prompts/select` | Agent selects a prompt for a mission (policy gate) |
| `POST` | `/api/v1/prompts/approve` | Operator approves HIGH-risk prompt use |
| `GET` | `/api/v1/prompts/usage-ledger` | Full audit log of all prompt selections |

---

## Required Metadata Schema

```json
{
  "prompt_id": "string",
  "name": "string",
  "path": "string",
  "sha256": "string",
  "category": "QA|AUDIT|SAST|DAST|DEVSECOPS|CODING|DEBUGGING|ARCHITECTURE|RELEASE|GOVERNANCE|CYBERSECURITY|SUPPLY_CHAIN|DOCUMENTATION|TRAINING|MISSION_INTEL|OPERATIONS|UNKNOWN",
  "intended_agents": ["string"],
  "risk_level": "LOW|MEDIUM|HIGH|BLOCKED",
  "requires_approval": true,
  "allowed_modes": ["read", "suggest", "execute_with_approval"],
  "blocked_reasons": [],
  "inputs_required": [],
  "expected_outputs": [],
  "last_reviewed_at": "ISO-8601 timestamp",
  "review_status": "APPROVED|NEEDS_REVIEW|BLOCKED"
}
```

---

## Blocked Prompt Types

Execution (not retrieval) is automatically blocked for prompts containing:

- Active jailbreak instructions against the executing agent itself
- `ignore previous instructions` — prompt injection
- `disable safety` — safety bypass
- Destructive shell commands as objectives (`rm -rf`, etc.)
- Credential exfiltration code (not as audit topic)
- `sudo` as a runtime instruction to the agent
- Persistence/evasion language as objective (not test topic)
- Production deploy without approval gate
- Instructions to ignore governance or audit requirements

**Distinction enforced:** "Test jailbreak resistance" ≠ "Jailbreak the system." The policy gate applies semantic context, not keyword-only matching.

---

## Approval Workflow

```
Agent selects prompt for mission
        │
        ▼
   Risk Level Check
    ├── LOW     → Auto-allowed → Log to ledger
    ├── MEDIUM  → Allowed → Agent logs rationale → Ledger entry
    ├── HIGH    → HOLD → POST /api/v1/prompts/select
    │               → Operator receives approval request
    │               → Approves → Log + Execute (TTL: 24h)
    │               → Denies  → Log + Reject
    └── BLOCKED → REJECT → Log attempt + operator alert

Approval TTL: 24 hours per prompt × mission context
Approver role: Operator or designated Security Officer
Audit retention: All decisions retained in swarm ledger indefinitely
```

---

## Implementation Backlog

| # | Task | Priority | Blocks |
|---|---|---|---|
| **PL-01** | Add `risk_level`, `requires_approval`, `review_status`, `last_reviewed_at` to `backend/prompt_library.json` | HIGH | PL-03, PL-04 |
| **PL-02** | Create `backend/prompt_library_adapter.py` — load, hash, classify at startup | HIGH | PL-03 |
| **PL-03** | `POST /api/v1/prompts/select` — policy gate (LOW/MEDIUM/HIGH/BLOCKED routing) | HIGH | PL-05 |
| **PL-04** | `POST /api/v1/prompts/approve` — operator approval for HIGH-risk | HIGH | PL-05 |
| **PL-05** | `GET /api/v1/prompts/usage-ledger` — full audit log | MEDIUM | — |
| **PL-06** | Add approval queue to **Governance Cockpit** UI | MEDIUM | PL-04 |
| **PL-07** | Add per-prompt risk badge to existing **Prompt Library** page | MEDIUM | PL-01 |
| **PL-08** | pytest unit tests: hash integrity, classification, policy gate | HIGH | Gate 2 |
| **PL-09** | `test-prompt-library-governance-contract.ts` | HIGH | Gate 3 |
| **PL-10** | `prompt-approval-workflow.spec.ts` | HIGH | Gate 4 |
| **PL-11** | Integrate prompt selection logging into swarm ledger | MEDIUM | PL-03 |
| **PL-12** | Stamp `last_reviewed_at` on all 103 prompts after human sign-off | LOW | PL-01 |
| **PL-13** | Add `intended_agents` field to all prompts | LOW | PL-02 |
| **PL-14** | Startup hash comparison: detect if `backend/prompt_library.json` drifts from source | LOW | PL-02 |

---

*Generated by HOCH QA Test Strategy Architect — 2026-06-26*  
*Evidence: `prompt_library_files.txt`, `prompt_library_prompt_files.txt`, `prompt_library_risk_scan.log`, `prompt_library_classification.json`*
