export type ReleaseManifest = {
  release: {
    version: string;
    codename: string;
    generated_at: string;
    generated_by: string;
    git_commit_sha: string;
    git_branch: string;
    ci_provider?: "github_actions" | "local" | "unknown";
    ci_run_id?: string;
    ci_run_url?: string;
  };
  artifacts: {
    path: string;
    type:
      | "evidence_pack"
      | "checksum"
      | "provenance"
      | "sbom"
      | "decision_memo"
      | "verification_report";
    sha256: string;
  }[];
  docker: {
    service: string;
    image: string;
    digest?: string;
    warning?: string;
  }[];
  baseline_chain: {
    previous: "v0.1.0-RT-LOCK";
    hardening: "v0.1.1-HOCHSTER-CLUSTER-HARDENING";
    current: "v0.1.2-SUPPLY-CHAIN-PROVENANCE";
  };
  integrity: {
    signed: boolean;
    signature_refs: string[];
    provenance_ref: string;
    sbom_ref: string;
  };
  hochster: {
    cluster_jobs_completed: number;
    cluster_jobs_blocked: number;
    missing_trace_ids: string[];
    missing_evidence_refs: string[];
  };
  decision: {
    status: "PASS" | "BLOCK";
    blockers: string[];
    warnings: string[];
  };
};
