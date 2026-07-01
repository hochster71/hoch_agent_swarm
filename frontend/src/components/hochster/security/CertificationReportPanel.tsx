import React from "react";
import { CheckCircle2, ShieldAlert } from "lucide-react";

export const CertificationReportPanel: React.FC = () => {
  const policies = [
    { name: "Tool Policy Engine Enforced", status: "Enabled" },
    { name: "Sandbox Isolation Enforced", status: "Enabled" },
    { name: "Secrets Redaction Enabled", status: "Enabled" },
    { name: "Network Egress Restricted", status: "Restricted" },
    { name: "Audit Logging Enabled", status: "Enabled" },
    { name: "MCP Gateway Controls Enforced", status: "Enabled" },
    { name: "Least Privilege Execution", status: "Enforced" },
    { name: "Human Approval Required (High Risk)", status: "Enforced" },
    { name: "Artifact Integrity Verification", status: "Active" },
    { name: "Data Residency Controls Active", status: "Active" }
  ];

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-semibold">Policy & Gate Summary</h4>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 font-bold">RELEASE ALLOWED</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
        {policies.map((p, idx) => (
          <div key={idx} className="flex items-center justify-between p-2 rounded bg-white/5 border border-white/5">
            <span className="text-slate-300 font-medium">{p.name}</span>
            <span className="text-green-400 font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
              {p.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
