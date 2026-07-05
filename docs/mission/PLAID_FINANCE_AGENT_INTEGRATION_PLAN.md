# Plaid Finance Agent Integration Plan

This document outlines the architecture, database schema, API routing, UI design, security controls, and testing strategy for integrating the read-only Personal Finance Agent (`hoch-finance-readonly-agent`) into the Hoch Agent Swarm (HAS) / Hoch Pods environment.

---

## 1. Discovered Architecture

* **Frontend Framework**: Single Page Application using vanilla JavaScript (`frontend/app.js`), HTML (`frontend/index.html`), and vanilla CSS (`frontend/styles.css`), compiled and bundled using Vite.
* **Backend Framework**: FastAPI web server defined in `backend/main.py`.
* **Database Layer**: SQLite database (`backend/swarm_ledger.db`) managed dynamically on startup in `backend/runtime_truth/state_store.py` (`init_runtime_truth_tables()`).
* **Existing Agent Registry**: Loaded dynamically from `data/prompt_registry/agents.manifest.json` and supplemented via the SQLite table `agent_capability_manifests`.
* **Evidence Ledger**: Appends structured JSON events to `data/agent_execution_ledger.jsonl`.
* **Runtime Truth Model**: System status signals collected in the SQLite table `runtime_truth_signals` by `backend/runtime_truth/collector.py`.
* **Dashboard Routing**: Client-side view switching toggled using `.hidden` classes in `frontend/app.js` and navigation links.
* **Environment Variables**: Managed using `.env` at the project root and validated by `backend/validate_env.py`.
* **Test Framework**: Pytest for backend unit/integration tests and Playwright for E2E specifications.

---

## 2. Proposed Changes & File Operations

### Exact Files to Modify
1. **[state_store.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/runtime_truth/state_store.py)**: Append Plaid Finance table creation statements to `init_runtime_truth_tables()`.
2. **[collector.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/runtime_truth/collector.py)**: Add Plaid connection and sync signals to the `collect_and_store_all()` function.
3. **[main.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/main.py)**: Implement FastAPI routes under `/api/plaid/*` and `/api/finance/*`, and enforce endpoint allowlists.
4. **[index.html](file:///Users/michaelhoch/hoch_agent_swarm/frontend/index.html)**: Add a navigation link for `Personal Finance` and the layout of the `personal-finance` view.
5. **[app.js](file:///Users/michaelhoch/hoch_agent_swarm/frontend/app.js)**: Map navigation routing, bind Plaid authentication/sync events, and render table/chart views.
6. **[.env.example](file:///Users/michaelhoch/hoch_agent_swarm/.env.example)**: Add Plaid configuration variables.
7. **[validate_env.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/validate_env.py)**: Ensure Plaid environment variables are checked softly so the app runs in sandbox/stub mode if they are absent.

### New Files to Add
1. **[PLAID_FINANCE_AGENT_INTEGRATION_PLAN.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/mission/PLAID_FINANCE_AGENT_INTEGRATION_PLAN.md)**: This plan file.
2. **[hoch-finance-readonly-agent.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/agents/hoch-finance-readonly-agent.md)**: Agent capability contract.
3. **[PLAID_FINANCE_READONLY_CONTROLS.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/security/PLAID_FINANCE_READONLY_CONTROLS.md)**: Read-only governance and token encryption documentation.
4. **[BUDGET_ENGINE.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/finance/BUDGET_ENGINE.md)**: Budget Engine functional overview.
5. **[DEBT_PLANNER.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/finance/DEBT_PLANNER.md)**: Debt payoff strategies overview.
6. **[STATEMENT_HANDLING.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/finance/STATEMENT_HANDLING.md)**: PDF list, download, and SHA-256 hashing specifications.
7. **[PLAID_FINANCE_AGENT_VALIDATION.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/release/PLAID_FINANCE_AGENT_VALIDATION.md)**: Audit validation report.
8. **[budget_categories.json](file:///Users/michaelhoch/hoch_agent_swarm/config/finance/budget_categories.json)**: Category mapping config.
9. **[plaid_connector.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/connectors/plaid_connector.py)**: Connector with read-only endpoint enforcement, token encryption, and Plaid API simulation.
10. **[budget_engine.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/finance/budget_engine.py)**: Budget variance calculation engine.
11. **[debt_planner.py](file:///Users/michaelhoch/hoch_agent_swarm/backend/finance/debt_planner.py)**: Avalanche/Snowball/Hybrid scenario calculations.
12. **[test_plaid_finance_agent.py](file:///Users/michaelhoch/hoch_agent_swarm/tests/test_plaid_finance_agent.py)**: Test suite covering all 15 checklist criteria.

---

## 3. Database Migration Plan (SQLite)

We will append the following schema tables to `init_runtime_truth_tables()`:
- `finance_plaid_items`
- `finance_accounts`
- `finance_transactions`
- `finance_liabilities`
- `finance_statements`
- `finance_audit_events`

---

## 4. API Route Plan

* **POST `/api/plaid/create-link-token`**: Prepares link token for the client link flow.
* **POST `/api/plaid/exchange-public-token`**: Exchanges the public token for an access token, encrypts it, and saves it.
* **POST `/api/finance/sync`**: Triggers account balance, transaction, and statements updates.
* **GET `/api/finance/accounts`**: Returns encrypted-safe metadata for connected accounts.
* **GET `/api/finance/transactions`**: Returns normalized transaction history.
* **GET `/api/finance/budget/monthly`**: Runs the deterministic budgeting calculation.
* **GET `/api/finance/debt-plan`**: Generates Avalanche, Snowball, and Hybrid scenarios.
* **GET `/api/finance/statements`**: Returns PDF statement metadata.
* **POST `/api/finance/statements/download`**: Syncs statements from Plaid (if supported).
* **GET `/api/finance/reports/monthly-closeout`**: Produces a summary PDF closeout file path with disclaimers.

---

## 5. UI Route / Component Plan

We will add a view `#view-personal-finance` inside the dark themed dashboard:
1. **Connection Status**: Displays whether Plaid is configured/connected and institutional sync metadata.
2. **Cash Position**: Displays credit/cash balances and the net operating position.
3. **Monthly Budget**: Displays income, spending, and category variance.
4. **Debt Planner**: Evaluates Avalanche, Snowball, and Hybrid payoff schedules.
5. **Subscriptions & Waste**: Lists recurring transactions and high-confidence waste detections.
6. **Statements**: Lists statements and SHA-256 verification hashes.
7. **Agent Findings**: Shows analytical disclaimers and advisor recommendations.
8. **Audit Trail**: Shows the execution ledger output for financial sync events.

---

## 6. Security Controls

* **Plaid Read-only Endpoint Verification**: A strict allowlist function (`assertReadOnlyPlaidEndpoint`) throws if any payment or money transfer endpoint is requested.
* **AES-256 Token Encryption**: Plaid access tokens are encrypted using `cryptography.fernet` and a key generated from `FINANCE_AGENT_ENCRYPTION_KEY`.
* **Zero Token Egress**: Raw Plaid tokens are never exposed in backend logs or sent to the client.
* **Consent Enforced**: Every data import requires consented link item records.
* **Advisory Disclaimer**: All finance reports include a disclaimer stating that the findings do not constitute financial advice.

---

## 7. Testing Plan

We will create a comprehensive Pytest test suite covering:
1. Plaid allowlist assertions.
2. Blocked endpoint rejections (fail-closed).
3. Missing env variable fallback (fails gracefully).
4. Token encryption and decryption.
5. Token masking in API outputs.
6. Transaction normalization.
7. Budget category rules.
8. Monthly variance engine checks.
9. Avalanche payment ordering.
10. Snowball payment ordering.
11. Unsupportive statement graceful degradation.
12. Audit event creation.
13. Dashboard state when Plaid is unconfigured.
14. Registry metadata inclusion.
15. Runtime truth signals.

---

## 8. Rollback Plan

If any critical failure occurs:
1. Revert modifications in `backend/main.py`, `frontend/index.html`, and `frontend/app.js` using git checkout.
2. Remove created files under `backend/connectors/`, `backend/finance/`, and `tests/`.
3. Database changes do not modify existing core tables and can be safely ignored (or tables dropped if needed).
