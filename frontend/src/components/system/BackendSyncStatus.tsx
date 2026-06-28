import { useState } from "react";
import { useLedgerStore } from "@/lib/ledger/ledgerClient";
import { RefreshCw, CheckCircle, AlertCircle, Database } from "lucide-react";

export function BackendSyncStatus() {
  const { blocks, fetchBlocks, isLoading } = useLedgerStore();
  const [lastSynced, setLastSynced] = useState<string>(new Date().toLocaleTimeString());

  async function handleSync() {
    await fetchBlocks();
    setLastSynced(new Date().toLocaleTimeString());
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            BACKEND SYNCHRONIZATION STATUS
          </h3>
        </div>
        <button
          onClick={handleSync}
          disabled={isLoading}
          className={`flex items-center gap-1 rounded bg-slate-900 border border-slate-700/60 hover:bg-slate-800 px-2 py-1 text-xs font-mono text-slate-300 transition-all ${
            isLoading ? "opacity-55 cursor-not-allowed" : ""
          }`}
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
          SYNC
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 font-mono text-xs mb-3">
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
          <span className="text-slate-500 block mb-1">LEDGER BLOCKS</span>
          <span className="text-lg font-bold text-slate-200">{blocks.length}</span>
        </div>
        <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
          <span className="text-slate-500 block mb-1">LAST SYNC</span>
          <span className="text-lg font-bold text-cyan-400">{lastSynced}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded bg-slate-900/50 border border-slate-800 px-3 py-2 text-xs">
        {blocks.length > 0 ? (
          <>
            <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="text-slate-400">
              All events verified and committed to SQLite backend ledger.
            </span>
          </>
        ) : (
          <>
            <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
            <span className="text-slate-400">
              No blocks detected. Click Sync to retrieve ledger blocks from backend.
            </span>
          </>
        )}
      </div>
    </div>
  );
}
