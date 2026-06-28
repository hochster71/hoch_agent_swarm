import { ScenarioLibrary } from "./ScenarioLibrary";
import { ChaosDrillPanel } from "./ChaosDrillPanel";
import { SafetyAssertionResults } from "./SafetyAssertionResults";
import { RemediationTracker } from "./RemediationTracker";
import { ShieldAlert, Terminal, AlertTriangle } from "lucide-react";
import { useChaosEngineStore } from "../../lib/adversarial/chaosEngine";

export function RedTeamDashboard() {
  const { scenarios, remediations } = useChaosEngineStore();

  const totalDrillsRun = scenarios.filter((s) => s.result !== undefined).length;
  const passedDrills = scenarios.filter((s) => s.result?.status === "passed").length;
  const failedDrills = scenarios.filter((s) => s.result?.status === "failed").length;
  const openRemediationsCount = remediations.filter((r) => r.status === "open").length;

  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-orange-500 animate-pulse" />
            RED-TEAM, CHAOS & ADVERSARIAL SIMULATION LAYER
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Controlled fault injection, policy bypass simulation, safety assertion auditing, and auto-patch remediation cycles.
          </p>
        </div>
      </div>

      {/* Summary Scorecard Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>SCENARIOS RUN</span>
            <Terminal className="h-4 w-4 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold text-slate-200 mt-2">{totalDrillsRun}</div>
          <div className="text-[10px] text-slate-500 mt-1">Total completed drills</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>PASSED CHECKS</span>
            <ShieldAlert className="h-4 w-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-green-500 mt-2">{passedDrills}</div>
          <div className="text-[10px] text-slate-500 mt-1">Matched safety assertions</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>FAILED ASSERTIONS</span>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </div>
          <div className="text-2xl font-bold text-red-500 mt-2">{failedDrills}</div>
          <div className="text-[10px] text-slate-500 mt-1">Failed guardrail conditions</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4">
          <div className="flex items-center justify-between text-slate-500">
            <span>OPEN REMEDIATIONS</span>
            <AlertTriangle className="h-4 w-4 text-orange-500" />
          </div>
          <div className="text-2xl font-bold text-orange-500 mt-2">{openRemediationsCount}</div>
          <div className="text-[10px] text-slate-500 mt-1">Pending patch adjustments</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <ScenarioLibrary />
        </div>
        <div className="space-y-6">
          <ChaosDrillPanel />
          <SafetyAssertionResults />
          <RemediationTracker />
        </div>
      </div>
    </div>
  );
}
