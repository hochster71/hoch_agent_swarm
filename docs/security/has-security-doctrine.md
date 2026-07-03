# HAS Security Doctrine
*Last updated: 2026-07-02. Authoritative for all agents, operators, and gates.*

## Authority model

| Actor | Role | Can sign approvals? | Can access founder key? |
|---|---|---|---|
| Michael Hoch | Founder / Approver | Yes (passphrase required) | Yes |
| hoch_agent (launchd user) | Swarm runtime | No | No (home 700, key 600) |
| HELM / CrewAI agents | Execution agents | No | No |
| CI (GitHub Actions) | Test runner | No (TEST_MODE only) | No |

## Closed findings

### C1 - Stripe/Drogon secrets in git history
- .env untracked; .gitignore covers all env and key files.
- scripts/purge_env_history.sh written; awaiting operator rotation and run.
- pre-commit hook blocks secret patterns before they enter history.
- Reference: GitHub Docs recommends revoking/rotating first, then
  git-filter-repo --path .env --invert-paths for history rewrite.

### C2 - Founder approval authority was a mutable string
- backend/mission_control/founder_signer.py: Ed25519 OpenSSH signatures,
  namespaced has-approval, over canonical approval payload.
- backend/approval_gate.py: APPROVED without valid founder signature raises,
  fails closed; no filesystem-writable bypass path exists.
- /api/v1/release/authority/request: requires a fresh (under 10 min)
  founder-signed grant bound to candidate_packet_id; unsigned returns HTTP 403.
- scripts/founder_approve.py: founder-only signing CLI.
- scripts/founder_keygen.sh: one-time key setup.

### C3 - Evidence manifests were agent-writable and forgeable
- backend/mission_control/evidence_integrity.py: HMAC-SHA256 manifest MAC
  keyed by founder private key material + append-only external anchor at
  ~/.has_founder/evidence_anchor.log (outside agent reach).
- scripts/evidence_tamper_gate.sh enforces MAC and anchor check.
- Reference: Tracehold (2026): append-only is not tamper-evident.
  Design per Schneier and Kelsey secure-log hash chaining.

### H1 - Path traversal CWE-23 in boundary.py
- Replaced startswith() prefix check with os.path.realpath +
  os.path.commonpath, plus NUL-byte rejection.
- Closes sibling-dir escape, dotdot escape, and NUL-truncation.
- CodeQL rates the remote-exploitable variant at 9.3 severity.

### H2 - Keyword-based risk classification was bypassable
- backend/mission_control/risk_classifier.py: five-tier capability model
  (read_only < write < execute < network < destructive).
- Risk is max tier over requested capabilities. Keywords are non-downgradable
  escalation only. Unknown capabilities default to EXECUTE (fail-safe).
- Reference: SafeHarness (2024): structural gating removes the means of
  evasion; behavioral/keyword defenses only reduce probability.

### H3 - Runtime state and release binaries tracked in git
- 5 release tarballs and 2 zips evicted from index; .gitignore extended.
- Policy: git holds code, policy, schemas only. Binaries go to GitHub Releases.
- Tracked repo verified at approx 109 MB; 1.3 GB was untracked venvs.

### H4 - 12095-line main.py monolith
- Guard test pins security-critical routes; caps file at 12500 lines.
- Incremental router-extraction plan in docs/security/main-split-plan.md.

### User account isolation (pre-monetization requirement)
- scripts/setup_agent_user.sh: macOS role account hoch_agent via
  sysadminctl -roleAccount (non-interactive, no GUI login).
- Agent launchd plists set UserName=hoch_agent; founder home hardened to 700.
- Reference: Alcoholless (NTT Labs 2025) validated this exact pattern for AI
  agent sandboxing on macOS. Apple Developer Forums: role account is the
  correct macOS concept for daemon service accounts.

## Remaining operator actions (code-complete, awaiting your execution)
1. Rotate Stripe keys + Drogon password, then run scripts/purge_env_history.sh
2. Run scripts/founder_keygen.sh -- C2 and C3 fail-closed without the key
3. Run sudo bash scripts/setup_agent_user.sh -- isolates the swarm runtime
4. Reload launchd plists: sudo launchctl bootout/bootstrap with UserName=hoch_agent
5. Push all remediation commits to hochster71/hoch_agent_swarm

## Standing policies
- All APPROVED decisions require a valid founder signature. No exceptions.
- Release authority tokens require a fresh (under 10 min) founder-signed grant.
- Capability-based risk floor. Agents declare capabilities; gates enforce tiers.
- Evidence manifests must carry a MAC anchored externally before any gate passes.
- main.py line ceiling: 12500. Ratchet down on each router extraction.
- Secret scanning: pre-commit hook blocks commits; add CI gitleaks workflow.
