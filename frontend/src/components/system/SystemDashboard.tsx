import { BackendSyncStatus } from "./BackendSyncStatus";
import { LedgerIntegrityPanel } from "./LedgerIntegrityPanel";
import { ApiHealthPanel } from "./ApiHealthPanel";
import { RetentionPolicyPanel } from "./RetentionPolicyPanel";
import { Database } from "lucide-react";

export function SystemDashboard() {
  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
            <Database className="h-5 w-5 text-cyan-400" />
            IMMUTABLE LEDGER & COMPLIANCE SYSTEM
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-1">
            SQLite database synchronization, SHA-256 chain validation, and API latency audit scorecards.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <BackendSyncStatus />
          <LedgerIntegrityPanel />
        </div>
        <div className="space-y-6">
          <ApiHealthPanel />
          <RetentionPolicyPanel />
        </div>
      </div>
    </div>
  );
}
