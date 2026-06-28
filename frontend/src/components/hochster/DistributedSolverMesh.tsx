import React from "react";
import { Play, CheckCircle2, Shield, Eye, HelpCircle } from "lucide-react";
import type { SolverCandidate } from "../../lib/hochster/hochsterTypes";

interface DistributedSolverMeshProps {
  candidates: SolverCandidate[];
  onSelectCandidate: (candidateId: string) => void;
  selectedCandidateId: string | null;
}

export const DistributedSolverMesh: React.FC<DistributedSolverMeshProps> = ({
  candidates,
  onSelectCandidate,
  selectedCandidateId
}) => {
  const steps = [
    { label: "Request Intake", desc: "Context & Evidence" },
    { label: "Mesh Orchestration", desc: "Parallel Strategies" },
    { label: "Candidate Generation", desc: "Multiple Solutions" },
    { label: "Validation Engine", desc: "Tests, Security, Risk" },
    { label: "Ranking & Selection", desc: "Best Solution" },
    { label: "Deliver / Automate", desc: "Callback / PR" }
  ];

  return (
    <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/2 space-y-5 text-left">
      <div>
        <h3 className="text-md font-bold text-white tracking-wide uppercase">Distributed Solver Mesh</h3>
        <p className="text-xs text-slate-400">Solve in parallel. Rank solutions. Remember patterns. Deliver with approval.</p>
      </div>

      {/* Chevron pipeline flow */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        {steps.map((s, idx) => (
          <div key={idx} className="relative flex flex-col items-center justify-center p-3 rounded-xl bg-white/5 border border-white/5 text-center">
            <div className="w-6 h-6 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 flex items-center justify-center text-xs font-bold mb-1">
              {idx + 1}
            </div>
            <span className="text-[10px] font-semibold text-white truncate w-full">{s.label}</span>
            <span className="text-[8px] text-slate-400 truncate w-full">{s.desc}</span>
            {idx < steps.length - 1 && (
              <div className="hidden md:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-slate-500 font-bold">
                →
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Active Solver Mesh Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300 uppercase">Active Solver Mesh</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
            Status: Solving (92%)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400 font-bold">
                <th className="py-2">Strategy</th>
                <th className="py-2">Solver Instance</th>
                <th className="py-2">Status</th>
                <th className="py-2">Tests</th>
                <th className="py-2">Confidence</th>
                <th className="py-2">Score</th>
                <th className="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => {
                const isSelected = c.candidate_id === selectedCandidateId;
                return (
                  <tr
                    key={c.candidate_id}
                    className={`border-b border-white/5 hover:bg-white/5 transition text-xs ${
                      isSelected ? "bg-blue-500/5 border-blue-500/30" : ""
                    }`}
                  >
                    <td className="py-2.5 font-semibold text-white capitalize">{c.strategy.replace(/_/g, " ")}</td>
                    <td className="py-2.5 font-mono text-slate-300 text-[10px]">solver-{c.strategy.slice(0, 3)}-0{Math.floor(Math.random() * 3) + 1}</td>
                    <td className="py-2.5">
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 font-medium">
                        Solved
                      </span>
                    </td>
                    <td className="py-2.5 font-mono text-slate-300">{c.validation.tests_passed}/{c.validation.tests_run}</td>
                    <td className="py-2.5 font-semibold text-slate-200">{(c.scoring.confidence).toFixed(2)}</td>
                    <td className="py-2.5 font-bold text-blue-400">{c.scoring.total_score}</td>
                    <td className="py-2.5 text-right">
                      <button
                        onClick={() => onSelectCandidate(c.candidate_id)}
                        className={`text-[10px] px-2.5 py-1 rounded-md font-semibold transition ${
                          isSelected
                            ? "bg-blue-500 text-white"
                            : "bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white"
                        }`}
                      >
                        {isSelected ? "Active" : "View"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
