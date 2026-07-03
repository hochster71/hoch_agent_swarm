# Data Model Proposal — CyberQRG-AI

---

## 1. Entities
* **ScanResult**:
  - `id`: UUID
  - `raw_content`: String
  - `sanitized_url`: String
  - `scanned_at`: ISO8601 Timestamp
  - `threat_class`: String
  - `compliance_score`: Float
  - `evidence_sha256`: String

---

## 2. Persistence Options
* Local SQLite file encrypted with SQLCipher.
* No central servers or database replication.
* Strictly no storage of user identifiers or cookies.
