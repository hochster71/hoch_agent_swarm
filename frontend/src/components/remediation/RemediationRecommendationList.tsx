import type { Runbook } from "../../lib/remediation/runbookTypes";
import { AlertTriangle, Play } from "lucide-react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";

type Props = {
  onSimulate: (rb: Runbook) => void;
};

export function RemediationRecommendationList({ onSimulate }: Props) {
  const { runbooks, startExecution } = useRemediationStore();

  // Map incidents to runbooks
  const recommendations = [
    { incident: "INC-3421: Phishing Email Campaign", runbookId: "phishing-response", severity: "high" },
    { incident: "INC-3417: Privilege Escalation Detected", runbookId: "privilege-reset", severity: "critical" },
    { incident: "INC-3409: Suspicious Data Exfiltration", runbookId: "contain-isolate", severity: "high" },
    { incident: "INC-3392: Malware Detected (Host)", runbookId: "malware-remediation", severity: "high" },
    { incident: "INC-3380: Failed Authentication Burst", runbookId: "access-throttle", severity: "medium" }
  ];

  const handleExecute = async (rbId: string) => {
    try {
      const execId = await startExecution(rbId);
      alert(`Recovery initiated: ${execId}`);
    } catch (e: any) {
      alert(`Blocked: ${e.message}`);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 border-b border-slate-900 pb-2 uppercase flex items-center gap-1.5">
        <AlertTriangle className="h-4 w-4 text-orange-400" />
        Recommended Remediation Workflows
      </h3>

      <div className="space-y-2">
        {recommendations.map((rec, i) => {
          const rb = runbooks.find(r => r.runbook_id === rec.runbookId);
          if (!rb) return null;
          return (
            <div key={i} className="p-2.5 rounded bg-slate-900/20 border border-slate-850 flex justify-between items-center">
              <div>
                <span className="font-bold text-slate-200">{rec.incident}</span>
                <span className="text-slate-500 block text-[9px] uppercase mt-0.5">Runbook: {rb.name} ({rb.version})</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onSimulate(rb)}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400 font-bold hover:bg-slate-800 text-[10px]"
                >
                  Simulate
                </button>
                <button
                  onClick={() => handleExecute(rec.runbookId)}
                  className="px-2.5 py-1 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 text-[10px] flex items-center gap-1"
                >
                  <Play className="h-3 w-3 fill-slate-950" /> Execute
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
