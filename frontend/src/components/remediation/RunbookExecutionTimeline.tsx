import { useRemediationStore } from "../../lib/remediation/remediationEngine";
import { CheckCircle2, XCircle, Loader2, Play, AlertCircle, RefreshCw } from "lucide-react";

export function RunbookExecutionTimeline() {
  const { activeExecution, runbooks, approveExecutionStep, triggerRollback, clearActiveExecution } = useRemediationStore();

  if (!activeExecution) {
    return null;
  }

  const rb = runbooks.find((r) => r.runbook_id === activeExecution.runbook_id);
  if (!rb) return null;

  // Calculate progress
  const totalSteps = rb.steps.length;
  const completedSteps = activeExecution.step_results.filter((sr) => sr.status === "succeeded").length;
  const progressPercent = Math.round((completedSteps / totalSteps) * 100);

  const getStepStatusBadge = (status: string) => {
    switch (status) {
      case "succeeded":
        return <span className="text-green-400 font-bold flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Success</span>;
      case "running":
        return (
          <span className="text-cyan-400 font-bold flex items-center gap-1 animate-pulse">
            <Loader2 className="h-3 w-3 animate-spin" /> Running
          </span>
        );
      case "failed":
        return <span className="text-red-400 font-bold flex items-center gap-1"><XCircle className="h-3 w-3" /> Failed</span>;
      case "skipped":
        return <span className="text-slate-500 font-bold">Skipped</span>;
      default:
        return <span className="text-slate-600 font-bold">Pending</span>;
    }
  };

  const handleRollback = () => {
    if (confirm("Are you sure you want to trigger manual rollback for this recovery?")) {
      triggerRollback(activeExecution.execution_id);
    }
  };

  const getExecutionStatusBadge = () => {
    switch (activeExecution.status) {
      case "succeeded":
        return "bg-green-950 border-green-800/40 text-green-400";
      case "failed":
        return "bg-red-950 border-red-800/40 text-red-400";
      case "rolled_back":
        return "bg-orange-950 border-orange-800/40 text-orange-400";
      case "paused":
        return "bg-yellow-950 border-yellow-800/40 text-yellow-400 animate-pulse";
      default:
        return "bg-blue-950 border-blue-800/40 text-cyan-400 animate-pulse";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 backdrop-blur-md p-4 font-mono text-[11px] space-y-4">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 font-bold uppercase">{activeExecution.execution_id}</span>
            <span className={`text-[8px] font-bold uppercase border px-1.5 rounded ${getExecutionStatusBadge()}`}>
              {activeExecution.status}
            </span>
          </div>
          <h3 className="font-bold text-slate-100 mt-1">{rb.name}</h3>
        </div>
        <button onClick={clearActiveExecution} className="text-slate-500 hover:text-slate-300">
          Close [X]
        </button>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-[9px] text-slate-500 font-bold">
          <span>RUNNING STEP: {completedSteps} / {totalSteps}</span>
          <span>{progressPercent}% COMPLETE</span>
        </div>
        <div className="w-full bg-slate-900 rounded-full h-1.5">
          <div className="h-1.5 rounded-full bg-cyan-500 transition-all" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      {/* Steps Table */}
      <div className="space-y-2 mt-3">
        {rb.steps.map((step) => {
          const res = activeExecution.step_results.find((sr) => sr.step_id === step.step_id);
          const isPaused = activeExecution.status === "paused" && activeExecution.current_step_id === step.step_id;
          
          return (
            <div
              key={step.step_id}
              className={`p-2.5 rounded border transition-all flex flex-col gap-2 ${
                res?.status === "running"
                  ? "bg-cyan-950/10 border-cyan-800/40 text-cyan-200"
                  : isPaused
                  ? "bg-yellow-950/10 border-yellow-800/40 text-yellow-200"
                  : "bg-slate-900/30 border-slate-900/60 text-slate-400"
              }`}
            >
              <div className="flex justify-between items-start">
                <div className="flex gap-2">
                  <span className="font-bold">#{step.order}</span>
                  <div>
                    <div className="font-bold text-slate-200">{step.title}</div>
                    <div className="text-[9px] text-slate-500 mt-0.5">{step.description}</div>
                  </div>
                </div>
                <div>{getStepStatusBadge(isPaused ? "pending" : res?.status || "pending")}</div>
              </div>

              {/* Approval Request UI */}
              {isPaused && (
                <div className="p-2 rounded bg-yellow-950/20 border border-yellow-800/40 flex items-center justify-between mt-1">
                  <div className="flex items-center gap-1.5 text-yellow-400">
                    <AlertCircle className="h-4 w-4 animate-bounce" />
                    <span>Awaiting human-in-the-loop authorization to proceed.</span>
                  </div>
                  <button
                    onClick={() => approveExecutionStep(activeExecution.execution_id, step.step_id)}
                    className="px-3 py-1 rounded bg-yellow-500 text-slate-950 font-bold hover:bg-yellow-400 text-[9px] font-mono uppercase"
                  >
                    Authorize Step
                  </button>
                </div>
              )}

              {/* Output log */}
              {res?.output && (
                <div className="text-[9px] bg-black/40 border border-slate-900 p-2 rounded text-slate-400 leading-normal mt-1">
                  <div className="text-[8px] text-slate-600 font-bold uppercase mb-1">Execution output feed:</div>
                  {res.output}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Rollback and cancel actions footer */}
      {activeExecution.status === "running" && activeExecution.rollback.available && (
        <div className="flex justify-end pt-2 border-t border-slate-900">
          <button
            onClick={handleRollback}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold bg-orange-950 border border-orange-850 text-orange-400 hover:bg-orange-900/30 transition-all font-mono"
          >
            <RefreshCw className="h-3 w-3" /> Trigger Rollback
          </button>
        </div>
      )}
    </div>
  );
}
