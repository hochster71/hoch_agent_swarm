# HAS Tech Scout — 2026-07-13

Scan window: ~last 7 days (plus still-fresh May/June items HAS has not adopted). Research only. Nothing installed, deployed, or spent.
First run of this scout — no prior digest to diff against.

## Top 5

### 1. Claude Managed Agents — Outcomes (rubric + independent grader)
- **What:** You write a rubric of what "done" means; a separate grader model evaluates the agent's output in its own context window and sends it back for another pass until it passes. Public beta. ([claude.com/blog/new-in-claude-managed-agents](https://claude.com/blog/new-in-claude-managed-agents))
- **Benefit:** This is exactly the missing piece for hands-off delivery — a machine-checkable definition of "ready for the doorstep" that isn't graded by the same context that wrote the code.
- **Catch:** It's a Managed Agents (platform) feature, not a local Claude Code primitive — adopting it means running swarm work through the platform, and grader passes cost extra tokens. Vendor-reported wins (Wisedocs 50% faster review) are UNVERIFIED by us.
- **HAS use:** Replace the current "founder eyeballs it at the door" gate with an Outcomes rubric per deliverable (e.g. Epic Fury build: compiles, tests green, no founder-gate violations) so only rubric-passing items reach the doorstep.

### 2. Multiagent orchestration (lead agent + parallel specialists on a shared filesystem)
- **What:** Native lead-agent/sub-agent fan-out where specialists run in parallel with their own model/prompt/tools and feed results back into the lead's context. ([claude.com/blog/new-in-claude-managed-agents](https://claude.com/blog/new-in-claude-managed-agents), [platform docs](https://platform.claude.com/docs/en/managed-agents/dreams))
- **Benefit:** Direct platform replacement for hand-rolled swarm orchestration; parallelism cuts wall-clock time on multi-front work (Story Studio + Epic Fury simultaneously).
- **Catch:** Multi-agent pipelines burn 3–15x the tokens of a single call when the specialization isn't actually needed ([niteagent](https://niteagent.com/blog/ai-agent-cost-optimization-2026/)). Fan-out without a cost ceiling is how a swarm eats a month of budget in a weekend.
- **HAS use:** Only fan out when the work is genuinely independent; keep Opus-class on the lead and cheap models on workers (see #3).

### 3. Hierarchical model routing — frontier lead, budget workers
- **What:** Route simple/worker steps to small models and reserve the flagship for the orchestrator. Reported ~97.7% of full-frontier accuracy at ~61% of cost; broader routing analyses claim 60–80% cost reduction. ([niteagent](https://niteagent.com/blog/ai-agent-cost-optimization-2026/), [MindStudio](https://www.mindstudio.ai/blog/ai-agent-token-cost-optimization-multi-model-routing), [obviousworks](https://www.obviousworks.ch/en/token-optimization-saves-up-to-80-percent-llm-costs/))
- **Benefit:** The single highest-leverage cost lever for an always-on swarm. Cost is HAS's real constraint on running hands-off.
- **Catch:** The 97.7%/61% figure is a vendor-blog number, not a paper — treat as **UNVERIFIED**. Quality loss shows up on exactly the hard tasks you'd notice late.
- **HAS use:** Tier the swarm — Haiku-class for file scans, test runs, digest writing; Opus/Fable-class only for planning and code that ships.

### 4. `/checkup` in Claude Code — context-cost audit of skills/MCPs/plugins
- **What:** New Claude Code command that checks install health, finds unused skills/MCP servers/plugins vs. their context cost, dedupes local CLAUDE.md against checked-in ones, and flags slow hooks. ([Claude Code changelog](https://code.claude.com/docs/en/changelog), [release notes](https://support.claude.com/en/articles/12138966-release-notes))
- **Benefit:** Free token savings. HAS carries a large plugin/MCP surface; every unused one is paid for on every single turn of every agent.
- **Catch:** It's an audit, not a fix — it proposes, you prune. Pruning a skill an agent silently relies on is a real footgun.
- **HAS use:** Run `/checkup` against the swarm's config, prune the dead weight, and re-baseline per-run token cost before/after.

### 5. Dreaming — scheduled memory curation between runs
- **What:** A scheduled background process that reviews past agent sessions, extracts patterns, and curates memory stores so agents improve run over run. Research preview. ([claude.com/blog/new-in-claude-managed-agents](https://claude.com/blog/new-in-claude-managed-agents), [Dreams docs](https://platform.claude.com/docs/en/managed-agents/dreams))
- **Benefit:** Platform-native version of the memory/compaction logic HAS would otherwise hand-roll (session summaries, memory.md index).
- **Catch:** Research preview — API and behavior will move. Curated memory is also a silent-corruption risk: a bad pattern learned once gets applied forever, and it's hard to notice.
- **HAS use:** Candidate replacement for the swarm's own memory files — but pin it to a read-only review pass first; do not let it write agent instructions unattended.

## Also seen (lower rank)
- **Concise-output SKILL.md pattern:** a ~10-line skill instructing Claude to drop filler/confirmations, reported ~65% fewer output tokens. Cheap, zero-risk, easy win. Number is **UNVERIFIED** (blog claim). ([buildtolaunch](https://buildtolaunch.substack.com/p/claude-code-token-optimization), [agensi](https://www.agensi.io/learn/how-to-reduce-claude-code-token-usage))
- **Skills marketplaces (VoltAgent/awesome-agent-skills ~1000+, alirezarezvani/claude-skills ~345):** mineable for patterns, but unvetted third-party skills are an injection/context-cost surface. Read, don't install. ([VoltAgent](https://github.com/VoltAgent/awesome-agent-skills), [alirezarezvani](https://github.com/alirezarezvani/claude-skills))
- **Stripe app-to-web checkout + Managed Payments (merchant of record):** post-*Epic v. Apple*, iOS apps can link out to external web checkout, saving up to ~90% of processing/commission fees; Stripe handles VAT/GST/sales tax as MoR. Catch: web checkout converts worse than native IAP — complement, don't replace. Directly relevant to Story Studio / Epic Fury pricing. ([Stripe blog](https://stripe.com/blog/building-for-the-next-wave-of-app-monetization), [Stripe docs](https://docs.stripe.com/mobile/digital-goods), [RevenueCat](https://www.revenuecat.com/blog/engineering/can-you-use-stripe-for-in-app-purchases/))
- **"Loop engineering" / self-verifying agents:** the emerging discipline of agents that run tests, grade themselves against measurable checks, and iterate until green or fail loudly. Same shape as Outcomes (#1), but as a build-it-yourself pattern. ([Addy Osmani](https://addyosmani.com/blog/self-improving-agents/), [Towards AI](https://pub.towardsai.net/loop-engineering-for-ai-agents-building-verifiable-self-correcting-coding-workflows-8b32c72184a1))

## Founder review queue (nothing actioned)
1. Decide whether HAS runs orchestration on Managed Agents (Outcomes + multiagent) or stays hand-rolled. Biggest architectural fork on this list.
2. Approve a model-routing tier table (cheap workers / frontier lead) — biggest cost lever.
3. Approve running `/checkup` and pruning unused skills/MCPs.
4. Story Studio / Epic Fury monetization: Stripe app-to-web vs. native IAP.

## Sources
- https://claude.com/blog/new-in-claude-managed-agents
- https://platform.claude.com/docs/en/managed-agents/dreams
- https://sdtimes.com/ai/new-in-claude-managed-agents-dreaming-outcomes-and-multiagent-orchestration/
- https://code.claude.com/docs/en/changelog
- https://support.claude.com/en/articles/12138966-release-notes
- https://niteagent.com/blog/ai-agent-cost-optimization-2026/
- https://www.mindstudio.ai/blog/ai-agent-token-cost-optimization-multi-model-routing
- https://www.obviousworks.ch/en/token-optimization-saves-up-to-80-percent-llm-costs/
- https://buildtolaunch.substack.com/p/claude-code-token-optimization
- https://www.agensi.io/learn/how-to-reduce-claude-code-token-usage
- https://github.com/VoltAgent/awesome-agent-skills
- https://github.com/alirezarezvani/claude-skills
- https://stripe.com/blog/building-for-the-next-wave-of-app-monetization
- https://docs.stripe.com/mobile/digital-goods
- https://www.revenuecat.com/blog/engineering/can-you-use-stripe-for-in-app-purchases/
- https://addyosmani.com/blog/self-improving-agents/
- https://pub.towardsai.net/loop-engineering-for-ai-agents-building-verifiable-self-correcting-coding-workflows-8b32c72184a1
