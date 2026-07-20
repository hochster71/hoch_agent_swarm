# HAS Tech Scout — 2026-07-20

Scope: last ~7 days, dev communities + vendor changelogs. Relevance filter: hands-off delivery to the doorstep, Epic Fury / Story Studio revenue.
Research only. Nothing installed, deployed, or spent. Actionable items flagged FOUNDER-REVIEW.

Note: several searches returned tool errors this run (HN and Reddit queries failed). Coverage is vendor-changelog + GitHub + dev-blog heavy this week. UNVERIFIED tags used where a claim is a secondary-source assertion I could not confirm at the primary source.

---

## Top 5

### 1. Harness Evolver / Harness Forge — self-optimizing agent scaffolding
What: Claude Code plugins that run a propose → score → keep-Pareto-best loop over the *scaffolding* (system prompts, routing, retrieval, context construction, tool selection) around a fixed model, in isolated git worktrees. Based on Meta-Harness (Lee et al., 2026).
Benefit: This is the most direct answer to "make HAS better without me tuning prompts by hand." The model stays fixed; the harness improves against a scored objective.
Catch: Needs a real scoring function. Harness Evolver is LangSmith-backed — that's an external dependency and a data-egress decision. Meta-Harness results are a 2026 paper claim; the plugins' effectiveness on a swarm like HAS is UNVERIFIED. Evolution loops burn tokens.
How HAS would use it: Point it at the HAS agent role overlays with "verified doorstep deliveries per founder-touch" as the score. FOUNDER-REVIEW — this modifies agent code, which is outside scout authority.
- https://github.com/raphaelchristi/harness-evolver
- https://github.com/001TMF/harness-forge
- https://arxiv.org/html/2606.14249 (HarnessX, adjacent)

### 2. app-publish-mcp — App Store Connect + Google Play from an agent
What: One MCP server, 91 tools (56 Apple / 35 Google): listings, screenshots, releases, review submission, review replies, phased rollout.
Benefit: Turns the Epic Fury / Story Studio store path from a browser-console task into a scriptable one. That is exactly the class of work CLAUDE.md says should be automated instead of handed back as a step list.
Catch: Does **not** remove the founder gates — Apple identity, 2FA, and legal attestation still require Michael. Third-party repo holding App Store Connect API keys is a real trust decision; audit before granting. The "45 min → 2 min" figure is a blog claim. UNVERIFIED.
How HAS would use it: Wire as the mechanical layer under the existing `r2-appstore-submit` doorstep item — HAS prepares and stages the whole submission, Michael's click submits. FOUNDER-REVIEW (credential grant).
- https://github.com/mikusnuz/app-publish-mcp/
- https://dev.to/alanwest/your-ai-can-submit-apps-to-the-app-store-now-no-seriously-4556

### 3. Claude Code v2.1.207–212 — background `/fork`, `/subtask`, WebSearch cap, EndConversation
What: `/fork` now spawns a real background session (own row in `claude agents`) while you keep working; the old in-session subagent is `/subtask`. Session-wide WebSearch cap (default 200, `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`). New EndConversation tool + progress heartbeats for long tasks. `/verify` and `/code-review` no longer self-trigger.
Benefit: Background `/fork` is native parallelism for the swarm without bespoke orchestration. Heartbeats + EndConversation make long autonomous builds observable and terminable. The search cap is a real runaway-cost guard.
Catch: The `/verify` change is a regression risk for anyone relying on auto-verification — HAS must invoke verification explicitly now or gates silently stop running.
How HAS would use it: Move parallel build/audit lanes onto background `/fork`; add an explicit `/verify` call to any HAS loop that assumed it fired automatically. FOUNDER-REVIEW — check whether HAS loops assumed auto-`/verify`.
- https://code.claude.com/docs/en/changelog
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md

### 4. Stripe Sessions 2026 — Managed Payments (merchant of record) for all digital businesses
What: Managed Payments — Stripe as merchant of record — now open to all digital businesses: indirect tax compliance in 80+ countries, fraud, disputes, customer support. Plus iOS/Android developers can collect via Stripe directly with full pricing control, and new usage-based/credits plan primitives.
Benefit: For a solo founder shipping paid apps in multiple countries, MoR removes the single ugliest non-code blocker — global tax registration. Direct in-app collection means pricing isn't hostage to store terms.
Catch: MoR takes a cut above standard processing; the actual rate for HELM's volume is UNVERIFIED. In-app payment routing outside the App Store has jurisdiction-dependent Apple rules — do not assume it's permitted everywhere.
How HAS would use it: Evaluate MoR for Story Studio before the first settled dollar, so the revenue path (`CHECKOUT_CREATED → SETTLED`) doesn't later need re-plumbing. FOUNDER-REVIEW — pricing/legal decision, plus a spend.
- https://stripe.com/blog/everything-we-announced-at-sessions-2026
- https://stripe.com/blog/building-for-the-next-wave-of-app-monetization

### 5. Loop / harness engineering as a discipline — "Ralph" minimal pattern + agentic evaluators
What: The 2026 consolidation of prompt → context → *harness* engineering. Geoffrey Huntley's "Ralph" is the minimalist reference: single-task loops, deterministic prompt stacking, bounded subagent parallelism for long-running autonomous coding. Alongside it: agentic evaluators that inspect generated codebases over multiple rounds rather than trusting a single pass.
Benefit: Cheap, dependency-free, and directly applicable — bounded parallelism and single-task loops are a discipline, not a package to install. Agentic evaluation is the honest version of NO-FAKE-GREEN at the code level.
Catch: Mostly blog-and-curated-list material, not benchmarked. Naive multi-round evaluators multiply token cost. UNVERIFIED as to measured gain.
How HAS would use it: Audit the HAS build loop against the Ralph constraints (is each lane genuinely single-task? is subagent fan-out bounded?) and add an agentic evaluator pass before anything reaches the doorstep.
- https://github.com/ai-boost/awesome-harness-engineering
- https://www.langchain.com/blog/the-anatomy-of-an-agent-harness
- https://tosea.ai/blog/loop-engineering-ai-agents-complete-guide-2026

---

## Also noted, lower rank

- **open-multi-agent** — TypeScript orchestration where a coordinator plans the task DAG at runtime from a stated goal, model-agnostic. Interesting shape; HAS already has its own runtime, so this is reference material, not a swap. https://github.com/open-multi-agent/open-multi-agent
- **Token reduction, consolidated 2026 practice** — compact at ~60% context utilization rather than 90%; every token in CLAUDE.md is paid on every turn; PreToolUse hooks to strip tool-output noise; subagents as context isolation. Reported 40–70% savings, source-claimed, UNVERIFIED. HAS's own CLAUDE.md is large enough that the per-turn cost is worth measuring. https://code.claude.com/docs/en/costs · https://www.kdnuggets.com/7-practical-ways-to-reduce-claude-code-token-usage
- **Claude Code live MCP connector data in published artifacts** — artifacts can now pull live connector data. Relevant to the HAS doorstep tracker as a live page rather than a regenerated file. https://code.claude.com/docs/en/changelog

---

## Coverage gaps this run

- Hacker News and Reddit (r/ClaudeAI, r/LocalLLaMA) searches errored out — no community-sentiment signal this week.
- No X/Twitter dev chatter captured.
- Anthropic changelog detail came via a secondary aggregator alongside the official changelog; version-level claims (v2.1.207–212) should be spot-checked against the primary CHANGELOG before acting.

## Top pick

**Harness Evolver / Harness Forge** — the only item this week that compounds. Everything else removes a blocker once; a working harness-evolution loop makes HAS better every cycle. Gated on defining an honest score function first.
