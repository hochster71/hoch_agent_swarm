# HELM R7 Performance Qualification Benchmark Report

**Generated UTC**: `2026-07-22T11:51:28.487992+00:00`  
**Git Commit**: `6bfd36b8c981332420942b5ad11c9a40a592a1a8` (Dirty Tree: `True`)  
**Environment**: `Darwin arm64` (`Python 3.14.6`)

---

## 1. Benchmark Results Summary

| Workload Name | Avg Size (bytes) | Ops / sec | Throughput (MB/s) | p50 (ms) | p95 (ms) | p99 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `small_governance_record` | 920 | 177481.98 | 155.72 | 0.0054 | 0.0068 | 0.0071 |
| `medium_evidence_record` | 3886 | 27273.50 | 101.08 | 0.0365 | 0.0376 | 0.0383 |
| `large_evidence_bundle` | 271434 | 1310.73 | 339.30 | 0.7245 | 0.8693 | 1.2867 |
| `flat_high_key_count` | 7391 | 10103.48 | 71.22 | 0.0975 | 0.1055 | 0.1222 |
| `deep_object_nesting` | 377 | 86846.41 | 31.22 | 0.0113 | 0.0116 | 0.0191 |
| `unicode_heavy_payload` | 1595 | 248267.40 | 377.64 | 0.0040 | 0.0041 | 0.0042 |
| `numeric_heavy_payload` | 3511 | 15443.02 | 51.71 | 0.0646 | 0.0701 | 0.0892 |

---

## 2. Regression Policy Budgets

- **Throughput Regression Limit**: $\le 5.0\%$
- **p50 Latency Regression Limit**: $\le 5.0\%$
- **p95 Latency Regression Limit**: $\le 7.0\%$
- **p99 Latency Regression Limit**: $\le 10.0\%$
- **Nondeterministic Digest Discrepancy**: **0**
