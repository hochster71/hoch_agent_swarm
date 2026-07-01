import { HochsterInstance, HochsterSolveRequest, HochsterSolution } from "./hochsterTypes";

export const mockInstances: HochsterInstance[] = [
  {
    instance_id: "hochster-01",
    status: "online",
    cpu_percent: 18,
    memory_usage_gb: 1.2,
    uptime_seconds: 7920,
    total_requests: 342,
    queue_length: 3,
    primary_swarm: "Code Review Swarm",
    region: "us-east-1"
  },
  {
    instance_id: "hochster-02",
    status: "online",
    cpu_percent: 21,
    memory_usage_gb: 1.4,
    uptime_seconds: 6480,
    total_requests: 287,
    queue_length: 1,
    primary_swarm: "DevOps Swarm",
    region: "us-east-1"
  },
  {
    instance_id: "hochster-03",
    status: "online",
    cpu_percent: 16,
    memory_usage_gb: 1.1,
    uptime_seconds: 10920,
    total_requests: 419,
    queue_length: 2,
    primary_swarm: "Security Swarm",
    region: "us-west-2"
  },
  {
    instance_id: "hochster-04",
    status: "online",
    cpu_percent: 24,
    memory_usage_gb: 1.5,
    uptime_seconds: 8700,
    total_requests: 233,
    queue_length: 0,
    primary_swarm: "Remediation Swarm",
    region: "eu-central-1"
  },
  {
    instance_id: "hochster-05",
    status: "online",
    cpu_percent: 17,
    memory_usage_gb: 1.0,
    uptime_seconds: 5520,
    total_requests: 198,
    queue_length: 0,
    primary_swarm: "QA Swarm",
    region: "us-east-1"
  },
  {
    instance_id: "hochster-06",
    status: "idle",
    cpu_percent: 6,
    memory_usage_gb: 0.6,
    uptime_seconds: 2700,
    total_requests: 23,
    queue_length: 0,
    primary_swarm: "Red-Team Swarm",
    region: "ap-southeast-1"
  },
  {
    instance_id: "hochster-07",
    status: "idle",
    cpu_percent: 5,
    memory_usage_gb: 0.5,
    uptime_seconds: 1920,
    total_requests: 12,
    queue_length: 0,
    primary_swarm: "General/On-Demand",
    region: "us-east-1"
  }
];

export const mockSolveRequest: HochsterSolveRequest = {
  request_id: "req_9f3a2c0f",
  correlation_id: "corr-7f3a0b2c-2dde-4a2f-bc1d-8a5f8b7c3e11",
  requested_at: "2026-06-24T12:00:00Z",
  status: "solved",
  caller: {
    swarm_id: "swarm-code-review",
    swarm_name: "Code Review Swarm"
  },
  problem: {
    type: "runtime_exception",
    summary: "NullReferenceException in UserService.cs",
    severity: "high",
    language: "C#",
    framework: ".NET 8.0",
    runtime: "dotnet"
  },
  context: {
    repository: "hoch-agent-swarm",
    branch: "feature/control-plane",
    commit_sha: "a9fdc38",
    files: ["src/services/UserService.cs"],
    logs: ["container://api/logs/latest"],
    stack_trace: "System.NullReferenceException: Object reference not set to an instance of an object.\n   at UserService.GetUser(Guid id) in src/services/UserService.cs:line 12\n   at UserController.Get(Guid id) in src/controllers/UserController.cs:line 24"
  },
  allowed_tools: ["filesystem", "shell", "docker", "tests", "diff_patch"],
  max_instances: 3,
  timeout_seconds: 60,
  constraints: {
    may_modify_files: false,
    may_run_commands: true,
    may_access_network: false,
    may_open_pull_request: false,
    requires_human_approval: true
  }
};

export const mockSolution: HochsterSolution = {
  solution_id: "sol_7f3a9b2c",
  request_id: "req_9f3a2c0f",
  generated_at: "2026-06-24T12:02:15Z",
  status: "validated",
  root_cause: "Unchecked null user database lookup leading to a NullReferenceException when accessing the User Name property.",
  explanation: "The database call to `_repo.Find(id)` returned null for an invalid Guid. The code immediately tried to access `user.Name` without checking if the user instance was null. The proposed patch checks for null and returns an empty string or throws a NotFoundException.",
  patch: {
    diff: `diff --git a/src/services/UserService.cs b/src/services/UserService.cs
index 89e248a..f713a9b 100644
--- a/src/services/UserService.cs
+++ b/src/services/UserService.cs
@@ -9,7 +9,11 @@ public class UserService
     public string GetUser(Guid id)
     {
         var user = _repo.Find(id);
-        return user.Name;
+        if (user == null)
+        {
+            throw new NotFoundException($"User {id} not found");
+        }
+        return user.Name ?? string.Empty;
     }`,
    files_changed: ["src/services/UserService.cs"],
    risk: "low"
  },
  validation: {
    tests_run: 12,
    tests_passed: 12,
    tests_failed: 0,
    commands_executed: ["dotnet test --filter UserServiceTests"],
    evidence_refs: ["ev-test-verify-19a"]
  },
  security: {
    secrets_exposed: false,
    dependency_risks: [],
    policy_warnings: []
  },
  confidence: 0.94
};

export const mockAuditTraces = [
  { timestamp: "12:12:44", event: "REQUEST_RECEIVED", summary: "Code Review Swarm submitted solve request." },
  { timestamp: "12:12:45", event: "INSTANCE_ASSIGNED", summary: "Assigned request to worker instance hochster-01." },
  { timestamp: "12:12:46", event: "ANALYSIS_STARTED", summary: "Worker analyzing UserService.cs file contents and stack trace." },
  { timestamp: "12:12:49", event: "TOOLS_EXECUTED", summary: "Ran 17 isolated filesystem and test tools." },
  { timestamp: "12:12:52", event: "SOLUTION_GENERATED", summary: "Candidate patch created with low-risk classification." },
  { timestamp: "12:12:53", event: "VALIDATION_PASSED", summary: "Validation tests passed. All 12 test assertions succeeded." },
  { timestamp: "12:12:54", event: "RESPONSE_SENT", summary: "Solution dispatched to calling swarm in 3.42 seconds total." }
];

import { SolverCandidate, SolutionMemoryRecord, HochsterCertificationReport, HochsterSlo } from "./hochsterTypes";

export const mockCandidates: SolverCandidate[] = [
  {
    candidate_id: "cand_01",
    request_id: "req_9f3a2c0f",
    strategy: "root_cause_first",
    generated_at: "2026-06-24T12:01:00Z",
    root_cause: "Null check missing on Repository lookup",
    explanation: "Checks if database returns null user object before reading user name.",
    patch: {
      diff: "diff --git a/UserService.cs b/UserService.cs\n...",
      files_changed: ["src/services/UserService.cs"]
    },
    validation: {
      tests_run: 12,
      tests_passed: 12,
      tests_failed: 0,
      security_warnings: [],
      regression_risk: "low"
    },
    scoring: {
      confidence: 0.94,
      correctness_score: 100,
      simplicity_score: 85,
      safety_score: 95,
      maintainability_score: 90,
      total_score: 92
    },
    evidence_refs: ["rec_l3_1"]
  },
  {
    candidate_id: "cand_02",
    request_id: "req_9f3a2c0f",
    strategy: "test_first",
    generated_at: "2026-06-24T12:01:05Z",
    root_cause: "Null database lookup triggers error",
    explanation: "Explicit unit tests added for null boundary cases followed by guard checks.",
    patch: {
      diff: "diff --git a/UserService.cs b/UserService.cs\n...",
      files_changed: ["src/services/UserService.cs", "tests/UserServiceTests.cs"]
    },
    validation: {
      tests_run: 12,
      tests_passed: 12,
      tests_failed: 0,
      security_warnings: [],
      regression_risk: "low"
    },
    scoring: {
      confidence: 0.90,
      correctness_score: 100,
      simplicity_score: 80,
      safety_score: 90,
      maintainability_score: 90,
      total_score: 86
    },
    evidence_refs: ["rec_l3_1"]
  },
  {
    candidate_id: "cand_03",
    request_id: "req_9f3a2c0f",
    strategy: "container_first",
    generated_at: "2026-06-24T12:01:10Z",
    root_cause: "Cache invalidation on Docker runtime restart",
    explanation: "Pre-heals container configuration before checking source code.",
    patch: {
      diff: "diff --git a/Dockerfile b/Dockerfile\n...",
      files_changed: ["Dockerfile"]
    },
    validation: {
      tests_run: 12,
      tests_passed: 12,
      tests_failed: 0,
      security_warnings: [],
      regression_risk: "low"
    },
    scoring: {
      confidence: 0.89,
      correctness_score: 100,
      simplicity_score: 75,
      safety_score: 90,
      maintainability_score: 85,
      total_score: 84
    },
    evidence_refs: ["rec_l3_1"]
  },
  {
    candidate_id: "cand_04",
    request_id: "req_9f3a2c0f",
    strategy: "minimal_patch",
    generated_at: "2026-06-24T12:01:15Z",
    root_cause: "Null check missing on Repository lookup",
    explanation: "Inline null check before user name query.",
    patch: {
      diff: "diff --git a/UserService.cs b/UserService.cs\n...",
      files_changed: ["src/services/UserService.cs"]
    },
    validation: {
      tests_run: 12,
      tests_passed: 12,
      tests_failed: 0,
      security_warnings: [],
      regression_risk: "low"
    },
    scoring: {
      confidence: 0.88,
      correctness_score: 100,
      simplicity_score: 95,
      safety_score: 90,
      maintainability_score: 80,
      total_score: 81
    },
    evidence_refs: ["rec_l3_1"]
  },
  {
    candidate_id: "cand_05",
    request_id: "req_9f3a2c0f",
    strategy: "security_first",
    generated_at: "2026-06-24T12:01:20Z",
    root_cause: "Null check missing on Repository lookup",
    explanation: "Checks permissions, sanitizes query inputs and performs null checks.",
    patch: {
      diff: "diff --git a/UserService.cs b/UserService.cs\n...",
      files_changed: ["src/services/UserService.cs"]
    },
    validation: {
      tests_run: 11,
      tests_passed: 11,
      tests_failed: 0,
      security_warnings: ["secrets"],
      regression_risk: "medium"
    },
    scoring: {
      confidence: 0.85,
      correctness_score: 92,
      simplicity_score: 70,
      safety_score: 85,
      maintainability_score: 85,
      total_score: 78
    },
    evidence_refs: ["rec_l3_1"]
  },
  {
    candidate_id: "cand_06",
    request_id: "req_9f3a2c0f",
    strategy: "refactor_first",
    generated_at: "2026-06-24T12:01:25Z",
    root_cause: "Null check missing on Repository lookup",
    explanation: "Refactors method signature to return Option<User> to prevent null exceptions.",
    patch: {
      diff: "diff --git a/UserService.cs b/UserService.cs\n...",
      files_changed: ["src/services/UserService.cs"]
    },
    validation: {
      tests_run: 8,
      tests_passed: 8,
      tests_failed: 4,
      security_warnings: [],
      regression_risk: "high"
    },
    scoring: {
      confidence: 0.72,
      correctness_score: 66,
      simplicity_score: 50,
      safety_score: 45,
      maintainability_score: 95,
      total_score: 52
    },
    evidence_refs: ["rec_l3_1"]
  }
];

export const mockMemoryRecords: SolutionMemoryRecord[] = [
  {
    memory_id: "mem_f39281a1",
    created_at: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
    scope: { tenant_id: "tenant-dod-zta", project_id: "mesh-macbook-neo", repository: "hoch-agent-swarm", language: "C#", framework: "dotnet" },
    problem_signature: { problem_type: "runtime_exception", stack_trace_hash: "hash_null_ref_user_get" },
    solution: { root_cause: "Null check in GetUser(Guid id)", patch_summary: "Add null check before usage", files_changed: ["UserService.cs"], validation_status: "validated", confidence: 0.96 },
    governance: { reusable: true, redacted: true, approved_by: "Michael Hoch", evidence_refs: ["rec_l3_1"] }
  },
  {
    memory_id: "mem_a831c2d4",
    created_at: new Date(Date.now() - 3600000 * 24 * 5).toISOString(),
    scope: { tenant_id: "tenant-dod-zta", project_id: "imac-beta", repository: "hoch-agent-swarm", language: "TypeScript", framework: "node" },
    problem_signature: { problem_type: "container_failure", stack_trace_hash: "hash_oom_imac_gordy" },
    solution: { root_cause: "Memory leak in socket parser", patch_summary: "Flush buffer on disconnect event", files_changed: ["socketParser.ts"], validation_status: "validated", confidence: 0.92 },
    governance: { reusable: true, redacted: true, approved_by: "Michael Hoch", evidence_refs: ["rec_l2_2"] }
  }
];

export const mockCertificationReport: HochsterCertificationReport = {
  report_id: "cert_2024_05_22_01",
  generated_at: "2024-05-22T10:12:00Z",
  version: "1.0.0-GA",
  status: "passed",
  tests: [
    { test_id: "FND-102", name: "Sandbox Escape via Symlinks", category: "sandbox", severity: "critical", status: "passed", evidence_refs: ["sandbox.escape.proof"], findings: [] },
    { test_id: "FND-103", name: "Prompt Injection Payload Isolation", category: "prompt_injection", severity: "high", status: "passed", evidence_refs: ["prompt.injection.proof"], findings: [] },
    { test_id: "FND-104", name: "Secrets Masking Verification", category: "secret_redaction", severity: "high", status: "passed", evidence_refs: ["secret.redaction.proof"], findings: [] }
  ],
  summary: { passed: 118, failed: 2, warnings: 6, critical_findings: 0 },
  release_decision: "allow"
};

export const mockSlos: HochsterSlo[] = [
  { slo_id: "solve_success_rate", name: "Solve Success Rate", target: 0.75, current: 0.794, window: "30d", status: "healthy" },
  { slo_id: "callback_delivery_rate", name: "Callback Delivery Rate", target: 0.99, current: 0.991, window: "30d", status: "healthy" },
  { slo_id: "p95_response_time", name: "p95 Response Time", target: 30, current: 2.31, window: "24h", status: "healthy" }
];

