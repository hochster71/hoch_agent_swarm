# Staging Deployment Plan — CyberQRG-AI

---

## 1. Local Preview Path
* Developers spin up static server:
  `python3 -m http.server 8080`
* Accessible only through Tailscale mesh (no public routes).

---

## 2. Rollback Plan
* Git-based rollbacks to verified tags.
* Deleting staging builds on local filesystem or remote staging folders.
