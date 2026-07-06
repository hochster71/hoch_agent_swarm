# BRAIN Gap Analysis

- generation: **11**  |  mean champion score: **60.769**  |  state: **STALLED_NO_IMPROVER**
- gene classes: **30**  |  champion classes: **26**  |  total genes: **427**
- concentration (top-5 share of gene pool): **67.7%**
- policy: min_pool=6, target_score=70.0

## Binding constraint by class

| constraint | classes |
|---|---|
| THIN_POOL | 15 |
| LOW_CEILING | 10 |
| SATURATED | 5 |

**Synthetic genes needed to lift every thin class to min_pool: 52**

## Thin classes (quantity-capped — expansion lever)

| class | genes | need | score |
|---|---|---|---|
| Legal / Compliance | 1 | +5 | None |
| UX Security | 1 | +5 | None |
| AI / ML Systems | 2 | +4 | 40.0 |
| Cloud Security | 2 | +4 | 57.5 |
| Data Security | 2 | +4 | 72.5 |
| Governance | 2 | +4 | 67.5 |
| Privacy | 2 | +4 | 47.5 |
| Supply Chain | 2 | +4 | 45.0 |
| Vulnerability Management | 2 | +4 | 60.0 |
| Coding | 3 | +3 | 45.0 |
| Detection Engineering | 3 | +3 | 80.0 |
| Incident Response | 3 | +3 | 55.0 |
| Software Engineering | 3 | +3 | 62.5 |
| DAST | 5 | +1 | None |
| Family & Personal | 5 | +1 | None |

## Low-ceiling classes (adequate pool, quality lever)

| class | genes | score |
|---|---|---|
| SDLC Governance | 8 | 40.0 |
| Security Architecture | 18 | 45.0 |
| Industry Specialized | 15 | 50.0 |
| AI / ML | 51 | 62.5 |
| DevSecOps | 58 | 62.5 |
| Governance / Compliance | 50 | 62.5 |
| Infrastructure & Hardware | 7 | 62.5 |
| Operations | 41 | 62.5 |
| Research & Delivery | 8 | 62.5 |
| SAST | 6 | 67.5 |

## Taxonomy drift (merge candidates)

| a | b | similarity |
|---|---|---|
| AI / ML | AI / ML Systems | 1.0 |
| Governance / Compliance | Governance | 1.0 |
| SDLC Governance | Governance | 1.0 |
