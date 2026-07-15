# HELM Voice V2 — Extended Factory Observe + CISO Deep-Bind

**Date:** 2026-07-15  
**Doctrine:** no_fake_green  

## Delivered

| Code | Observe source | Status class |
|------|----------------|--------------|
| HSF | `hsf/deploy` pricing, vercel, Stripe env SET/PLACEHOLDER/MISSING (no secret values) | PARTIAL; revenue UNKNOWN |
| HCF | `helm_control_posture.json`, cyber_swarm_state, conmon ledger, goal blocker | PARTIAL |
| HFF | spend meter + northstar + HSF stripe path | PARTIAL; revenue UNKNOWN |
| HPF | prompt_brain genes/champions/convergence | PARTIAL |
| HHF | homemesh device tracker if present | PARTIAL/UNKNOWN |

| Role | Enhancement |
|------|-------------|
| ciso | Deep-binds HCF observe + REQ-CP-SECURITY messaging |
| cfo | HSF stripe path + explicit revenue UNKNOWN |

UI mounts: roadmap, pert, jspace_console, command (+ prior voice/console/founder/helm).

## Verification

```bash
.venv/bin/pytest tests/unit/test_helm_voice_executive.py -q
```
