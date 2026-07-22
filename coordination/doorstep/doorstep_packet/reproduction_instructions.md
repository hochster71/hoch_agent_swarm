# HELM v1.0.0-RC1 Reproduction & Verification Instructions

## 1. Environment Requirements
- Python >= 3.10
- pytest >= 8.0

## 2. Verification Steps
```bash
# Verify HELM Qualification Suite
pytest tests/unit/test_helm_*.py

# Verify Formal Verification Proofs
python3 scripts/helm/run_native_tlc.py

# Generate Executive Briefing
python3 scripts/helm/helm_cpm_executive_report.py
```
Build SHA-256 Commit: 93634c17be91e4f653e95e2ca0b19df00b4da146
Generated: 2026-07-22T14:54:47.012921Z
