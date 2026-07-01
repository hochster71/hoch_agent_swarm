import { ShieldCheck, Activity, Award } from "lucide-react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";

export function OutcomeVerificationPanel() {
  const { executions } = useRemediationStore();
  const total = executions.length;
  const succeeded = executions.filter(e => e.status === "succeeded").length;
  const successRate = total > 0 ? Math.round((succeeded / total) * 100) : 100;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1.5">
        <ShieldCheck className="h-4 w-4 text-green-400" />
        Recovery Outcome Metrics (30d)
      </h3>

      <div className="grid grid-cols-2 gap-3 text-center">
        <div className="p-3 bg-slate-900/20 border border-slate-900 rounded">
          <span className="text-slate-500 text-[8px] uppercase block">Recovery Success Rate</span>
          <span className="text-2xl font-bold text-green-400 block mt-1">{successRate}%</span>
          <span className="text-[8px] text-slate-600 block mt-0.5">Target: 90% Threshold</span>
        </div>
        <div className="p-3 bg-slate-900/20 border border-slate-900 rounded">
          <span className="text-slate-500 text-[8px] uppercase block">Closed-Loop MTTR</span>
          <span className="text-2xl font-bold text-cyan-400 block mt-1">2.4 Hours</span>
          <span className="text-[8px] text-slate-600 block mt-0.5">Average recovery window</span>
        </div>
      </div>
    </div>
  );
}
