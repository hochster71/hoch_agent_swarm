# Mission Intake Signing Specification — HELM

---

## 1. Security Mandate
Every mission added to `mission_intake_queue.json` must be signed with a key matching the founder public key.

---

## 2. Signature and Key Segregation (Ed25519)
* **Algorithm**: Ed25519 signatures.
* **Key Segregation**: The private key exists ONLY on the founder Mac.
* **Verification**: `HOCH-200` stores the public key only for signature verification.
* **Sync Protection**: Private key material is never synced to remote environments or committed to repository source control.

---

## 3. Config & Missing Key Handling
If the environment does not expose the signing key, submission falls back to dry-run or signs as `SIGNING_PARTIAL_PENDING_FOUNDER_KEY`.
Do not commit private keys to the repository.
