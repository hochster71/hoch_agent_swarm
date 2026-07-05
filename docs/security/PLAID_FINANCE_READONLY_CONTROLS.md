# Security Controls: Plaid Personal Finance Integration

This document outlines the security architecture and governance measures built into the personal finance integration to ensure it remains strictly read-only and fails closed on authorization anomalies.

## 1. Strictly Read-Only Operations
To guarantee no money movement can ever occur:
* **Allowlisted Plaid Endpoints**: The backend will reject any endpoint not explicitly declared in the allowlist.
* **Prohibited Endpoint Detection**: Blocked prefixes include `/transfer/`, `/bank_transfer/`, `/payment_initiation/`, and `/processor/`.
* **Zero Egress to Front-End**: Under no circumstances are Plaid access tokens returned to the client or written in trace logs.

## 2. Encryption Controls
* **Storage Encryption**: All access tokens are encrypted before storage in SQLite using Fernet symmetric encryption.
* **Key Derivation**: Fernet keys are derived from `FINANCE_AGENT_ENCRYPTION_KEY`.
* **Fail-Closed Configuration**: If the encryption key is missing or invalid in production, links will fail closed and the UI will show an unconfigured state.
