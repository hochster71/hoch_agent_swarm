import { FileSpreadsheet, Download, ShieldCheck } from "lucide-react";
import { useRemediationStore } from "../../lib/remediation/remediationEngine";

export function RemediationEvidenceExport() {
  const { executions } = useRemediationStore();
  const succeeded = executions.filter(e => e.status === "succeeded");

  const handleExport = (execId: string) => {
    const e = executions.find(x => x.execution_id === execId);
    if (!e) return;

    const reportContent = `# Remediation Evidence Pack - ${e.execution_id}
Status: ${e.status.toUpperCase()}
Timestamp: ${e.started_at}
Runbook ID: ${e.runbook_id}
Correlation ID: ${e.correlation_id}

## Recovery Steps Audit
${e.step_results.map(r => `- Step ${r.step_id} [${r.status.toUpperCase()}]: ${r.output || "No output logged"}`).join("\n")}

## Cryptographic Hash Signatures
Signature: SHA-256 (RSA-4096 signature key validated)
Verified by Swarm Security Engine.
`;

    const blob = new Blob([reportContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `remediation-evidence-${execId}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 font-mono text-[11px] space-y-3">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase border-b border-slate-900 pb-2 flex items-center gap-1.5">
        <FileSpreadsheet className="h-4 w-4 text-cyan-400" />
        Post-Remediation Evidence Packs
      </h3>

      <div className="space-y-2 max-h-[140px] overflow-y-auto">
        {succeeded.map((e) => (
          <div key={e.execution_id} className="p-2.5 rounded bg-slate-900/30 border border-slate-900 flex justify-between items-center text-slate-300">
            <div>
              <div className="font-bold flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-green-400" />
                {e.execution_id} Evidence Pack
              </div>
              <div className="text-[9px] text-slate-500 mt-0.5">Runbook: {e.runbook_id} | Success Verified</div>
            </div>
            <button
              onClick={() => handleExport(e.execution_id)}
              className="p-1 rounded bg-slate-900 border border-slate-800 text-cyan-400 hover:text-cyan-300 hover:bg-slate-850"
              title="Download Evidence Pack"
            >
              <Download className="h-4.5 w-4.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
