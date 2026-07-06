# BRAIN Gap Analysis

- generation: **13**  |  mean champion score: **67.019**  |  state: **IMPROVING**
- gene classes: **30**  |  champion classes: **26**  |  total genes: **461**
- concentration (top-5 share of gene pool): **62.7%**
- policy: min_pool=6, target_score=70.0

## Binding constraint by class

| constraint | classes |
|---|---|
| LOW_CEILING | 14 |
| SATURATED | 7 |
| THIN_POOL | 7 |
| NO_CHAMPION | 2 |

**Synthetic genes needed to lift every thin class to min_pool: 18**

## Thin classes (quantity-capped — expansion lever)

| class | genes | need | score |
|---|---|---|---|
| Vulnerability Management | 2 | +4 | 60.0 |
| Coding | 3 | +3 | 75.0 |
| Detection Engineering | 3 | +3 | 80.0 |
| Incident Response | 3 | +3 | 55.0 |
| Software Engineering | 3 | +3 | 62.5 |
| DAST | 5 | +1 | None |
| Family & Personal | 5 | +1 | None |

## Low-ceiling classes (adequate pool, quality lever)

| class | genes | score |
|---|---|---|
| Supply Chain | 6 | 45.0 |
| Industry Specialized | 15 | 50.0 |
| Cloud Security | 6 | 57.5 |
| AI / ML | 51 | 62.5 |
| Governance / Compliance | 50 | 62.5 |
| Infrastructure & Hardware | 7 | 62.5 |
| Research & Delivery | 8 | 62.5 |
| AI / ML Systems | 6 | 67.5 |
| Governance | 6 | 67.5 |
| Operations | 41 | 67.5 |
| Privacy | 6 | 67.5 |
| SAST | 6 | 67.5 |
| SDLC Governance | 8 | 67.5 |
| Security Architecture | 18 | 67.5 |

## Taxonomy drift (merge candidates)

| a | b | similarity |
|---|---|---|
| AI / ML | AI / ML Systems | 1.0 |
| Governance / Compliance | Governance | 1.0 |
| SDLC Governance | Governance | 1.0 |
