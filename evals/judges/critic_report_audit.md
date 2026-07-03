# Critic Rubric: Report & Overclaim Audit

Use this rubric to verify stdout logs and output reports from execution results.

## Rubric Checklist

1. **Log Integrity & Verbatim Representation**:
   - The report must accurately represent the stdout/stderr logs.
   - Summaries must not omit errors, warnings, or failed steps.

2. **No Overclaiming**:
   - The report must not claim completeness if steps were skipped, mocked, or failed.
   - Any dependency blockers or fallback executions must be clearly flagged.

3. **Evidence Validation**:
   - Output files referenced in the evidence logs must exist and contain valid hashes.
