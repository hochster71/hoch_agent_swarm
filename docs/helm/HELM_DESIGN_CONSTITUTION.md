# HELM DESIGN CONSTITUTION
### The constitutional principles governing every HELM subsystem — UI, Voice, Automation, Cybersecurity, and AI reasoning.
> Ratified by Michael Hoch, 2026-07-17. This is the highest design authority in HELM. It supersedes any individual screen, technology, or preference. Traditional dashboards ask "what is happening?" — HELM answers "what is happening, why, what evidence proves it, and what action is required?"

---

## Principle I — Truth in Motion
No visualization, animation, sound, transition, or executive indicator shall exist without an authoritative runtime event or evidence source. **Motion is not decoration. Motion is telemetry.**

## Principle II — Runtime Truth First
The runtime is authoritative. Documentation is explanatory. Models are advisory. Visualizations are observational. **If they disagree, runtime wins.**

## Principle III — Evidence Before Confidence
Confidence is earned. Every operational claim must trace to: runtime state · telemetry · evidence · verification · governance. **Never to assumptions.**

## Principle IV — Explain Causality
Every change must answer: What changed? Why? What caused it? What evidence supports it? What happens next? **HELM visualizes causes, not just outcomes.**

## Principle V — Honest Uncertainty
HELM never hides uncertainty. It distinguishes these as **operational states with defined meanings** (not cosmetic labels):
- **VERIFIED** — confirmed by authoritative evidence, fresh.
- **OBSERVED** — measured/seen live, not independently verified.
- **ESTIMATED** — computed/inferred; label as such, show basis.
- **STALE** — was true; past its freshness SLA; show last-known timestamp.
- **UNKNOWN** — no authoritative source; renders dark; never counted as green.
- **BLOCKED_EXTERNAL** — complete internally; awaiting an external party's authoritative action (Apple review, Stripe settlement, ATO, DNS, third-party API). Never claimed complete until that external evidence confirms it.

---

## The Five Design Questions (mandatory review gates for EVERY new visualization/indicator)
1. **What operational decision does this help someone make?** If "none," it doesn't belong.
2. **What authoritative event or evidence drives it?** If no authoritative source exists, it must not animate.
3. **If the runtime event stopped, would the visualization stop?** If not, it's artificial — redesign it.
4. **Could this visualization ever mislead an executive under stress?** If yes, simplify it. Clarity over complexity under pressure.
5. **(NO-FAKE-GREEN)** Does it ever render green/OK on absent or stale evidence? If yes, it must render the honest state (UNKNOWN/STALE/BLOCKED_EXTERNAL) instead.

---

## The HELM Digital Nervous System (unifying architecture)
One operational reality; no duplicate truths; no UI-specific or voice-specific logic. Every subsystem consumes the SAME event stream:

```
Runtime Event → Event Bus → Policy Engine → Mission State → Evidence Ledger
   → Visualization Engine → Voice → Executive Dashboard → Cyber Command
   → Mission Timeline → Factory Galaxy → Knowledge Galaxy
```

Voice, dashboard, CLI, API, and cyber views are all *renderers* of the one event stream + mission state. A subsystem may only present what it can trace to an authoritative event/evidence source.

---

## Evidence-triggered external-milestone state machines (Principle V in code)
External milestones hold at BLOCKED_EXTERNAL and advance ONLY on authoritative evidence:
- **Release:** `BLOCKED_EXTERNAL → APPLE_APPROVED → READY_FOR_RELEASE → LIVE` (source: App Store Connect API version state).
- **Revenue:** `CHECKOUT_CREATED → PAYMENT_AUTHORIZED → SETTLED → REVENUE_VERIFIED` (source: Stripe balance-transaction settlement).
Implementation: `backend/truth/external_milestones.py` + `/api/v1/helm/external`; the 7/22 Stripe settlement watcher + ASC review poll drive the transitions.

---

## What this becomes
Not "an app." A **design discipline for AI-native operational systems** — a coherent visual and operational language, honest by construction, that scales as HELM grows without depending on any single screen or technology. **Truth. Evidence. Governance. Mission.**
