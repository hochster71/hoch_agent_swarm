import React, { useState, useEffect } from "react";
import { Shield, CheckCircle2, AlertTriangle, Download, RefreshCw } from "lucide-react";

interface LockReport {
  report_id: string;
  version: string;
  codename: string;
  generated_at: string;
  git_commit_sha: string;
  gates: {
    realtime_data: string;
    stale_detection: string;
    audit_trace_integrity: string;
    hochster_debug_check: string;
    tool_policy_enforcement: string;
    otel_instrumentation: string;
  };
  lock_decision: "PASS" | "BLOCK";
}

export const BaselineLockPanel: React.FC = () => {
  const [report, setReport] = useState<LockReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [showJson, setShowJson] = useState(false);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/hochster/baseline/lock");
      if (res.ok) {
        const data = await res.json();
        setReport(data.report);
      }
    } catch (e) {
      console.error("Failed to fetch baseline lock report", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  const downloadReport = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `baseline_lock_report_${report.version}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!report) {
    return (
      <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 flex items-center justify-center min-h-[150px]">
        <div className="flex items-center gap-2 text-slate-400 text-xs">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Generating baseline report...</span>
        </div>
      </div>
    );
  }

  const gateKeys = Object.keys(report.gates) as Array<keyof typeof report.gates>;

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-blue-400" />
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Baseline Lock Dashboard</h4>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchReport}
            disabled={loading}
            className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition"
            title="Refresh Gates"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 font-semibold font-mono">
            {report.version}
          </span>
        </div>
      </div>

      <div className="p-3 bg-white/5 rounded-lg border border-white/5 space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400">Lock Codename:</span>
          <span className="font-semibold text-white font-mono">{report.codename}</span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400">Git Commit:</span>
          <span className="font-mono text-slate-300 text-[10px]">{report.git_commit_sha.slice(0, 12)}</span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400">Decision Lock Status:</span>
          <span
            className={`font-bold px-2 py-0.5 rounded text-[10px] ${
              report.lock_decision === "PASS"
                ? "bg-green-500/10 text-green-400"
                : "bg-red-500/10 text-red-400 animate-pulse"
            }`}
          >
            {report.lock_decision === "PASS" ? "LOCK APPROVED (PASS)" : "LOCK BLOCKED (BLOCK)"}
          </span>
        </div>
      </div>

      {/* Gates Checklist */}
      <div className="space-y-2">
        <span className="text-[10px] font-bold uppercase text-slate-400 block tracking-wider">Release Gates Checklist</span>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          {gateKeys.map((k) => {
            const pass = report.gates[k] === "PASS";
            const name = k.replace(/_/g, " ");
            return (
              <div
                key={k}
                className="flex items-center justify-between p-2 rounded bg-white/5 border border-white/5"
              >
                <span className="capitalize text-slate-300 text-[11px] font-medium">{name}</span>
                <span className="flex items-center gap-1">
                  {pass ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                      <span className="text-green-400 text-[10px] font-bold">PASS</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                      <span className="text-red-400 text-[10px] font-bold">FAIL</span>
                    </>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex gap-2 justify-end pt-1">
        <button
          onClick={() => setShowJson(!showJson)}
          className="text-[10px] px-3 py-1.5 rounded-lg font-semibold bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 hover:text-white transition"
        >
          {showJson ? "Hide Evidence Pack" : "View Evidence Pack"}
        </button>
        <button
          onClick={downloadReport}
          className="text-[10px] px-3 py-1.5 rounded-lg font-semibold bg-blue-500 text-white hover:bg-blue-600 transition flex items-center gap-1.5"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Lock Evidence</span>
        </button>
      </div>

      {showJson && (
        <pre className="p-3 bg-black/60 rounded-lg text-[10px] font-mono text-blue-300 overflow-x-auto max-h-[200px] border border-white/5">
          {JSON.stringify(report, null, 2)}
        </pre>
      )}
    </div>
  );
};
