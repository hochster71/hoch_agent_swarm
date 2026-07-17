# Factory Audit — HELM OMEGA ASSURANCE AUDIT v1.0

Factories in scope: **HASF, HRF, HCF, HMF, HSF, HFF, HHF, HPF**

Sources: `coordination/council/factory_registry.json`, `docs/founder/FACTORY_READINESS_BOARD.md` (2026-07-17), disk inventory under `products/` and `hsf/`, revenue ledger, live homepage probes reported by readiness board.

---

## Maturity Scale (board)

0 IDEA · 1 PROTOTYPE · 2 BUILT_NOT_SELLABLE · 3 PRODUCTIZED_DEFINED · 4 SELLABLE · 5 EARNING

---

## Portfolio Matrix

| Factory | Registry health/readiness | Board observed rung | Source on disk (this audit) | Live sellable? | Settled $ | Classification |
|---|---|---|---|---|---|---|
| **HASF** | ACTIVE / READY | Epic Fury page-based checkout rung 4 | Epic Fury source **clobber-guarded / not in this monorepo path** per board | Homepage 200 (board) | $0 settled (PENDING 18.1) | **LIVE product surface; mission BLOCKED; not earning settled** |
| **HSF** | ACTIVE / READY | Story Studio rung 4 SELLABLE | `hsf/deploy` **exists** (26 files) | Stripe checkout URL probe PASS (board) | $0 settled | **SELLABLE surface; earning NOT PROVEN** |
| **HCF** | ACTIVE / READY | CyberQRG rung 2 BUILT | `products/cyberqrg-ai` **exists** | No live URL declared | $0 | **BUILT / not sellable live** |
| **HMF** | ACTIVE / READY | Cue Library rung 1 | `products/hmf-cue-library` **exists** (audio empty by design per commits) | No | $0 | **PROTOTYPE / PLACEHOLDER catalog** |
| **HRF** | ACTIVE / READY | Clarity Briefs rung 1 | `products/hrf-clarity-briefs` **exists** | No | $0 | **PROTOTYPE / early** |
| **HFF** | UNKNOWN / NOT_READY | Runway rung 1 (board path mismatch) | `products/hff-runway` + `hff-invoice-aging` **exist** (large trees) | No | $0 | **CODE PRESENT; board under-reports path; not sellable** |
| **HHF** | UNKNOWN / NOT_READY | Not on readiness board products table | No product dir confirmed | No | $0 | **UNKNOWN / NOT IMPLEMENTED as product** |
| **HPF** | UNKNOWN / NOT_READY | Not on readiness board products table | No product dir confirmed | No | $0 | **UNKNOWN / NOT IMPLEMENTED as product** |

---

## Critical Conflicts

### F-CONFLICT-1 — Registry READY vs operational maturity

Registry marks HSF/HMF/HRF/HCF **READY** while readiness board scores several at rung 1–2.  
**Evidence overrides registry narrative.** Registry readiness is **NOT TRUSTED** as operational proof.

### F-CONFLICT-2 — Readiness board “source on disk ❌” vs filesystem

Board marks HFF/HMF/HRF source missing for *declared product paths*, but monorepo contains `products/hff-runway`, `products/hmf-cue-library`, `products/hrf-clarity-briefs`.  
**Either path mapping is wrong or board intentionally ignores undeclared trees.** Status: **AUTHORITY SPLIT — NOT VERIFIED which path is canonical for deploy guard.**

### F-CONFLICT-3 — PENDING revenue ≠ EARNING

Revenue ledger: one **PENDING** Epic Fury-related Stripe entry. Mission state correctly refuses settled earning.  
Any claim of “first dollar settled” is **NOT SUPPORTED**.

---

## Per-Factory Notes

### HASF
- Role: swarm/control-plane factory + champion Epic Fury.
- Mission overall blocked on governance binding REQ-GOV-002.
- Testing area claims VERIFIED with ~107h-old evidence package — aging.

### HSF (Story Studio)
- Strongest commercial path after Epic Fury page surface.
- `hsf/deploy` tests present (`package.json` test script).
- Doorstep contract in registry: **NONE** (weaker than HASF founder signature) — governance inconsistency.

### HCF
- Source present; staged for Stripe/deploy via `factory_to_money.sh` (founder `--go`).
- Best **next guarded deploy candidate** per readiness board.

### HMF / HRF / HFF
- Engines and tests partially present (commits claim suite greens).
- Not live sellable; HMF ships zero audio by design (honest).

### HHF / HPF
- Registry stubs only effectively; **not productized**.

---

## Factory Portfolio Maturity Score: **35 / 100**

| Subscore | Value |
|---|---:|
| Code existence | 55 |
| Live sellable paths | 40 |
| Settled monetization | 5 |
| Registry honesty | 25 |
| Deploy guard alignment | 40 |
