from typing import List, Dict, Any

# Define the standard job configuration
STANDARD_CLUSTER_JOBS: List[Dict[str, Any]] = [
    {
        "job_id": "RT-001",
        "instance": "hochster-ui-static-01",
        "role": "Detect mock/static UI state",
        "tools": ["filesystem", "tests", "diff_patch"],
        "mutation": "No",
        "severity": "critical",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-ui-static-gate"]
    },
    {
        "job_id": "RT-002",
        "instance": "hochster-api-live-01",
        "role": "Validate live endpoints",
        "tools": ["filesystem", "observability", "tests"],
        "mutation": "No",
        "severity": "critical",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-api-live-gate"]
    },
    {
        "job_id": "RT-003",
        "instance": "hochster-stream-01",
        "role": "Validate OTel traces/metrics/logs",
        "tools": ["observability", "tests"],
        "mutation": "No",
        "severity": "critical",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-stream-gate"]
    },
    {
        "job_id": "RT-004",
        "instance": "hochster-docker-01",
        "role": "Inspect containers/logs/health",
        "tools": ["docker", "observability"],
        "mutation": "No",
        "severity": "high",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-docker-gate"]
    },
    {
        "job_id": "RT-005",
        "instance": "hochster-policy-01",
        "role": "Validate policy enforcement",
        "tools": ["filesystem", "tests"],
        "mutation": "No",
        "severity": "critical",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-policy-gate"]
    },
    {
        "job_id": "RT-006",
        "instance": "hochster-audit-01",
        "role": "Validate audit event integrity",
        "tools": ["filesystem", "tests"],
        "mutation": "No",
        "severity": "high",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-audit-gate"]
    },
    {
        "job_id": "RT-007",
        "instance": "hochster-stale-01",
        "role": "Inject stale/failure scenarios",
        "tools": ["tests", "observability"],
        "mutation": "No",
        "severity": "critical",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-stale-gate"]
    },
    {
        "job_id": "RT-008",
        "instance": "hochster-patch-01",
        "role": "Generate validated patches",
        "tools": ["filesystem", "diff_patch", "tests"],
        "mutation": "No direct apply",
        "severity": "high",
        "status": "pass",
        "findings": [],
        "patches_generated": 2,
        "patches_validated": 2,
        "evidence_refs": ["ev-patch-gate"]
    },
    {
        "job_id": "RT-009",
        "instance": "hochster-release-01",
        "role": "Verify image digests/release metadata",
        "tools": ["filesystem", "security"],
        "mutation": "No",
        "severity": "high",
        "status": "pass",
        "findings": [],
        "patches_generated": 0,
        "patches_validated": 0,
        "evidence_refs": ["ev-release-gate"]
    }
]
