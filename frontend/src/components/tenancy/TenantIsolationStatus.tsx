import type { TenantRecord } from "../../lib/tenancy/tenantTypes";
import { evaluateTenantIsolation } from "../../lib/tenancy/isolationChecks";
import { ShieldCheck, ShieldAlert, Key } from "lucide-react";

type Props = {
  tenant: TenantRecord;
};

export function TenantIsolationStatus({ tenant }: Props) {
  const check = evaluateTenantIsolation(tenant);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px] space-y-4">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 border-b border-slate-900 pb-2 uppercase flex items-center gap-1.5">
        <Key className="h-4 w-4 text-cyan-400" />
        Cryptographic Isolation Verification
      </h3>

      <div className={`p-3 rounded border flex items-center justify-between ${
        check.passed
          ? "bg-green-950/20 border-green-800/40 text-green-400"
          : "bg-red-950/20 border-red-800/40 text-red-400"
      }`}>
        <div className="flex items-center gap-2">
          {check.passed ? (
            <ShieldCheck className="h-5 w-5 text-green-400" />
          ) : (
            <ShieldAlert className="h-5 w-5 text-red-400 animate-pulse" />
          )}
          <div>
            <div className="text-xs font-bold uppercase">{check.passed ? "Isolation Verified" : "Risk Detected"}</div>
            <div className="text-[9px] opacity-75 mt-0.5">Namespace boundary and data partition key scan</div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-[9px] text-slate-500 uppercase font-bold">Boundary Check Findings</div>
        {check.findings.length === 0 ? (
          <div className="text-slate-600 italic">No isolation leakage or boundary crossing findings detected. Namespace is secure.</div>
        ) : (
          <ul className="space-y-1.5">
            {check.findings.map((f, i) => (
              <li key={i} className="p-2 rounded bg-red-950/10 border border-red-900/30 text-red-400/90 flex gap-2">
                <span>•</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
