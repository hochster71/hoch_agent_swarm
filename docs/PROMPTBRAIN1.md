# PROMPTBRAIN1 — Universal Prompt Coverage & Centralized LLM Brain Integration

The Prompt Brain cockpit (PROMPTBRAIN1) provides a governed, versioned, audited, and safety-hardened prompt registry for HOCH Agent Swarm. It analyzes the existing prompt library, identifies missing coverage categories, generates missing prompts programmatically, and provides semantic task routing logic.

## Compliance Notices & Status Boundary

> [!IMPORTANT]
> **ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW**
> 
> *The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated, and no claim of absolute security is made.*

## Feature Overview

1. **Ingested Prompt Registry**: Imports and normalizes 103 original prompts from `hoch_agent_swarm_prompt_library.json`. Performs schema validation (requiring `id`, `category`, `industry`, `title`, `mission`, `outputs`, `prompt`).
2. **Jaccard Word-Overlap Detection**: Calculates similarity metrics between prompt missions to warn of redundant prompts in the registry.
3. **Gap Analysis**: Identifies missing prompt templates across key governance frameworks and sectors. Out of the target coverage scope, 84 missing prompt families were detected and flagged.
4. **Remediation & Programmatic Generation**: Automatically creates complete prompt entries for the 84 missing families (`BRAIN-001` through `PMO-001`).
5. **Safety Output Constraint Injection**: Every generated prompt enforces the following constraints:
   - **Mandated Output Structure**:
     1. Facts Observed
     2. Assumptions
     3. Risks (Ranked by severity and likelihood)
     4. Exact Remediation Actions
     5. Validation Tests
     6. Evidence Artifacts
     7. Release/Audit/Authorization Decision
     8. POA&M Entries
     9. Closure Criteria
     10. Central Brain Ingestion JSON block
   - **Safety Boundaries**: Fail closed on unresolved high-risk ambiguity; separate facts from assumptions; do not claim compliance/authorization without evidence; restrict to local-only context.
6. **Task-to-Prompt Recommendation Engine**: Routes user queries to recommended templates based on keyword similarity and categories, enforcing fail-closed restrictions for bypass attempts.
7. **Centralized LLM Brain**: Seeds metadata schemas, graph links, and retrieval policies.

## API Endpoints

The Flask UI server exposes the following endpoints under `/api/v1/promptbrain/`:

- `GET /api/v1/promptbrain/status`: Summarizes count of indexed, gap, and generated prompts.
- `GET /api/v1/promptbrain/prompts`: Returns the list of valid original prompts.
- `GET /api/v1/promptbrain/coverage`: Returns sector, category, and framework coverage matrices.
- `GET /api/v1/promptbrain/gaps`: Lists open gaps and missing prompt families.
- `GET /api/v1/promptbrain/generated`: Lists the 84 programmatically generated prompt records.
- `GET /api/v1/promptbrain/revised-library`: Returns the merged 187 prompt library.
- `GET /api/v1/promptbrain/brain-schema`: Returns the central LLM brain schema and relationships.
- `GET /api/v1/promptbrain/routing-matrix`: Returns the agent-to-prompt lane matrix.
- `POST /api/v1/promptbrain/route`: Accepts a `task_description` query and yields recommended prompt configurations.
- `GET /api/v1/promptbrain/export`: Serves a compiled `.zip` file of all generated registry reports.

## UI Cockpit Tab

The dashboard UI at `http://localhost:8085` contains a dedicated **Prompt Brain** tab with a dark theme:
- **Registry Table**: Live searchable index of all 187 active prompts.
- **Gap Status Grid**: Displays Open/Closed prompt families and severity levels.
- **Generated Preview**: Showcases safety-hardened prompt bodies.
- **Schema Viewer**: Inspects the knowledge graph relationships.
- **Routing Simulator**: Interactive testing of prompt-to-task mapping.
