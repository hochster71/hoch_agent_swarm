export type NavOperationalContract = {
  id: string;
  label: string;
  endpoint: string;
  expectedFreshness: "live" | "planned" | "stale" | "error";
  releaseIntroduced: string;
};

export const navOperationalContracts: NavOperationalContract[] = [
  {
    id: "readiness-autopilot",
    label: "Readiness Autopilot",
    endpoint: "/api/v1/readiness/status",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.4-OPERATIONAL-READINESS-AUTOPILOT",
  },
  {
    id: "hochster-runtime",
    label: "HOCHSTER Runtime",
    endpoint: "/api/v1/hochster/health",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.3-HOCHSTER-RUNTIME-EXECUTION-AUDIT",
  },
  {
    id: "remediation-safety",
    label: "Remediation Safety",
    endpoint: "/api/v1/readiness/budget-report",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.5-AUTONOMOUS-REMEDIATION-SAFETY-GATES",
  },
  {
    id: "runtime-audit",
    label: "Runtime Audit",
    endpoint: "/api/v1/audit/runtime/execution",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.3-HOCHSTER-RUNTIME-EXECUTION-AUDIT",
  },
  {
    id: "error-budget",
    label: "Error Budget",
    endpoint: "/api/v1/readiness/budget-report",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY",
  },
  {
    id: "release-provenance",
    label: "Release Provenance",
    endpoint: "/api/v1/hochster/baseline/lock",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.2-SUPPLY-CHAIN-PROVENANCE",
  },
  {
    id: "swarm-control",
    label: "Swarm Control",
    endpoint: "/api/v1/agents/status",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.0-RT-LOCK",
  },
  {
    id: "mission-intel",
    label: "Mission Intel",
    endpoint: "/api/v1/audit/events",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.0-RT-LOCK",
  },
  {
    id: "timeline-replay",
    label: "Timeline Replay",
    endpoint: "/api/v1/audit/events",
    expectedFreshness: "live",
    releaseIntroduced: "v0.1.0-RT-LOCK",
  },
];
