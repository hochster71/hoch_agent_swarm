# Improved Prompt Templates Playbook

Use these template patterns to ensure high prompt scoring (>= 80/100) and prevent loops.

## Bug Fix template

```markdown
Fix one root cause only.
Failure:
[paste exact command/log]
Expected:
[exact command must pass]
Scope:
Only touch files required to fix this failure.
Non-goals:
Do not refactor unrelated systems.
Do not add new features.
Proof:
Run the failing command again.
Run related gates.
Show logs clean.
```
