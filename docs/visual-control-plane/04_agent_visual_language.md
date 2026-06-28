# Agent Visual Language

Every agent deployed in the HOCH Swarm must represent its task status, boundaries, and performance using this visual card layout and family style sheet.

## Agent Card Layout Schema

Each agent card contains the following telemetry slots:
1. **Header**: Name, Role Title, and active status beacon.
2. **Identity**: Prompt ID (e.g. `PR-001`), Category tag (e.g. `SAST`), and Model used (e.g. `Ollama:mistral`).
3. **Task context**: Active mission details, current task description, loop phase.
4. **Safety profile**: Autonomy level (L1–L4), Risk score (1–10), and Approval required (yes/no).
5. **Quality & Evidence**: Output quality score (e.g. `98%`), and links to generated `evidence_manifest.json`.
6. **Telemetry**: Last heartbeat timestamp, allowed tools list, fail-closed state indicator.

## Agent Visual Families

Agents are styled with dedicated border/indicator accents based on their functional family:

### 1. Planner / Research Family
- **Accent Color**: Blue-White (`#3b82f6` to `#e0f2fe`)
- **Graphics**: Constellation lines, search globe vectors.
- **Roles**: Planner, Researcher, Discovery agents.

### 2. Architect / Builder Family
- **Accent Color**: Violet (`#8b5cf6`)
- **Graphics**: Grids, blueprint overlays, block wireframes.
- **Roles**: Architect, Code Builder, Adapter generators.

### 3. QA Family
- **Accent Color**: Green (`#10b981`)
- **Graphics**: Check matrices, test status beacons.
- **Roles**: QA Auditor, Integration Tester, Regression Checkers.

### 4. Cyber / Red Team Family
- **Accent Color**: Red-Amber (`#ef4444` to `#f59e0b`)
- **Graphics**: Shield panels, crosshair vectors, exposure rings.
- **Roles**: Threat Modeler, Vulnerability Scanner, Penetration Translator.

### 5. Audit / Evidence Family
- **Accent Color**: Grey-Purple (`#a855f7`)
- **Graphics**: Ledger books, lock seals, hash chain links.
- **Roles**: Evidence Gatherer, Compliance Signer, Ledger recorder.

### 6. ConMon / SRE Family
- **Accent Color**: Teal (`#0d9488`)
- **Graphics**: Heartbeat lines, gauge circles, error-budget bars.
- **Roles**: Health Daemon, Port Scanner, Resource Monitor.

### 7. App Factory Family
- **Accent Color**: Cyan (`#06b6d4`)
- **Graphics**: Pipeline slots, assembly cell outlines.
- **Roles**: Compiler, Packager, App-Store deployer.

### 8. Family / Home Family
- **Accent Color**: Soft Moonlight (`#f1f5f9` with low opacity)
- **Graphics**: Home silhouettes, child lock shields, privacy badges.
- **Roles**: Household scheduler, smart-home daemon, personal logs.

### 9. Hobby / Humanity Family
- **Accent Color**: Gold/Starfield (`#fbbf24`)
- **Graphics**: Spark icons, community collaboration symbols.
- **Roles**: Idea parser, helper templates, open-source contributor.
