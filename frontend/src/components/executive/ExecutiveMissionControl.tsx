import { PortfolioRiskSummary } from "./PortfolioRiskSummary";
import { SwarmPerformanceScorecards } from "./SwarmPerformanceScorecards";
import { buildExecutiveReport, downloadBoardReportFile } from "../../lib/executive/executiveReportBuilder";
import { FileText, Download, AlertTriangle, ShieldCheck, ArrowRight } from "lucide-react";
import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import { useChaosEngineStore } from "../../lib/adversarial/chaosEngine";

export function ExecutiveMissionControl() {
  const { systems } = useGovernanceRegistryStore();
  const { scenarios } = useChaosEngineStore();
  
  // Re-build report dynamically based on active state of other stores
  const report = buildExecutiveReport();

  const handleDownload = () => {
    downloadBoardReportFile(report);
  };

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case "critical":
        return "text-red-500 font-bold border-red-500/20 bg-red-500/10";
      case "high":
        return "text-orange-500 font-bold border-orange-500/20 bg-orange-500/10";
      case "medium":
        return "text-yellow-500 font-bold border-yellow-500/20 bg-yellow-500/10";
      default:
        return "text-green-500 font-bold border-green-500/20 bg-green-500/10";
    }
  };

  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
            <FileText className="h-5 w-5 text-cyan-400" />
            EXECUTIVE MISSION CONTROL & PORTFOLIO REPORTING
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Enterprise posture views, strategic investment advice, dynamic KPI scorecards, and board-ready evidence exports.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <PortfolioRiskSummary report={report} />
          <SwarmPerformanceScorecards />

          {/* Open Risks & Blocked Decisions Lists */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md font-mono text-xs">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="h-4 w-4 text-cyan-400" />
              <h3 className="font-semibold text-slate-200 tracking-wider">
                PORTFOLIO THREATS & BLOCKED MILESTONES
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Risks */}
              <div>
                <span className="font-bold text-slate-400 block mb-2 text-[10px] tracking-wider uppercase">Active Risks ({report.open_risks.length})</span>
                <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                  {report.open_risks.length > 0 ? (
                    report.open_risks.map((riskId) => {
                      const sys = systems.find((s: any) => s.system_id === riskId);
                      return (
                        <div key={riskId} className="flex items-center gap-2 text-[10px] bg-slate-900/60 p-1 rounded border border-slate-900">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
                          <span className="text-slate-300 truncate">{sys ? sys.name : riskId}</span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-slate-600 italic text-[10px]">No active critical/high risks registered.</div>
                  )}
                </div>
              </div>

              {/* Blocked decisions */}
              <div>
                <span className="font-bold text-slate-400 block mb-2 text-[10px] tracking-wider uppercase">Blocked Decisions ({report.blocked_decisions.length})</span>
                <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                  {report.blocked_decisions.length > 0 ? (
                    report.blocked_decisions.map((decId) => {
                      const sc = scenarios.find((s: any) => s.scenario_id === decId);
                      return (
                        <div key={decId} className="flex items-center gap-2 text-[10px] bg-slate-900/60 p-1 rounded border border-slate-900">
                          <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse flex-shrink-0" />
                          <span className="text-slate-300 truncate">{sc ? sc.name : decId}</span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-slate-600 italic text-[10px]">All safety enclaves gates are cleared.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Actionable Recommendations */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-green-400" />
                <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
                  EXECUTIVE RESOLUTION RECOMMENDATIONS
                </h3>
              </div>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 px-2 py-1 text-xs font-mono font-medium text-cyan-400 transition-all"
              >
                <Download className="h-3.5 w-3.5" />
                EXPORT BOARD REPORT
              </button>
            </div>

            <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
              {report.recommendations.map((rec) => (
                <div
                  key={rec.recommendation_id}
                  className="rounded border border-slate-900 bg-slate-950/40 p-4 hover:border-slate-800 transition-all font-mono text-xs"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-bold text-slate-200 text-sm leading-tight">{rec.title}</h4>
                    <span className={`rounded border px-2 py-0.5 text-[9px] font-bold uppercase ${getPriorityStyle(rec.priority)}`}>
                      {rec.priority}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">
                    {rec.summary}
                  </p>

                  <div className="mb-3 space-y-1">
                    <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider block">Rationale:</span>
                    <p className="text-slate-500 text-[10px] leading-normal">{rec.rationale}</p>
                  </div>

                  <div className="mb-3 space-y-1">
                    <span className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider block">Expected Impact:</span>
                    <p className="text-slate-500 text-[10px] leading-normal">{rec.expected_impact}</p>
                  </div>

                  <div className="rounded bg-slate-900/60 p-2.5 border border-slate-900 text-[10px] text-slate-300 flex items-center justify-between">
                    <div>
                      <span className="text-cyan-500 font-semibold">Action:</span>{" "}
                      <span>{rec.proposed_action}</span>
                    </div>
                    <ArrowRight className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
