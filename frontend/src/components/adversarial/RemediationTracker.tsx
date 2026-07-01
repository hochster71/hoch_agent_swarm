import { useChaosEngineStore } from "../../lib/adversarial/chaosEngine";
import { Hammer, CheckCircle2, AlertTriangle, ShieldCheck } from "lucide-react";

export function RemediationTracker() {
  const { remediations, resolveRemediation } = useChaosEngineStore();

  const openRemediations = remediations.filter((r) => r.status === "open");
  const resolvedRemediations = remediations.filter((r) => r.status === "resolved");

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Hammer className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200 uppercase">
            REMEDIATION & VULNERABILITY TRACKER
          </h3>
        </div>
        <span className="font-mono text-xs text-slate-500">
          Open: <strong className="text-red-400">{openRemediations.length}</strong> &bull; Resolved: <strong className="text-green-400">{resolvedRemediations.length}</strong>
        </span>
      </div>

      <div className="space-y-3 font-mono text-xs max-h-[260px] overflow-y-auto pr-1">
        {openRemediations.length > 0 ? (
          openRemediations.map((rem) => (
            <div
              key={rem.task_id}
              className="rounded border border-red-500/20 bg-red-500/5 p-3 hover:border-red-500/30 transition-all flex flex-col md:flex-row md:items-center justify-between gap-3"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
                  <span className="font-bold text-slate-200">{rem.scenario_name}</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-normal">{rem.description}</p>
                <div className="text-[9px] text-slate-500">
                  Task ID: <code className="text-slate-400">{rem.task_id}</code> &bull; Created at {rem.created_at.split("T")[1].slice(0, 5)}
                </div>
              </div>
              <button
                onClick={() => resolveRemediation(rem.task_id)}
                className="flex items-center gap-1 rounded bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 px-2 py-1 text-[10px] font-semibold text-green-400 transition-colors self-end md:self-center flex-shrink-0"
              >
                <ShieldCheck className="h-3 w-3" /> APPLY PATCH
              </button>
            </div>
          ))
        ) : (
          <div className="text-center py-6 border border-slate-900 rounded bg-slate-950/20 text-slate-500 italic">
            No active vulnerabilities or failed assertions requiring remediation.
          </div>
        )}

        {resolvedRemediations.length > 0 && (
          <div className="border-t border-slate-900 pt-3 space-y-2">
            <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block mb-1">PATCHED VULNERABILITIES</span>
            {resolvedRemediations.map((rem) => (
              <div key={rem.task_id} className="flex items-center justify-between text-[10px] bg-slate-950/60 p-2 rounded border border-slate-900/50 hover:border-slate-800">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                  <span>{rem.scenario_name}: {rem.description.slice(0, 45)}...</span>
                </div>
                <span className="status-badge success">PATCHED</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
