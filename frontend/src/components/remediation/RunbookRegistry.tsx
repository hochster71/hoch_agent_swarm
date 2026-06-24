import { useRemediationStore } from "../../lib/remediation/remediationEngine";
import type { Runbook } from "../../lib/remediation/runbookTypes";
import { BookOpen, AlertTriangle } from "lucide-react";

type Props = {
  onSelect: (rb: Runbook) => void;
  selectedId?: string;
};

export function RunbookRegistry({ onSelect, selectedId }: Props) {
  const { runbooks } = useRemediationStore();

  const getRiskColor = (risk: Runbook["risk"]) => {
    switch (risk) {
      case "critical": return "text-red-500 font-bold";
      case "high": return "text-orange-500";
      case "medium": return "text-yellow-500";
      default: return "text-green-500";
    }
  };

  const getStatusColor = (status: Runbook["status"]) => {
    switch (status) {
      case "approved": return "text-green-400";
      case "validated": return "text-blue-400";
      default: return "text-slate-500";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px]">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2 border-b border-slate-900 pb-2">
        <BookOpen className="h-4 w-4 text-cyan-400" />
        Runbook Library Registry
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-900 text-[10px] text-slate-500 uppercase font-bold">
              <th className="py-2">Runbook Name</th>
              <th className="py-2">Version</th>
              <th className="py-2">Risk</th>
              <th className="py-2 text-center">Steps</th>
              <th className="py-2 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {runbooks.map((rb) => {
              const active = selectedId === rb.runbook_id;
              return (
                <tr
                  key={rb.runbook_id}
                  onClick={() => onSelect(rb)}
                  className={`border-b border-slate-900/50 cursor-pointer hover:bg-slate-900/30 transition-all ${
                    active ? "bg-cyan-950/20 text-cyan-200 border-l-2 border-l-cyan-500" : "text-slate-300"
                  }`}
                >
                  <td className="py-2.5 font-bold pl-1">{rb.name}</td>
                  <td className="py-2.5 text-slate-500">{rb.version}</td>
                  <td className={`py-2.5 uppercase font-bold ${getRiskColor(rb.risk)}`}>{rb.risk}</td>
                  <td className="py-2.5 text-center text-slate-400 font-bold">{rb.steps.length}</td>
                  <td className={`py-2.5 text-center uppercase font-bold ${getStatusColor(rb.status)}`}>{rb.status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
