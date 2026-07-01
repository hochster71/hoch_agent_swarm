export type HochsterRequestStatus =
  | "queued"
  | "assigned"
  | "analyzing"
  | "executing_tools"
  | "validating"
  | "solved"
  | "failed"
  | "cancelled";

export type HochsterTool =
  | "filesystem"
  | "shell"
  | "docker"
  | "kubernetes"
  | "database"
  | "web"
  | "mcp"
  | "tests"
  | "security"
  | "observability"
  | "diff_patch"
  | "custom";

export type HochsterProblemType =
  | "code_bug"
  | "build_failure"
  | "test_failure"
  | "container_failure"
  | "runtime_exception"
  | "security_vulnerability"
  | "performance_bottleneck"
  | "dependency_conflict"
  | "configuration_error"
  | "unknown";

export type SubmitHochsterSolveRequest = {
  correlation_id: string;
  caller: {
    swarm_id: string;
    swarm_name: string;
    agent_id?: string;
    operator_id?: string;
  };
  problem: {
    type: HochsterProblemType;
    summary: string;
    severity: "low" | "medium" | "high" | "critical";
    language?: string;
    framework?: string;
    runtime?: string;
  };
  context: {
    repository?: string;
    branch?: string;
    commit_sha?: string;
    files?: string[];
    logs?: string[];
    stack_trace?: string;
    failing_tests?: string[];
    container_ids?: string[];
    docker_compose_files?: string[];
    evidence_refs?: string[];
  };
  allowed_tools: HochsterTool[];
  max_instances: number;
  timeout_seconds: number;
  callback_url?: string;
  constraints: {
    may_modify_files: boolean;
    may_run_commands: boolean;
    may_access_network: boolean;
    may_open_pull_request: boolean;
    requires_human_approval: boolean;
  };
};

export type SubmitHochsterSolveResponse = {
  request_id: string;
  status: "queued" | "assigned";
  assigned_instances: string[];
  correlation_id: string;
};

export type HochsterRequestStatusResponse = {
  request_id: string;
  status: HochsterRequestStatus;
  progress_percent: number;
  active_instances: string[];
  latest_trace_event?: string;
};

export type HochsterSolutionResponse = {
  request_id: string;
  solution: {
    solution_id: string;
    request_id: string;
    status: "candidate" | "validated" | "rejected" | "needs_review";
    root_cause: string;
    explanation: string;
    patch?: {
      diff: string;
      files_changed: string[];
      risk: "low" | "medium" | "high" | "critical";
    };
    validation: {
      tests_run: number;
      tests_passed: number;
      tests_failed: number;
      commands_executed: string[];
      evidence_refs: string[];
    };
    confidence: number;
  };
};

export type HochsterSolveRequest = SubmitHochsterSolveRequest & {
  request_id: string;
  requested_at: string;
  status: HochsterRequestStatus;
};

export type HochsterSolution = HochsterSolutionResponse["solution"] & {
  generated_at: string;
  security: {
    secrets_exposed: boolean;
    dependency_risks: string[];
    policy_warnings: string[];
  };
};

export type HochsterInstance = {
  instance_id: string;
  status: "online" | "idle" | "busy" | "offline";
  cpu_percent: number;
  memory_usage_gb: number;
  uptime_seconds: number;
  total_requests: number;
  queue_length: number;
  primary_swarm: string;
  region: string;
};

// Phase 25 types
export type SolverStrategy =
  | "minimal_patch"
  | "root_cause_first"
  | "test_first"
  | "security_first"
  | "performance_first"
  | "container_first"
  | "dependency_first"
  | "refactor_first";

export type SolverCandidate = {
  candidate_id: string;
  request_id: string;
  strategy: SolverStrategy;
  generated_at: string;
  root_cause: string;
  explanation: string;
  patch?: {
    diff: string;
    files_changed: string[];
  };
  validation: {
    tests_run: number;
    tests_passed: number;
    tests_failed: number;
    security_warnings: string[];
    regression_risk: "low" | "medium" | "high" | "critical";
  };
  scoring: {
    confidence: number;
    correctness_score: number;
    simplicity_score: number;
    safety_score: number;
    maintainability_score: number;
    total_score: number;
  };
  evidence_refs: string[];
};

export type SolutionMemoryRecord = {
  memory_id: string;
  created_at: string;
  scope: {
    tenant_id?: string;
    project_id?: string;
    repository?: string;
    language?: string;
    framework?: string;
  };
  problem_signature: {
    problem_type: string;
    stack_trace_hash?: string;
    error_message_hash?: string;
    dependency_fingerprint?: string;
  };
  solution: {
    root_cause: string;
    patch_summary: string;
    files_changed: string[];
    validation_status: "validated" | "rejected" | "needs_review";
    confidence: number;
  };
  governance: {
    reusable: boolean;
    redacted: boolean;
    approved_by?: string;
    evidence_refs: string[];
  };
};

// Phase 26 types
export type HochsterCertificationStatus =
  | "not_started"
  | "in_progress"
  | "passed"
  | "failed"
  | "conditional";

export type HochsterSecurityTest = {
  test_id: string;
  name: string;
  category:
    | "sandbox"
    | "tool_policy"
    | "prompt_injection"
    | "secret_redaction"
    | "supply_chain"
    | "mcp_manifest"
    | "artifact_integrity";
  severity: "low" | "medium" | "high" | "critical";
  status: "passed" | "failed" | "warning" | "not_run";
  evidence_refs: string[];
  findings: string[];
};

export type HochsterCertificationReport = {
  report_id: string;
  generated_at: string;
  version: string;
  status: HochsterCertificationStatus;
  tests: HochsterSecurityTest[];
  summary: {
    passed: number;
    failed: number;
    warnings: number;
    critical_findings: number;
  };
  release_decision: "allow" | "block" | "conditional";
};

// Phase 27 types
export type HochsterSlo = {
  slo_id: string;
  name: string;
  target: number;
  current: number;
  window: "24h" | "7d" | "30d";
  status: "healthy" | "warning" | "breached";
};

export type HochsterRolloutRing =
  | "internal_dev"
  | "platform_team"
  | "trusted_internal_swarms"
  | "pilot_tenants"
  | "enterprise_tenants"
  | "regulated_tenants";

export type HochsterRolloutState = {
  version: string;
  active_ring: HochsterRolloutRing;
  enabled_tenants: string[];
  blocked_tenants: string[];
  feature_flags: {
    distributed_solver_mesh: boolean;
    pr_automation: boolean;
    mcp_tools: boolean;
    docker_inspection: boolean;
    shell_sandbox: boolean;
  };
};

export type HochsterMarketplaceListing = {
  listing_id: string;
  name: "HOCHSTER";
  category: "debugging" | "devsecops" | "ai_agent" | "automation";
  version: string;
  description: string;
  capabilities: string[];
  required_permissions: string[];
  supported_environments: ("LOCAL" | "DEV" | "STAGING" | "PROD")[];
  pricing_model: "internal" | "per_request" | "per_tenant" | "usage_based";
  documentation_url?: string;
  support_contact?: string;
  certification: {
    status: "passed" | "conditional" | "failed";
    report_id?: string;
    sbom_ref?: string;
    provenance_ref?: string;
  };
};

export type RealtimeUiDatum<T> = {
  value: T;
  source: "live" | "cache" | "simulation" | "manual" | "unknown";
  source_id: string;
  observed_at: string;
  received_at: string;
  ttl_ms: number;
  freshness: "live" | "stale" | "expired" | "error";
  correlation_id?: string;
  evidence_refs: string[];
};


