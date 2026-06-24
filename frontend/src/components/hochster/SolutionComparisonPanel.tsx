import React from "react";
import type { SolverCandidate } from "../../lib/hochster/hochsterTypes";

interface SolutionComparisonPanelProps {
  candidateA: SolverCandidate;
  candidateB: SolverCandidate;
}

export const SolutionComparisonPanel: React.FC<SolutionComparisonPanelProps> = ({
  candidateA,
  candidateB
}) => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 space-y-4 text-left">
      <div>
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Solution Comparison (Top 2)</h4>
        <span className="text-[10px] text-slate-400">Comparing {candidateA.strategy} and {candidateB.strategy}</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs border-t border-white/5 pt-3">
        <div className="text-slate-400">Metric</div>
        <div className="font-semibold text-white capitalize">{candidateA.strategy.replace(/_/g, " ")}</div>
        <div className="font-semibold text-white capitalize">{candidateB.strategy.replace(/_/g, " ")}</div>

        <div className="border-t border-white/5 py-1 text-slate-400">Confidence</div>
        <div className="border-t border-white/5 py-1 text-green-400 font-semibold">{(candidateA.scoring.confidence).toFixed(2)}</div>
        <div className="border-t border-white/5 py-1 text-slate-300">{(candidateB.scoring.confidence).toFixed(2)}</div>

        <div className="border-t border-white/5 py-1 text-slate-400">Total Score</div>
        <div className="border-t border-white/5 py-1 text-green-400 font-bold">{candidateA.scoring.total_score}</div>
        <div className="border-t border-white/5 py-1 text-slate-300 font-bold">{candidateB.scoring.total_score}</div>

        <div className="border-t border-white/5 py-1 text-slate-400">Simplicity</div>
        <div className="border-t border-white/5 py-1 text-slate-200">{candidateA.scoring.simplicity_score}</div>
        <div className="border-t border-white/5 py-1 text-slate-200">{candidateB.scoring.simplicity_score}</div>

        <div className="border-t border-white/5 py-1 text-slate-400">Maintainability</div>
        <div className="border-t border-white/5 py-1 text-slate-200">{candidateA.scoring.maintainability_score}</div>
        <div className="border-t border-white/5 py-1 text-slate-200">{candidateB.scoring.maintainability_score}</div>

        <div className="border-t border-white/5 py-1 text-slate-400">Regression Risk</div>
        <div className="border-t border-white/5 py-1 text-green-400 uppercase">{candidateA.validation.regression_risk}</div>
        <div className="border-t border-white/5 py-1 text-yellow-400 uppercase">{candidateB.validation.regression_risk}</div>
      </div>

      <div className="bg-white/5 rounded-lg p-2.5 border border-white/5 text-[10px] space-y-1">
        <span className="font-semibold text-slate-300 block">Diff Summary</span>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-slate-400">Files Changed: </span>
            <span className="text-white font-mono">{candidateA.patch?.files_changed.length || 0}</span>
          </div>
          <div>
            <span className="text-slate-400">Files Changed: </span>
            <span className="text-white font-mono">{candidateB.patch?.files_changed.length || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
