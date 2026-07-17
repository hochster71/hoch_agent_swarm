# HELM ROADMAP — post-ratification operating model

> Governed under `HELM_CONSTITUTION_v1.0.md` (RATIFIED 2026-07-17, architecture &
> governance). **The architecture phase is declared COMPLETE.** From here the
> emphasis is building, verifying, and operating against the baseline — not
> inventing architecture. Changes to the architecture occur only via EDR (Article IX).

## Permanent qualifier (never removed)
**Architecture ratified. Implementation conformance pending independent verification.**
Governance and evidence are separate: the Constitution governs; conformance is
measured by independent audit and never assumed.

## Standard Worker Session Flow (every worker, every session)
```
Load Constitution → Load applicable EDRs → Load current Mission Runtime →
Load Runtime Truth → Execute assigned work → Produce evidence → Request verification
```
No giant prompts. No architecture redesign. No "remember everything." The
Constitution and the Knowledge Engine replace reliance on prior conversations.

## Governed operating hierarchy
```
Michael → Executive Decisions → HELM Constitution → EDRs → Knowledge Engine →
Mission Runtime → Runtime Truth Engine → Dispatch Gateway →
[ OpenAI · Anthropic · xAI · Ollama · … ] → Shared Evidence → Executive Operations Center
```
Everything **below** the Constitution evolves; the Constitution changes only by amendment.

## Phases

### Phase A — Governance ✅ COMPLETE
Constitution v1.0 · EDR process · Founder ratification · Frozen baseline.
Artifacts: `HELM_CONSTITUTION_v1.0.md`, `FOUNDER_RATIFICATION.md`,
`CONSTITUTION_CONFORMANCE_REPORT.md`, `HELM_PLATFORM_RELEASE_v1.0.0-alpha.yaml`,
EDR-0001, EDR-0002.

### Phase B — Knowledge  ◀ largest remaining constitutional gap
The **Knowledge Engine**: the authoritative, governed source of organizational
memory so every worker (Claude, ChatGPT, Grok, Ollama, LM Studio) retrieves the
same knowledge instead of depending on prior chats. Scope: Constitution · EDRs ·
runbooks · cyber mappings · mission history · lessons learned · factory specs ·
runtime docs · verification artifacts. Work: semantic indexing · retrieval ·
cross-model memory. *Constitution Article I layer 5 — currently PLANNED. Requires a
Knowledge Engine EDR before implementation.*

### Phase C — Runtime
Mission Runtime · Dispatch enablement (founder-gated credentials) · Worker roster
expansion · autonomous execution loops. Builds on the existing substrate
(IMPLEMENTED / skeleton) toward operation.

### Phase D — Verification
Independent implementation audit (Auditor confirms code matches the Constitution) ·
conformance · Continuous Monitoring · drift detection. *Founder's standing priority:
independent verification is prerequisite to trusting any "implemented" claim.*

### Phase E — Factory Expansion
HASF · HRF · HMF · HSF · Finance · Cyber · Research · Applications — as **plugins**
that consume runtime services and never duplicate the runtime (Constitution Article VIII).

## Release Trains (platform versioning, not "keep building")
HELM ships as **platform releases**; the phases map to a release train:
```
HELM 1.0.0-alpha   Governance Frozen         (Constitution ratified) ← current
      ↓
HELM 1.0.0-beta    Knowledge Engine          (Phase B — Governed Retrieval)
      ↓
HELM 1.0.0-rc1     Dispatch Enabled          (Phase C — founder-gated credentials)
      ↓
HELM 1.0.0         Executive Runtime Operational
```
**Factories version independently** from HELM Core, so the platform stays stable while
factories evolve at their own speed:
```
HELM Core 1.x   ·   HASF 1.x   ·   HRF 1.x   ·   HMF 1.x   ·   HSF 1.x   · …
```
A factory is a plugin (Constitution Article VIII); its version advances without forcing a
HELM Core release, and HELM Core advances without forcing a factory release.

## Open sequencing decision (founder)
The prior founder priority put **independent verification first**; this roadmap lists
Knowledge (B) before Verification (D). These can run in either order or in parallel —
recorded here as an explicit founder decision rather than a silent assumption.

*Amendments to the architecture occur only via EDR. This roadmap may be revised as a
governance document without an EDR, since it schedules work against the frozen baseline
rather than changing it.*
