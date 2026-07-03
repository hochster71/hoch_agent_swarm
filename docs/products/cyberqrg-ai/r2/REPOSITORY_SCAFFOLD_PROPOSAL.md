# Repository Scaffold Proposal — CyberQRG-AI

---

## 1. Directory Structure
```
cyberqrg-ai/
├── src/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scripts/
│   └── scanner_daemon.py
├── tests/
│   └── unit_tests.py
└── pyproject.toml
```

---

## 2. Environment Policy
* Strictly local `.env.example` template with NO credentials or secrets.
* Dev dependency locks maintained via `uv`.
