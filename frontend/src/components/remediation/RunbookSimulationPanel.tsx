import { useState, useEffect } from "react";
import type { Runbook } from "../../lib/remediation/runbookTypes";
import { simulateRunbook } from "../../lib/remediation/runbookSimulator";
import { PlayCircle, ShieldAlert, CheckCircle, Info } from "lucide-react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";

type Props = {
  runbook: Runbook;
  onClose: () => void;
};

export function RunbookSimulationPanel({ runbook, onClose }: Props) {
  const { startExecution } = useRemediationStore();
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<ReturnType<typeof simulateRunbook> | null>(null);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      const res = simulateRunbook(runbook);
      setResults(res);
      setLoading(false);

      // Audit simulated event
      if (typeof window !== "undefined" && window.addAuditEvent) {
        window.addAuditEvent({
          action: {
            type: "RUNBOOK_SIMULATED",
            summary: `Runbook simulated: ${runbook.name}. Blockers found: ${res.blockers.length}, Approvals required: ${res.required_approvals.length}`,
          },
          actor: {
            id: "operator",
            name: "Michael Hoch",
            type: "human",
            role: "Operator",
          },
          target: {
            type: "task",
            id: runbook.runbook_id,
            name: runbook.name,
          },
          result: res.executable ? "success" : "blocked",
          severity: res.executable ? "info" : "high",
          provenance: {
            source: "manual",
            evidence_refs: [],
          },
          policy: {
            required: false,
            result: "not_required",
          },
        });
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [runbook]);

  const handleExecute = async () => {
    try {
      const execId = await startExecution(runbook.runbook_id);
      alert(`Recovery initiated: ${execId}`);
      onClose();
    } catch (e: any) {
      alert(`Blocked: ${e.message}`);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <div className="flex items-center justify-between border-b border-slate-900 pb-2">
        <h3 className="text-xs font-bold text-slate-100 uppercase flex items-center gap-1.5">
          <PlayCircle className="h-4 w-4 text-cyan-400" />
          Runbook Simulation Lab
        </h3>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
          Close [X]
        </button>
      </div>

      {loading ? (
        <div className="text-center py-6 text-slate-500">
          <div className="animate-pulse">Analyzing runbook steps, evaluating permission overrides, and simulating containment boundaries...</div>
        </div>
      ) : (
        results && (
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="flex-1 space-y-3">
                
                {/* Blockers check */}
                <div>
                  <div className="text-[9px] text-slate-500 uppercase font-bold mb-1">Pre-Execution Blockers</div>
                  {results.blockers.length === 0 ? (
                    <div className="p-2 rounded bg-green-950/20 border border-green-800/40 text-green-400 flex items-center gap-1.5 font-bold">
                      <CheckCircle className="h-4 w-4" /> Ready for deployment. No system blockers identified.
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {results.blockers.map((b, idx) => (
                        <div key={idx} className="p-2 rounded bg-red-950/20 border border-red-800/40 text-red-400 flex items-center gap-1.5">
                          <ShieldAlert className="h-4 w-4 animate-pulse" /> {b}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Approvals */}
                <div>
                  <div className="text-[9px] text-slate-500 uppercase font-bold mb-1 font-mono">Operator Approvals Required</div>
                  {results.required_approvals.length === 0 ? (
                    <div className="text-slate-500 italic">No manual approvals required. Swarm can run autonomously.</div>
                  ) : (
                    <div className="p-2 rounded bg-orange-950/10 border border-orange-900/40 text-orange-400">
                      Step(s) requiring verification: <span className="font-bold">{results.required_approvals.join(", ")}</span>
                    </div>
                  )}
                </div>

                {/* Predicted impact */}
                <div>
                  <div className="text-[9px] text-slate-500 uppercase font-bold mb-1">Simulated Impact Report</div>
                  <ul className="space-y-1 text-slate-400">
                    {results.predicted_impact.map((pi, idx) => (
                      <li key={idx} className="flex gap-2">
                        <span>•</span>
                        <span>{pi}</span>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-900 pt-3">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded border border-slate-800 text-slate-400 hover:text-slate-200"
              >
                Dismiss
              </button>
              <button
                onClick={handleExecute}
                disabled={!results.executable}
                className={`px-4 py-1.5 rounded font-bold text-[11px] font-mono transition-all ${
                  results.executable
                    ? "bg-cyan-500 text-slate-950 hover:bg-cyan-400 cursor-pointer"
                    : "bg-slate-900 border border-slate-800 text-slate-600 cursor-not-allowed"
                }`}
              >
                Deploy Remediation
              </button>
            </div>
          </div>
        )
      )}
    </div>
  );
}
