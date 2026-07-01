import React from "react";
import { ShieldCheck, EyeOff, Lock, AlertOctagon, HelpCircle, CheckCircle2 } from "lucide-react";

export const HochsterSecurityPanel: React.FC = () => {
  const policies = [
    { name: "Sandbox Isolation", desc: "Per-request isolated container instances.", icon: Lock, status: "Active" },
    { name: "Tool Allowlist", desc: "Strict tool policy enforcement.", icon: ShieldCheck, status: "Enforced" },
    { name: "Network Egress", desc: "Restricted outbound proxy whitelist.", icon: AlertOctagon, status: "Restricted" },
    { name: "Secret Protection", desc: "Redacted credentials in logs and output traces.", icon: EyeOff, status: "Active" },
    { name: "Approval Required", desc: "High-risk actions require manual confirmation.", icon: CheckCircle2, status: "Required" },
    { name: "Audit Integrity", desc: "All actions registered in ledger ledger database.", icon: ShieldCheck, status: "Active" }
  ];

  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <h3 className="text-lg font-bold flex items-center gap-2">
        <ShieldCheck className="w-5 h-5 text-emerald-400" /> Security &amp; Isolation
      </h3>

      <div className="space-y-3">
        {policies.map(p => (
          <div key={p.name} className="p-3 bg-white/5 rounded-lg border border-white/5 flex justify-between items-start gap-4 hover:border-white/10 transition">
            <div className="flex gap-2.5">
              <p.icon className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-bold text-xs text-white">{p.name}</div>
                <p className="text-slate-400 text-[10px] mt-0.5">{p.desc}</p>
              </div>
            </div>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold uppercase">
              {p.status}
            </span>
          </div>
        ))}
      </div>
      
      <p className="text-[10px] text-slate-500 text-center">
        HOCHSTER is secured, isolated, and auditable by design.
      </p>
    </div>
  );
};
