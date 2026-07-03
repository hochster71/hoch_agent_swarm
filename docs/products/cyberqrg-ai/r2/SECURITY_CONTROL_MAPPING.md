# Security and Compliance Control Mapping — CyberQRG-AI

---

## 1. Cybersecurity Threat Model
* **Threat 1**: QR URL containing malicious domain payload.
* **Threat 2**: Interception of QR content via local network sniffers.
* **Mitigation**: Private Tailscale overlays, absolute offline validation, local storage only.

---

## 2. NIST Compliance Mapping
* **PR.DS-1**: Data-at-rest is protected using local filesystem permissions.
* **PR.PT-4**: Zero external routing ensures network path containment.
* **Controls Inherited from HAS/HASF**: Strict policy engine gatekeepers.
