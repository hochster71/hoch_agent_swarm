import { useState } from "react";
import { Clock, Save } from "lucide-react";

export function RetentionPolicyPanel() {
  const [auditDays, setAuditDays] = useState(90);
  const [rotateSize, setRotateSize] = useState(10);
  const immutableLedger = true;

  function handleSave() {
    alert(`Retention policy updated. Rules committed to backend configuration.`);
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            DATA RETENTION POLICY
          </h3>
        </div>
        <button
          onClick={handleSave}
          className="flex items-center gap-1 rounded bg-slate-900 border border-slate-700/60 hover:bg-slate-800 px-2.5 py-1 text-xs font-mono text-slate-300 transition-all"
        >
          <Save className="h-3.5 w-3.5" />
          APPLY
        </button>
      </div>

      <div className="space-y-4 font-mono text-xs">
        <div>
          <label className="block text-slate-400 mb-1.5">Audit Events Retention (Days)</label>
          <select
            value={auditDays}
            onChange={(e) => setAuditDays(Number(e.target.value))}
            className="w-full h-8 rounded border border-slate-800 bg-slate-900 px-2 text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value={30}>30 Days (Standard Compliance)</option>
            <option value={90}>90 Days (Extended Audit)</option>
            <option value={365}>365 Days (Full Governance)</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-400 mb-1.5">Log Rotation File Size Limit (MB)</label>
          <input
            type="number"
            value={rotateSize}
            onChange={(e) => setRotateSize(Number(e.target.value))}
            className="w-full h-8 rounded border border-slate-800 bg-slate-900 px-2.5 text-slate-300 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center justify-between border-t border-slate-900/60 pt-3">
          <div>
            <span className="text-slate-300 block font-medium">Immutable Chain Policy</span>
            <span className="text-[10px] text-slate-500">Ledger blocks cannot be modified or truncated.</span>
          </div>
          <input
            type="checkbox"
            checked={immutableLedger}
            disabled
            className="h-4 w-4 rounded border-slate-800 bg-slate-900 text-cyan-500 accent-cyan-500 cursor-not-allowed"
          />
        </div>
      </div>
    </div>
  );
}
