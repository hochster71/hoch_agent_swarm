# HAS Model & Compute Baseline (set 2026-07-07)

The settled baseline so we're not scrambling later. Two layers: **which models** and **which compute**.

## Model baseline (auto-resolved + verified)
Managed by `scripts/model_upgrade.py` → `model_registry.json`. The engine reads it; upgrades need no code edits.

| Tier | Model | Role | Status |
|---|---|---|---|
| **frontier** | `gpt-5.5` | hard / develop / escalated tasks | verified ✓ |
| **cheap** | `gpt-5.4-mini` | research · design · code · verify (the workhorse) | verified ✓ |
| **gemini** | `gemini-2.5-flash` | free-tier bonus only | unverified (free-tier 429 — needs billing) |
| **local** | Ollama fleet | offline fallback | optional |

**Scenario proof (2026-07-07):** gpt-5.4-mini wrote a correct optimized `is_prime()` in 2.1s;
gpt-5.5 answered a strategy question sharply in 3.0s. Both fractions of a cent, under the $100/mo cap.

**Self-upgrade:** the station queries the provider's live model list weekly, smoke-tests the newest
capable model, and promotes it only if it responds (never downgrades to a broken model). When
gpt-5.6 / gpt-6 / Gemini 3 ship, HAS adopts them automatically. Audit trail: `model_upgrade_audit.jsonl`.

## Compute baseline — "cloud relay, local intelligence, burst acceleration"
Relay provider confirmed: **Akamai Connected Cloud (Linode)**.

- **Tier 1 — always-on control plane (live):** relay-001 on Linode runs the API, dashboards,
  `/api/live` + `/api/northstar`, evidence, burn-in daemon. ~$5–40/mo. This is the brainstem.
- **Tier 2 — intelligence (now the API baseline):** with `gpt-5.4-mini` / `gpt-5.5` doing coding &
  research at pennies, **you no longer need heavy local models for text work** — that alone takes the
  heavy compute off the MacBook. Local Ollama becomes an optional offline fallback.
- **Tier 3 — burst GPU (only when needed):** for private/local heavy inference or image/music/video.
  Spin up per-job, then shut down. Never idle.

### Akamai/Linode GPU options (burst, not always-on)
| GPU | VRAM | ~$/hr | Fit |
|---|---|---|---|
| RTX 4000 Ada | 16 GB | ~$0.52 | 7–14B models, light image |
| Quadro RTX 6000 | 24 GB | ~$1.50 | ~30B quantized, sustained |
| RTX PRO 6000 Blackwell | 96 GB | ~$3.50 | 70B+/120B, heavy batch (limited availability) |

Always-on GPU is **not** recommended (the 96 GB card ≈ $2,500/mo). For occasional bursts, RunPod
RTX 4090 (~$0.34–0.59/hr) is typically cheaper than Linode for the same job.

### Recommendation
1. **Run text work on the API baseline** (gpt-5.4-mini / gpt-5.5) — heavy compute already off the Mac, pennies, capped.
2. **Keep the cheap Linode relay** for the 24/7 control plane; bump to a ~$60/mo Dedicated-CPU plan only if orchestration needs more headroom (CPU can't run big LLMs — that's fine, it doesn't need to).
3. **Add burst GPU as a queued job type** only for private inference / media generation, with a hard monthly cap. No always-on GPU until revenue.

Net monthly: **$10–60 (Phase 1)**, **$75–200 with occasional burst** — well under the $325–635 "always-on GPU" trap.

Sources: [Akamai GPU Linodes](https://techdocs.akamai.com/cloud-computing/docs/gpu-compute-instances) · [Akamai Cloud GPU pricing](https://computeprices.com/providers/akamai-cloud)
