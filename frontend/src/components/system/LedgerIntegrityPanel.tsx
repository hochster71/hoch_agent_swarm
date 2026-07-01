import { useLedgerStore } from "@/lib/ledger/ledgerClient";
import { ShieldCheck, ShieldAlert, Cpu, Award } from "lucide-react";

export function LedgerIntegrityPanel() {
  const { verification, verifyLedger, syncing, blocks } = useLedgerStore();

  const genesisBlock = blocks.find((b) => b.index === 0);
  const latestBlock = blocks.length > 0 ? blocks[blocks.length - 1] : null;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            CRYPTOGRAPHIC CHAIN VERIFIER
          </h3>
        </div>
        <button
          onClick={() => verifyLedger()}
          disabled={syncing}
          className={`flex items-center gap-1 rounded bg-emerald-500 hover:bg-emerald-400 px-3 py-1 text-xs font-mono font-bold text-slate-950 transition-all ${
            syncing ? "opacity-55 cursor-not-allowed" : ""
          }`}
        >
          {syncing ? "VERIFYING..." : "RUN FULL AUDIT PASS"}
        </button>
      </div>

      {verification ? (
        <div className="mb-4 rounded border border-slate-900 bg-slate-950/40 p-3 font-mono text-xs">
          <div className="flex items-center gap-2 mb-2">
            {verification.is_valid ? (
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-rose-500" />
            )}
            <span className={`text-sm font-bold uppercase tracking-wider ${
              verification.is_valid ? "text-emerald-400" : "text-rose-500"
            }`}>
              {verification.is_valid ? "LEDGER CHAIN SECURE" : "CHAIN CORRUPTION DETECTED"}
            </span>
          </div>
          <p className="text-slate-400 leading-relaxed mb-2">{verification.verification_msg}</p>
          <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-500">
            <div>Verified count: {verification.block_count}</div>
            <div>Time: {new Date(verification.verified_at).toLocaleTimeString()}</div>
          </div>
        </div>
      ) : (
        <div className="mb-4 rounded border border-slate-900 bg-slate-950/40 p-3 text-center">
          <p className="font-mono text-xs text-slate-500">
            No validation scan executed in this session. Run pass to verify ledger integrity.
          </p>
        </div>
      )}

      {/* Block stats */}
      <div className="space-y-2.5 font-mono text-[11px]">
        <div className="rounded border border-slate-900 bg-slate-950/20 p-2.5">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <Award className="h-3.5 w-3.5 text-cyan-400" />
            <span className="font-bold">GENESIS SEED BLOCK</span>
          </div>
          {genesisBlock ? (
            <div className="space-y-0.5 text-slate-500">
              <div>Index: 0</div>
              <div>Hash: <span className="text-slate-400 select-all">{genesisBlock.hash.substring(0, 16)}...</span></div>
            </div>
          ) : (
            <span className="text-slate-600 italic">No genesis block synced.</span>
          )}
        </div>

        <div className="rounded border border-slate-900 bg-slate-950/20 p-2.5">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <Cpu className="h-3.5 w-3.5 text-cyan-400" />
            <span className="font-bold">LATEST BLOCK SEAL</span>
          </div>
          {latestBlock ? (
            <div className="space-y-0.5 text-slate-500">
              <div>Index: {latestBlock.index}</div>
              <div>Hash: <span className="text-slate-400 select-all">{latestBlock.hash.substring(0, 16)}...</span></div>
            </div>
          ) : (
            <span className="text-slate-600 italic">No blocks synced.</span>
          )}
        </div>
      </div>
    </div>
  );
}
