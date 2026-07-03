# Architecture Blueprint — CyberQRG-AI

---

## 1. Application Architecture
* **Frontend**: Vanilla HTML5 / Vanilla CSS with local script components.
* **Backend/Service**: Local Python scanner daemon.
* **Model Backend**: Ephemeral Qwen 32B Coder for local link sanitization.

---

## 2. Local-First / Offline Posture
* Absolutely zero external internet dependency.
* Portability: Runnable inside a sandbox Docker container.

---

## 3. Data Flow
1. QR raw string processed by scanner service.
2. local regex / compliance parser evaluates structure.
3. Local audit log output to verification directory.
