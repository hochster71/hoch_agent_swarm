# Ephemeral Pipeline Doctrine

This doctrine sets forth the rules for executing agent tasks in isolated, temporary environments.

## Core Principles

### 1. Isolated Task Workspaces
Every agent run or mission execution is initiated in a freshly allocated, isolated workspace directory. This prevents tasks from contaminating one another or modifying global project configurations.

### 2. Least-Context Loading
Only the files and context required for the specific task are mounted in the workspace. Secrets or credentials are never mounted by default; they are retrieved via secure APIs when authorized.

### 3. Agent Chain Execution
Tasks are executed sequentially through specialized agent chains (e.g. Architect -> Builder -> QA). Output from one step must satisfy criteria before being passed to the next.

### 4. Non-Destructive Default
Workspaces operate in read-only mode relative to the host repository. Write actions are staged in temporary files and never committed to the main branch autonomously.

### 5. Evidence Capture
All execution logs, compiler logs, and test outputs are captured and written to the `evidence_manifest.json` file inside the workspace.

### 6. Workspace Destruction
Upon completion of the task (or failure), the temporary workspace is destroyed. Only the signed evidence package is exported to the persistent audit folder.

### 7. Promotion Only After Gates Pass
Code modifications are promoted from the workspace to the repository only when all lint, unit, and security validation tests pass.

### 8. Rollback Plan
Every promotion has a corresponding rollback plan. If runtime regressions are detected after promotion, the control plane resets the branch to the previous known good commit.

### 9. Human Approval Gate
Before any workspace promotion is committed, the final diff and validation report must be approved by Michael Hoch.
