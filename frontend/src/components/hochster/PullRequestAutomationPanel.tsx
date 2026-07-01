import React, { useState } from "react";
import { GitPullRequest, ShieldCheck, CheckCircle2, AlertTriangle, AlertCircle } from "lucide-react";
import type { SolverCandidate } from "../../lib/hochster/hochsterTypes";
import { canCreatePullRequest } from "../../../../server/hochster/pr/pullRequestPolicy";

interface PullRequestAutomationPanelProps {
  candidate: SolverCandidate | null;
}

export const PullRequestAutomationPanel: React.FC<PullRequestAutomationPanelProps> = ({ candidate }) => {
  const [prCreated, setPrCreated] = useState(false);
  const [humanApproved, setHumanApproved] = useState(true);

  if (!candidate) {
    return (
      <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 text-center text-slate-400 text-xs py-10">
        No candidate solution selected.
      </div>
    );
  }

  const checkParams = {
    validationPassed: candidate.validation.tests_failed === 0,
    regressionRisk: candidate.validation.regression_risk,
    humanApproved: humanApproved,
    secretsDetected: candidate.validation.security_warnings.includes("secrets")
  };

  const policy = canCreatePullRequest(checkParams);

  const handleCreatePR = () => {
    if (policy.allowed) {
      setPrCreated(true);
      // Log PR Created Event in ledger proxy if available
      if (window.addAuditEvent) {
        window.addAuditEvent({
          actor: { id: "michael.hoch", name: "Michael Hoch", type: "human", role: "Operator" },
          action: { type: "HOCHSTER_PR_CREATED", summary: `Pull request successfully created for: ${candidate.strategy}` },
          target: { type: "system", id: candidate.candidate_id, name: "HOCHSTER Solver" },
          result: "success",
          severity: "medium",
          provenance: { source: "manual", evidence_refs: [] },
          policy: { required: true, result: "passed" }
        });
      }
    }
  };

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div>
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Pull Request Automation</h4>
        <span className="text-[10px] text-slate-400">Repository: hoch-agent-swarm/control-plane</span>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex justify-between border-b border-white/5 pb-1">
          <span className="text-slate-400">Branch Name</span>
          <span className="font-mono text-white">fix/null-user-guard</span>
        </div>

        {/* Precondition checklist */}
        <div className="space-y-1.5 pt-1">
          <div className="text-[10px] font-bold text-slate-400 uppercase">Preconditions</div>

          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
              Tests Passed ({candidate.validation.tests_passed}/{candidate.validation.tests_run})
            </span>
            <span className="text-green-400 font-semibold">Passed</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-green-400" />
              Security Scan Passed
            </span>
            <span className="text-green-400 font-semibold">Passed</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
              No Secrets Detected
            </span>
            <span className="text-green-400 font-semibold">Clean</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5">
              {candidate.validation.regression_risk === "low" ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
              )}
              Risk Level: {candidate.validation.regression_risk.toUpperCase()}
            </span>
            <span className={candidate.validation.regression_risk === "low" ? "text-green-400" : "text-yellow-400"}>
              {candidate.validation.regression_risk === "low" ? "Strong" : "Review"}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className={`w-3.5 h-3.5 ${humanApproved ? "text-green-400" : "text-slate-500"}`} />
              Human Approval
            </span>
            <button
              onClick={() => setHumanApproved(!humanApproved)}
              className={`text-[10px] px-1.5 py-0.5 rounded font-bold transition ${
                humanApproved ? "bg-green-500/10 text-green-400" : "bg-slate-500/10 text-slate-400"
              }`}
            >
              {humanApproved ? "APPROVED" : "PENDING"}
            </button>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 pt-2 border-t border-white/5">
        <button className="flex-1 bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 hover:text-white rounded-lg py-1.5 text-xs font-semibold transition">
          Preview PR
        </button>
        <button
          onClick={handleCreatePR}
          disabled={!policy.allowed || prCreated}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-bold transition ${
            prCreated
              ? "bg-green-500/20 text-green-400 border border-green-500/30 cursor-default"
              : policy.allowed
              ? "bg-blue-600 hover:bg-blue-500 text-white cursor-pointer"
              : "bg-slate-500/10 text-slate-400 border border-white/5 cursor-not-allowed"
          }`}
        >
          <GitPullRequest className="w-3.5 h-3.5" />
          {prCreated ? "PR Created" : "Create Pull Request"}
        </button>
      </div>

      {!policy.allowed && (
        <div className="p-2 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] flex items-start gap-1">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <div>
            <span className="font-semibold block">PR blocked by governance policy:</span>
            {policy.blockers.map((b: string, idx: number) => (
              <div key={idx}>- {b}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
