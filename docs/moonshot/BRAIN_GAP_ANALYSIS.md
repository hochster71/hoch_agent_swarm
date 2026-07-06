# BRAIN Gap Analysis

- generation: **16**  |  mean champion score: **68.846**  |  state: **PLATEAUING**
- gene classes: **30**  |  champion classes: **26**  |  total genes: **479**
- concentration (top-5 share of gene pool): **60.3%**
- policy: min_pool=6, target_score=70.0

## Binding constraint by class

| constraint | classes |
|---|---|
| LOW_CEILING | 16 |
| SATURATED | 10 |
| NO_CHAMPION | 4 |

**Synthetic genes needed to lift every thin class to min_pool: 0**

## Thin classes (quantity-capped — expansion lever)

| class | genes | need | score |
|---|---|---|---|

## Low-ceiling classes (adequate pool, quality lever)

| class | genes | score |
|---|---|---|
| Industry Specialized | 15 | 50.0 |
| Supply Chain | 6 | 57.5 |
| Vulnerability Management | 6 | 60.0 |
| AI / ML | 51 | 62.5 |
| Governance / Compliance | 50 | 62.5 |
| Infrastructure & Hardware | 7 | 62.5 |
| Research & Delivery | 8 | 62.5 |
| Software Engineering | 6 | 62.5 |
| AI / ML Systems | 6 | 67.5 |
| Cloud Security | 6 | 67.5 |
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
