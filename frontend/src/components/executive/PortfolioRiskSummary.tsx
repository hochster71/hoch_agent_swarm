import type { ExecutiveReport } from "../../lib/executive/executiveTypes";
import { ShieldAlert } from "lucide-react";

type PortfolioRiskSummaryProps = {
  report: ExecutiveReport;
};

export function PortfolioRiskSummary({ report }: PortfolioRiskSummaryProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "strong":
        return "text-green-400 bg-green-500/10 border-green-500/30";
      case "stable":
        return "text-cyan-400 bg-cyan-500/10 border-cyan-500/30";
      case "watch":
        return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30";
      case "degraded":
        return "text-orange-400 bg-orange-500/10 border-orange-500/30 pulsing-orange";
      case "critical":
        return "text-red-400 bg-red-500/10 border-red-500/30 pulsing-red";
      default:
        return "text-slate-400 bg-slate-500/10 border-slate-500/30";
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-400";
    if (score >= 75) return "text-cyan-400";
    if (score >= 60) return "text-yellow-400";
    if (score >= 40) return "text-orange-400";
    return "text-red-500";
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
            EXECUTIVE MISSION POSTURE SUMMARY
          </h3>
        </div>
        <span className={`status-badge border px-3 py-1 font-mono rounded capitalize ${getStatusColor(report.posture.overall_status)}`}>
          {report.posture.overall_status}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Posture Score Block */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-4 flex flex-col items-center justify-center font-mono">
          <div className="text-sm text-slate-400 font-bold mb-1">OVERALL STATUS</div>
          <div className={`text-4xl font-extrabold tracking-wider ${getScoreColor(report.posture.risk_score)}`}>
            {report.posture.overall_status.toUpperCase()}
          </div>
          <div className="text-[10px] text-slate-500 mt-2 text-center">
            Computed from ZTA posture checks, open risks, and failed enclaves release gates.
          </div>
        </div>

        {/* Individual Scores */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-4 font-mono space-y-3 text-xs text-slate-300">
          <span className="font-bold text-slate-200 block mb-1 uppercase text-[10px] tracking-wider">KPI Posture Scorecards</span>
          
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Governance Score:</span>
            <span className={`font-bold ${getScoreColor(report.posture.governance_score)}`}>
              {report.posture.governance_score}/100
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Release Readiness:</span>
            <span className={`font-bold ${getScoreColor(report.posture.readiness_score)}`}>
              {report.posture.readiness_score}/100
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Risk Management:</span>
            <span className={`font-bold ${getScoreColor(report.posture.risk_score)}`}>
              {report.posture.risk_score}/100
            </span>
          </div>

          <div className="flex justify-between items-center border-t border-slate-900 pt-2 text-[11px]">
            <span className="text-slate-400">Compliance Mappings:</span>
            <span className="font-bold text-green-400">
              {report.posture.compliance_coverage_percent}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
