# Security Report — HELM OMEGA ASSURANCE AUDIT v1.0

**Standard lenses:** OWASP Top 10, OWASP LLM Top 10, local RMF fragments, existing pentest package.

---

## 1. Executive Security Verdict

| Scope | Verdict |
|---|---|
| Internet-facing production control plane | **NO-GO / NOT READY** |
| LAN-local development | **CONDITIONAL GO** (per existing pentest; residual open findings) |
| Secrets handling (policy intent) | **PARTIAL** — gitignore + gitleaks config present; live secret values not extracted this audit |
| AuthN/AuthZ completeness | **PARTIAL / FAIL** for read path |

---

## 2. Findings (Evidence-Traced)

### SEC-01 — Unauthenticated read path on HELM LIVE API (HIGH)

- **Evidence:** NIST matrix assessor text (2026-07-15) states read-auth staged but **NOT mounted** in `helm_live_api.py`.
- **Evidence:** This audit retrieved `/api/v1/helm/mission`, `/api/v1/helm/authority` without presenting credentials (localhost TLS).
- **Impact:** Local process compromise or LAN reachability exposes mission, authority, voice policy surfaces.
- **CVSS (est.):** 7.1 (AV:A/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N) if LAN-reachable; lower if strictly loopback-only.
- **Exploitability:** High on shared LAN; depends on bind address (8770 observed `127.0.0.1` in process list — mitigates).
- **Residual:** Loopback bind reduces exposure; still weak multi-user / malware local threat model.

### SEC-02 — CORS `allow_origins=["*"]` on helm_live_api (HIGH)

- **Evidence:** `backend/helm_live_api.py` line pattern confirmed.
- **Impact:** Browser-based CSRF-style data exfil if endpoints reachable from attacker origin and cookies/tokens ever used loosely.
- **Mitigation present:** Founder write routes token-gated (`authorized(body.get("token"))`).
- **Residual:** Read data still broadly origin-open if reachable.

### SEC-03 — Control posture “100%” overclaim (HIGH — integrity/governance)

- **Evidence:** `coordination/security/helm_control_posture.json`: `controls_assessed: 13`, `posture_percent: 100.0`.
- **Evidence:** CM-3 claims `0 uncommitted code files` at assess time; current tree has **289 dirty paths**.
- **Impact:** Executive risk dashboards can green-wash residual risk.
- **Status:** **FAIL as full RMF posture**; **PARTIAL** as narrow continuous-monitoring sample.

### SEC-04 — Network pentest residual findings (MEDIUM–CRITICAL historical)

From `artifacts/pentest/`:

| ID | Title | Status in package |
|---|---|---|
| F-0 | AT&T gateway remote admin | REMEDIATED (package claim) |
| F-1 | Double-NAT | OPEN |
| F-2 | Upstream management reachable | OPEN |
| F-3 | Gateway HTTP local admin | OPEN |
| F-4 | Switch mgmt on transit | OPEN |
| F-5 | Lack of swarm/IoT segmentation | OPEN |

Release gate: **CONDITIONAL GO — LAN-only** (dated 2026-06-27). **Not re-validated end-to-end this audit** → residual network risk **UNVERIFIED-current / OPEN-as-documented**.

### SEC-05 — Model runtime ports (MEDIUM)

- Gateway live: lmstudio `:1234` alive.
- Pentest requires blocking IoT/general clients from 1234/11434.
- **Current enforcement:** NOT re-probed across VLANs this audit → **UNKNOWN**.

### SEC-06 — Secrets on disk

| Check | Result |
|---|---|
| `.env` gitignored | YES (`git check-ignore`) |
| `hsf/deploy/.env.local` gitignored | YES |
| Pattern scan for live `sk_live_` in tracked code | Hits are **docs/tests/placeholders**, not extracted live secrets |
| Secret values themselves | **NOT inspected** (doctrine: never print secrets) |

**Verdict:** Policy controls present; **secret inventory completeness UNKNOWN**.

### SEC-07 — Supply chain / CI

| Control | Evidence | Verdict |
|---|---|---|
| GitHub workflows | `.github/workflows/*` including `supply-chain-provenance.yml`, `rc21-security.yml`, CodeQL | PRESENT |
| SBOM scripts | `package.json` supply:* scripts | PRESENT (execution not re-run) |
| SLSA level | No live SLSA provenance attestation verified this audit | **UNVERIFIED** |
| Dependency CVEs | Full `pip-audit`/`npm audit` not completed this audit | **UNKNOWN** |

### SEC-08 — Founder gate integrity (POSITIVE)

- Voice governance validator: deploy/spend/provision_keys → DOORSTEP.
- `control/authority_policy.json` separates autonomous vs human-approval actions.
- Founder decide API token-gated.

**Verdict:** Write-side founder authority **PARTIALLY VERIFIED** (unit/validator). Not a substitute for full auth stack.

### SEC-09 — Hash-chain audit protection (POSITIVE / PARTIAL)

- Spend ledger: 15,428 rows with entry_hash structure.
- Revenue ledger: chained PENDING entry.
- Historical soak supersession when instrument lied (FALSE_RELEASE_LEDGER_INSTRUMENT) shows detection culture.

**Not fully re-verified chain recompute algorithm this audit** → structure **PRESENT**, cryptographic verification **PARTIAL**.

### SEC-10 — Prompt / tool injection (AI)

- Fail-closed doctrines in prompt managers exist.
- Full OWASP LLM Top 10 red-team **not executed** this audit → **UNKNOWN residual**.

---

## 3. Risk Matrix (Security)

| ID | Likelihood | Impact | Risk | Mitigation | Residual |
|---|---|---|---|---|---|
| SEC-01 unauth read | M (local/LAN) | H | HIGH | Loopback bind; stage zero-trust | OPEN |
| SEC-02 CORS * | M | M–H | HIGH | Token on writes | OPEN |
| SEC-03 posture greenwash | H | H | HIGH | Narrow assessors | OPEN |
| SEC-04 LAN findings | M | M | MEDIUM | Prior pentest backlog | OPEN |
| SEC-05 model ports | M | M | MEDIUM | Gateway design | UNKNOWN |
| SEC-06 secrets leak | L | H | MEDIUM | gitignore/gitleaks | UNKNOWN |
| SEC-07 supply chain | M | H | MEDIUM | CI scripts | UNVERIFIED |
| SEC-10 LLM injection | M | H | HIGH | prompt doctrine | UNKNOWN |

---

## 4. OWASP Top 10 (application — abbreviated)

| OWASP | Status | Notes |
|---|---|---|
| A01 Broken Access Control | **PARTIAL/FAIL** | Read unauthenticated; write founder-gated |
| A02 Cryptographic Failures | PARTIAL | TLS on 8770 with dev cert; chain hashing |
| A03 Injection | PARTIAL | LLM/tool injection not fully tested |
| A04 Insecure Design | PARTIAL | Strong doorstep doctrine; dual truth surfaces |
| A05 Misconfiguration | FAIL/PARTIAL | CORS *; dirty tree; multi-service sprawl |
| A06 Vulnerable Components | UNKNOWN | CVE scan not completed |
| A07 Auth Failures | PARTIAL | Token founder path; weak read auth |
| A08 Integrity Failures | PARTIAL | Hash chains + superseded false green history |
| A09 Logging Failures | PARTIAL | Many ledgers; log poisoning not tested |
| A10 SSRF | UNKNOWN | Not specifically tested |

## 5. OWASP LLM Top 10 (abbreviated)

| Item | Status |
|---|---|
| LLM01 Prompt injection | UNKNOWN (not red-teamed this audit) |
| LLM02 Insecure output handling | PARTIAL (validators exist) |
| LLM03 Training data poisoning | N/A-ish / UNKNOWN (local models) |
| LLM04 Model DoS | UNKNOWN |
| LLM05 Supply chain | PARTIAL (gateway attestation PARTIAL historically) |
| LLM06 Sensitive info disclosure | PARTIAL (secrets doctrine) |
| LLM07 Insecure plugin/tool design | PARTIAL (doorstep) |
| LLM08 Excessive agency | PARTIAL–controlled by doorstep; self-cert risks in agents need ongoing control |
| LLM09 Overreliance | HIGH organizational risk if posture 100% trusted |
| LLM10 Model theft | UNKNOWN |

---

## 6. Security Score: **48 / 100**

Deserves credit for fail-closed write gates and evidence culture; **does not** deserve production trust without read-auth, CORS fix, honest posture scoring, and current network revalidation.
