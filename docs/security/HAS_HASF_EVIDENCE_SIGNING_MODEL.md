# HAS/HASF Evidence Signing Model

This document defines the cryptographic security model for securing the evidence hash-chain against unauthorized modifications.

---

## 1. Hash-Chain Model
Every file registered in the evidence manifest is cryptographically linked to its predecessor:
\[H_i = \text{SHA256}(\text{Entry}_i \parallel H_{i-1})\]
This ensures that deleting, inserting, or modifying any historic evidence file invalidates all subsequent entry hashes.

---

## 2. Signing Model & Key Custody
To prove the origin of the chain:
* **HELM Modifiable Fields**: The runner can only *append* new elements. It cannot modify prior elements.
* **Founder Key**: The ultimate authority (Michael) holds a private key (Offline PGP/GPG or RSA key) used to sign the manifest's head.
* **L4 Baseline**: For L4, we utilize a local safe simulation of signing via a key pair generated locally (or using a pre-configured verification key), flagging the status as `SIGNING_PARTIAL_PENDING_FOUNDER_KEY` if key material is missing.

---

## 3. Future L5 Roadmap
* Hardware Security Module (HSM) or secure enclave key custody for autonomous runner signing.
* Multi-signature verification of build/deployment gates before verification.
