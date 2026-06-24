import React from "react";
import type { SolverCandidate } from "../../lib/hochster/hochsterTypes";

interface CandidateSolutionListProps {
  candidates: SolverCandidate[];
  onSelectCandidate: (candidateId: string) => void;
  selectedCandidateId: string | null;
}

export const CandidateSolutionList: React.FC<CandidateSolutionListProps> = ({
  candidates,
  onSelectCandidate,
  selectedCandidateId
}) => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div>
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Candidate Solutions (Ranked)</h4>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 text-[9px] uppercase text-slate-400 font-bold">
              <th className="py-2">Rank</th>
              <th className="py-2">Strategy</th>
              <th className="py-2">Confidence</th>
              <th className="py-2">Tests</th>
              <th className="py-2">Risk</th>
              <th className="py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c, idx) => {
              const isSelected = c.candidate_id === selectedCandidateId;
              
              // Map risk badge
              let riskClass = "bg-green-500/10 text-green-400";
              if (c.validation.regression_risk === "medium") riskClass = "bg-yellow-500/10 text-yellow-400";
              if (["high", "critical"].includes(c.validation.regression_risk)) riskClass = "bg-red-500/10 text-red-400";

              // Map status label
              let statusLabel = "Good";
              let statusClass = "text-slate-400";
              if (idx === 0) {
                statusLabel = "Recommended";
                statusClass = "text-green-400 font-bold";
              } else if (idx === 1) {
                statusLabel = "Strong";
                statusClass = "text-blue-400 font-semibold";
              } else if (c.validation.regression_risk === "high") {
                statusLabel = "Review";
                statusClass = "text-red-400 font-medium";
              }

              return (
                <tr
                  key={c.candidate_id}
                  onClick={() => onSelectCandidate(c.candidate_id)}
                  className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition text-xs ${
                    isSelected ? "bg-blue-500/5" : ""
                  }`}
                >
                  <td className="py-2.5 font-bold text-slate-400">#{idx + 1}</td>
                  <td className="py-2.5 font-semibold text-white capitalize">{c.strategy.replace(/_/g, " ")}</td>
                  <td className="py-2.5 text-slate-300">{(c.scoring.confidence).toFixed(2)}</td>
                  <td className="py-2.5 font-mono text-slate-300">{c.validation.tests_passed}/{c.validation.tests_run}</td>
                  <td className="py-2.5">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded capitalize ${riskClass}`}>
                      {c.validation.regression_risk}
                    </span>
                  </td>
                  <td className="py-2.5 text-right font-medium text-[10px]">
                    <span className={statusClass}>{statusLabel}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
