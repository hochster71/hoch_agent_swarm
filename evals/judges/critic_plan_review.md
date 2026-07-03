# Critic Rubric: Plan Alignment Review

Use this rubric to assess LLM-generated execution plans before they are promoted to execution.

## Rubric Checklist

1. **Requirements Mapping**:
   - Every requirement in the user's intent must map to at least one numbered plan step.
   - Traceability must be explicit (e.g., "[Req 1] -> Step 1.2").

2. **Scope Boundaries**:
   - The plan must not contain any blocked scopes (no public claims, live billing, or production key deployments).
   - Ensure the plan maintains a private-first doctrine.

3. **No Execution Conflicts**:
   - Steps must be logically sequenced.
   - Dependencies between steps must be clearly identified and resolved.
