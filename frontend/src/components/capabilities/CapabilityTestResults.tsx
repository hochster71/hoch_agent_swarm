import { ClipboardList, Play, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { CapabilityRecord } from "../../lib/capabilities/capabilityTypes";
import { useCapabilityRegistryStore } from "../../lib/capabilities/capabilityRegistry";

type Props = {
  capability: CapabilityRecord;
};

export function CapabilityTestResults({ capability }: Props) {
  const { testResults, runTests } = useCapabilityRegistryStore();

  const record = testResults[capability.capability_id];
  const running = record?.running;
  const results = record?.results || [];

  const handleRun = () => {
    runTests(capability.capability_id);
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px]">
      <div className="flex items-center justify-between mb-3 border-b border-slate-900 pb-2">
        <h3 className="text-xs font-bold tracking-wider text-slate-400 uppercase flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-cyan-400" />
          Capability Test Suite
        </h3>
        <button
          onClick={handleRun}
          disabled={running}
          className={`flex items-center gap-1.5 px-3 py-1 rounded text-[10px] font-bold border transition-all ${
            running
              ? "bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed"
              : "bg-cyan-950/20 border-cyan-800/40 text-cyan-400 hover:bg-cyan-950/40"
          }`}
        >
          {running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5 fill-cyan-400 text-cyan-400" />
          )}
          {running ? "Running Checks..." : "Run Test Suite"}
        </button>
      </div>

      {running && (
        <div className="flex flex-col items-center justify-center py-6 text-slate-500 gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-cyan-500" />
          <div className="text-[10px] animate-pulse">Running cluster sandbox verification, permission checking, and static analysis scans...</div>
        </div>
      )}

      {!running && results.length === 0 && (
        <div className="text-slate-600 italic py-3 text-center">
          No test executions logged for this version lifecycle. Run suite before activation.
        </div>
      )}

      {!running && results.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[9px] text-slate-500 font-bold uppercase mb-1">
            <span>Scan Assertion Name</span>
            <span>Outcome</span>
          </div>
          {results.map((r, i) => (
            <div key={i} className="flex items-start justify-between p-2 rounded bg-slate-900/40 border border-slate-800/40">
              <div className="flex gap-2">
                {r.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                )}
                <div>
                  <div className={`font-bold ${r.passed ? "text-slate-200" : "text-red-400"}`}>{r.test_name}</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">{r.message}</div>
                </div>
              </div>
              <div className="text-right text-[9px] text-slate-600 font-mono">
                {r.duration_ms}ms
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
