import React, { useState } from "react";
import { CheckCircle2, XCircle, FileText, AlertTriangle, ShieldCheck, Download } from "lucide-react";
import { HochsterSolution } from "../../lib/hochster/hochsterTypes";

interface Props {
  solution: HochsterSolution | null;
}

export const HochsterSolutionViewer: React.FC<Props> = ({ solution }) => {
  const [activeSubTab, setActiveSubTab] = useState<"summary" | "patch" | "explanation" | "tests" | "logs" | "security" | "metrics">("summary");

  if (!solution) {
    return (
      <div className="glass-panel p-6 rounded-xl border border-white/10 bg-white/2 text-center text-slate-400 space-y-2">
        <AlertTriangle className="w-8 h-8 text-yellow-400 mx-auto" />
        <h4 className="font-bold text-white text-sm">No Active Solution Loaded</h4>
        <p className="text-xs">Submit a solve request to generate and inspect candidate patches.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <div className="flex justify-between items-start border-b border-white/5 pb-3">
        <div>
          <h3 className="text-lg font-bold text-white">Solution Viewer — <span className="font-mono text-slate-400">{solution.request_id}</span></h3>
        </div>
        <span
          className="text-xs px-2.5 py-1 bg-green-500/20 text-green-400 border border-green-500/20 rounded-full font-bold uppercase"
        >
          Solved (100%)
        </span>
      </div>

      {/* Tabs matching the prototype image */}
      <div className="flex border-b border-white/5 gap-2 overflow-x-auto">
        {["summary", "patch", "explanation", "tests", "logs", "security", "metrics"].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveSubTab(tab as any)}
            className={`px-3 py-1.5 text-xs font-semibold border-b-2 uppercase tracking-wider transition whitespace-nowrap ${
              activeSubTab === tab ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white"
            }`}
          >
            {tab === "patch" ? "Patch / Diff" : tab === "logs" ? "Logs & Evidence" : tab}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="min-h-[220px]">
        {activeSubTab === "summary" && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-white/2 border border-white/5 p-3 rounded-lg">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Problem Type</span>
                <span className="font-bold text-white">Code Bug</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Type</span>
                <span className="font-bold text-white">Runtime Error</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Language / Framework</span>
                <span className="font-bold text-white">C# / .NET 8.0</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Severity</span>
                <span className="font-bold text-red-400">High</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] text-slate-400 uppercase font-bold block">Root Cause</span>
              <p className="text-sm font-semibold text-slate-200">{solution.root_cause}</p>
            </div>

            <div className="grid grid-cols-4 gap-4 border-t border-white/5 pt-3">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Confidence</span>
                <span className="font-bold text-emerald-400 text-sm">0.94</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Instances Used</span>
                <span className="font-bold text-white text-sm">3</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Total Time</span>
                <span className="font-bold text-white text-sm">3.42s</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-bold block">Tokens Used</span>
                <span className="font-bold text-white text-sm">28.4M</span>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === "patch" && solution.patch && (
          <div className="space-y-4">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-400 uppercase">Patch (Unified Diff)</span>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="show_white" className="rounded border-white/20 text-blue-500 cursor-pointer" />
                <label htmlFor="show_white" className="text-slate-300 font-semibold cursor-pointer">Show Whitespace</label>
              </div>
            </div>
            
            <div className="bg-slate-950 p-4 rounded-lg font-mono text-xs overflow-x-auto text-slate-300 max-h-[300px] border border-white/5">
              {solution.patch.diff.split("\n").map((line, idx) => {
                let color = "text-slate-300";
                if (line.startsWith("+")) color = "text-green-400 bg-green-500/5";
                if (line.startsWith("-")) color = "text-red-400 bg-red-500/5";
                if (line.startsWith("@@")) color = "text-cyan-400";
                if (line.startsWith("diff")) color = "text-slate-400 font-bold";
                return (
                  <div key={idx} className={`${color} px-1.5 rounded`}>
                    {line}
                  </div>
                );
              })}
            </div>

            {/* Patch Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs mt-2">
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Files Changed</span>
                <span className="font-mono text-white mt-1 block truncate">src/services/UserService.cs</span>
              </div>
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Risk Assessment</span>
                <span className="font-bold text-green-400 mt-1 block uppercase">Low Risk</span>
              </div>
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Potential Impact</span>
                <span className="font-semibold text-slate-300 mt-1 block">No breaking changes. Adds null guard checks.</span>
              </div>
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Rollback Plan</span>
                <span className="font-semibold text-slate-300 mt-1 block">Revert this patch.</span>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === "explanation" && (
          <div className="text-xs text-slate-300 space-y-3 leading-relaxed">
            <h4 className="font-bold text-white">Triage Diagnosis</h4>
            <p>{solution.explanation}</p>
            <div className="bg-white/5 border border-white/5 p-3 rounded-lg space-y-1 mt-2">
              <span className="font-bold uppercase text-[9px] text-slate-400">Suggested Commits</span>
              <p className="font-mono text-slate-200">feat(user-service): add null check and not found exception</p>
            </div>
          </div>
        )}

        {activeSubTab === "tests" && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg text-center">
                <span className="text-xs text-slate-400 uppercase font-bold">Passed</span>
                <div className="text-xl font-bold text-green-400 mt-1">12</div>
              </div>
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg text-center">
                <span className="text-xs text-slate-400 uppercase font-bold">Failed</span>
                <div className="text-xl font-bold text-red-400 mt-1">0</div>
              </div>
              <div className="bg-white/2 border border-white/5 p-3 rounded-lg text-center">
                <span className="text-xs text-slate-400 uppercase font-bold">Coverage</span>
                <div className="text-xl font-bold text-white mt-1">98%</div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <span className="font-bold text-slate-400 uppercase">Executed Tools</span>
                <div className="flex flex-wrap gap-1.5">
                  {["filesystem", "shell", "dotnet test", "code analyzer", "search", "logger"].map(tool => (
                    <span key={tool} className="bg-white/5 border border-white/5 px-2 py-0.5 rounded text-[10px] text-slate-300 font-mono">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="font-bold text-slate-400 uppercase">Evidence Links</span>
                <div className="space-y-1">
                  {["trace_9f7a2c0e", "artifact_patch_001", "logs_execution.txt"].map(ev => (
                    <div key={ev} className="text-blue-400 font-mono hover:underline cursor-pointer flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-slate-400" />
                      {ev}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === "logs" && (
          <div className="bg-slate-950 p-4 rounded-lg font-mono text-[10px] text-slate-300 max-h-[300px] overflow-y-auto border border-white/5">
            <div>2026-06-24 12:12:44 - [Docker Worker] Initialized sandbox env.</div>
            <div>2026-06-24 12:12:45 - [Docker Worker] Mounting /app/src/services/UserService.cs read-only.</div>
            <div>2026-06-24 12:12:46 - [Observability] Fetching container logs from container://api/logs/latest.</div>
            <div>2026-06-24 12:12:49 - [Debugger] Found NullReferenceException at line 12 inside UserService.cs.</div>
            <div>2026-06-24 12:12:52 - [Debugger] Generated code patch candidate.</div>
            <div>2026-06-24 12:12:53 - [TestRunner] Spawning sandbox container to run 'dotnet test'.</div>
            <div>2026-06-24 12:12:54 - [TestRunner] 12 test assertions succeeded. 0 failures.</div>
          </div>
        )}

        {activeSubTab === "security" && (
          <div className="space-y-4 text-xs">
            <div className="flex justify-between items-center bg-white/2 border border-white/5 p-3 rounded-lg">
              <span>Secrets exposure check:</span>
              <span className="font-bold uppercase text-green-400">CLEAN - SECRETS REDACTED</span>
            </div>

            <div className="flex justify-between items-center bg-white/2 border border-white/5 p-3 rounded-lg">
              <span>Dependency vulnerability risk check:</span>
              <span className="font-bold uppercase text-green-400">No vulnerabilities found</span>
            </div>

            <div className="flex justify-between items-center bg-white/2 border border-white/5 p-3 rounded-lg">
              <span>Policy constraints evaluation:</span>
              <span className="font-bold uppercase text-emerald-400">PASSED - Sandbox Compliant</span>
            </div>
          </div>
        )}

        {activeSubTab === "metrics" && (
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-bold block">CPU Load</span>
              <span className="font-bold text-white mt-1 block">18% avg</span>
            </div>
            <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-bold block">Memory footprint</span>
              <span className="font-bold text-white mt-1 block">1.2 GB max</span>
            </div>
            <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-bold block">Network egress</span>
              <span className="font-bold text-red-400 mt-1 block">0 bytes (Blocked)</span>
            </div>
            <div className="bg-white/2 border border-white/5 p-3 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-bold block">I/O read rate</span>
              <span className="font-bold text-white mt-1 block">12.5 MB/s</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
