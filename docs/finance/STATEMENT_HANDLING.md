# Statement Handling Specification

This document details how statement metadata and PDF binaries are handled by the Personal Finance Agent.

## Plaid Statements Flow
If Plaid Statements product is enabled:
1. **List Statements**: Fetch the list of statements from Plaid via `/statements/list`.
2. **Exclusion Check**: Match existing statement IDs in the database and download only missing PDFs via `/statements/download`.
3. **Integrity Hash**: Hash the downloaded PDF content using SHA-256 and store the hash value in the `finance_statements` table as validation proof.
4. **Local Secure Storage**: PDF files are stored encrypted in a local directory `data/finance/statements/` or object store.
5. **Auditing**: Generate a `finance.statements.download.completed` audit ledger entry.

## Unsupported Institutions
If statements are not supported:
- Backend routes should degrade gracefully, returning empty sets or unsupported flag values.
- UI elements display warning message: "Statements unsupported by connected institution."
