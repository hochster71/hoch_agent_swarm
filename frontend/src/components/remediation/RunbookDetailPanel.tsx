import type { Runbook } from "../../lib/remediation/runbookTypes";
import { Info, Play, ClipboardList, ShieldAlert } from "lucide-react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";

type Props = {
  runbook: Runbook;
  onSimulate: () => void;
};

export function RunbookDetailPanel({ runbook, onSimulate }: Props) {
  const { startExecution } = useRemediationStore();

  const handleExecute = async () => {
    try {
      const execId = await startExecution(runbook.runbook_id);
      alert(`Recovery initiated: ${execId}`);
    } catch (e: any) {
      alert(`Execution Blocked: ${e.message}`);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <div>
          <h3 className="text-xs font-bold text-slate-100">{runbook.name}</h3>
          <span className="text-[9px] text-slate-500">Trigger Conditions: {runbook.trigger_conditions.join(" | ")}</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onSimulate}
            className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400 font-bold hover:bg-slate-800 text-[10px]"
          >
            Simulate
          </button>
          <button
            onClick={handleExecute}
            className="px-2.5 py-1 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 text-[10px] flex items-center gap-1"
          >
            <Play className="h-3 w-3 fill-slate-950" /> Execute
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-[9px] text-slate-500 uppercase font-bold">Execution Steps Checklist</div>
        {runbook.steps.map((step) => (
          <div key={step.step_id} className="p-2.5 rounded bg-slate-900/30 border border-slate-900 flex justify-between items-start gap-4">
            <div className="flex gap-2">
              <span className="text-cyan-500 font-bold">#{step.order}</span>
              <div>
                <div className="font-bold text-slate-300">{step.title}</div>
                <div className="text-[9px] text-slate-500 mt-0.5">{step.description}</div>
                {step.command_text && (
                  <code className="block text-[8px] bg-black/40 border border-slate-800 text-emerald-400 p-1 rounded font-mono mt-1 w-fit max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap">
                    {step.command_text}
                  </code>
                )}
              </div>
            </div>
            {step.requires_approval && (
              <span className="flex items-center gap-0.5 text-[8px] font-bold text-orange-400 border border-orange-800/40 bg-orange-950/20 px-1 rounded uppercase">
                <ShieldAlert className="h-2.5 w-2.5" /> Approval Req.
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
