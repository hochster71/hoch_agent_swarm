import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import { downloadGovernanceEvidenceFile } from "../../lib/governance/governanceEvidence";
import { FileText, Download, Database } from "lucide-react";

export function GovernanceEvidencePanel() {
  const { systems } = useGovernanceRegistryStore();

  const handleExport = () => {
    downloadGovernanceEvidenceFile(systems);
  };

  // Collect all evidence references from systems
  const allEvidence: { systemName: string; controlId: string; ref: string }[] = [];
  systems.forEach((sys) => {
    sys.controls.forEach((ctrl) => {
      ctrl.evidence_refs.forEach((ref) => {
        allEvidence.push({
          systemName: sys.name,
          controlId: ctrl.control_id,
          ref,
        });
      });
    });
  });

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            GOVERNANCE EVIDENCE REGISTRY
          </h3>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 px-2 py-1 text-xs font-mono font-medium text-cyan-400 transition-all"
        >
          <Download className="h-3.5 w-3.5" />
          GENERATE COMPLIANCE REPORT
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left side: Evidence stats */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3 flex flex-col justify-between font-mono text-xs text-slate-400">
          <div className="space-y-2">
            <span className="font-bold text-slate-200">EVIDENCE OVERVIEW</span>
            <div className="grid grid-cols-2 gap-2 text-center py-2">
              <div className="rounded bg-slate-900 p-2">
                <div className="text-lg font-bold text-cyan-400">{allEvidence.length}</div>
                <div className="text-[9px] text-slate-500">CAPTURED LINKS</div>
              </div>
              <div className="rounded bg-slate-900 p-2">
                <div className="text-lg font-bold text-green-400">
                  {systems.reduce((acc, sys) => acc + sys.controls.filter(c => c.status === "implemented").length, 0)}
                </div>
                <div className="text-[9px] text-slate-500">PASSED CONTROLS</div>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 leading-normal">
              Compliance report collects evidence references mapped in the matrix, compiling an exportable audit bundle confirming system alignment with NIST AI RMF guidelines.
            </p>
          </div>
        </div>

        {/* Right side: Evidence links feed */}
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3 font-mono text-xs">
          <span className="font-bold text-slate-200 block mb-2">LIVE EVIDENCE LOGS</span>
          <div className="space-y-2 max-h-[140px] overflow-y-auto pr-1">
            {allEvidence.length > 0 ? (
              allEvidence.map((ev, idx) => (
                <div key={idx} className="flex items-start gap-2 text-[10px] bg-slate-950/60 p-1.5 rounded border border-slate-900/50 hover:border-slate-800">
                  <Database className="h-3.5 w-3.5 text-cyan-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-semibold text-slate-300">{ev.ref}</div>
                    <div className="text-slate-500 text-[9px]">
                      Mapped to {ev.systemName} &bull; Control {ev.controlId}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-slate-600 italic text-[11px] py-4 text-center">
                No active evidence references generated yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
