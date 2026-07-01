import { RefreshCw, History, ShieldAlert } from "lucide-react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";

export function RollbackPlanPanel() {
  const { executions } = useRemediationStore();
  const rolledBackExecs = executions.filter(e => e.status === "rolled_back");

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase flex items-center gap-1.5">
          <RefreshCw className="h-4 w-4 text-orange-400 animate-spin" />
          Rollback Control Center
        </h3>
        <span className="text-[10px] text-slate-500 font-bold uppercase">{rolledBackExecs.length} Executed</span>
      </div>

      <div className="space-y-2">
        {rolledBackExecs.length === 0 ? (
          <div className="text-slate-600 italic py-2 text-center">No active rollback plans deployed in cluster histories.</div>
        ) : (
          rolledBackExecs.map((e, idx) => (
            <div key={idx} className="p-2.5 rounded bg-orange-950/5 border border-orange-900/30 flex justify-between items-center text-orange-300">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-orange-500" />
                <div>
                  <div className="font-bold">{e.execution_id} Rollback Restored</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">Runbook: {e.runbook_id} | Completed: {e.completed_at ? new Date(e.completed_at).toLocaleTimeString() : "N/A"}</div>
                </div>
              </div>
              <span className="text-[9px] bg-orange-950/20 border border-orange-900/40 text-orange-400 px-1.5 py-0.5 rounded font-bold uppercase">
                Restored
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
