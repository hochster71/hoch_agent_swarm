import { AiSystemRegistry } from "./AiSystemRegistry";
import { AiRiskRegister } from "./AiRiskRegister";
import { ControlMappingMatrix } from "./ControlMappingMatrix";
import { GovernanceEvidencePanel } from "./GovernanceEvidencePanel";
import { GovernanceReviewQueue } from "./GovernanceReviewQueue";
import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import { Shield, Settings, Server, Eye } from "lucide-react";

export function GovernanceControlPlane() {
  const { systems } = useGovernanceRegistryStore();

  const totalSystems = systems.length;
  const highRiskSystems = systems.filter((s) => s.risk_tier === "high" || s.risk_tier === "critical").length;
  const pendingReviews = systems.filter((s) => s.status === "under_review").length;

  // Calculate overall controls implementation coverage
  let totalControls = 0;
  let implementedControls = 0;
  systems.forEach((s) => {
    s.controls.forEach((c) => {
      totalControls++;
      if (c.status === "implemented") {
        implementedControls++;
      }
    });
  });
  const overallCoverage = totalControls > 0 
    ? Math.round((implementedControls / totalControls) * 100) 
    : 0;

  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
            <Shield className="h-5 w-5 text-cyan-400" />
            AI GOVERNANCE, RISK & COMPLIANCE CONTROL PLANE
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-1">
            System registries, NIST AI RMF risk scorecards, oversight review queue, and compliance control matrices.
          </p>
        </div>
      </div>

      {/* Summary Scorecard Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>REGISTERED SYSTEMS</span>
            <Server className="h-4 w-4 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{totalSystems}</div>
          <div className="text-[10px] text-slate-500 mt-1">Active inventory profile</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>HIGH / CRITICAL RISK</span>
            <Shield className="h-4 w-4 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-red-500 mt-2">{highRiskSystems}</div>
          <div className="text-[10px] text-slate-500 mt-1">Systems requiring review</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>PENDING REVIEW</span>
            <Eye className="h-4 w-4 text-yellow-500" />
          </div>
          <div className="text-2xl font-bold text-yellow-500 mt-2">{pendingReviews}</div>
          <div className="text-[10px] text-slate-500 mt-1">Awaiting oversight approval</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>OVERALL COVERAGE</span>
            <Settings className="h-4 w-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-green-500 mt-2">{overallCoverage}%</div>
          <div className="text-[10px] text-slate-500 mt-1">Framework controls passed</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <AiSystemRegistry />
          <GovernanceReviewQueue />
        </div>
        <div className="space-y-6">
          <AiRiskRegister />
          <ControlMappingMatrix />
          <GovernanceEvidencePanel />
        </div>
      </div>
    </div>
  );
}
