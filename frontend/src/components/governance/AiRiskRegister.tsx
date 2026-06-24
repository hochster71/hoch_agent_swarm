import { useGovernanceRegistryStore } from "../../lib/governance/aiSystemRegistry";
import { scoreAiSystemRisk } from "../../lib/governance/aiRiskScoring";
import { AlertCircle, TrendingUp, ShieldAlert, CheckCircle } from "lucide-react";

export function AiRiskRegister() {
  const { systems } = useGovernanceRegistryStore();

  // Helper to map record to heatmap coordinates
  // Impact: Restricted=3, Confidential=2/3, Internal=2, Public=1
  // Likelihood: can_execute=3, can_recommend=2, else=1
  const getMatrixCoords = (sys: any) => {
    let impact = 1;
    if (sys.data_access.classification === "restricted") impact = 3;
    else if (sys.data_access.classification === "confidential") impact = 3;
    else if (sys.data_access.classification === "internal") impact = 2;

    let likelihood = 1;
    if (sys.autonomy.can_execute) likelihood = 3;
    else if (sys.autonomy.can_recommend) likelihood = 2;

    return { row: 3 - impact, col: likelihood - 1 }; // row: 0 is High, 2 is Low. col: 0 is Low, 2 is High.
  };

  // Build matrix grids (3x3)
  const matrix = Array(3).fill(null).map(() => Array(3).fill(null).map(() => [] as any[]));
  systems.forEach((sys) => {
    const { row, col } = getMatrixCoords(sys);
    matrix[row][col].push(sys);
  });

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Left side: Heatmap */}
      <div className="xl:col-span-1 rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-orange-500" />
            <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
              RISK HEAT MAP (Impact vs Likelihood)
            </h3>
          </div>

          <div className="grid grid-cols-4 gap-2 font-mono text-[9px] text-center">
            {/* Row Header column */}
            <div className="flex flex-col justify-around text-slate-500 text-right pr-2">
              <span className="h-10 flex items-center justify-end font-semibold">HIGH</span>
              <span className="h-10 flex items-center justify-end font-semibold">MED</span>
              <span className="h-10 flex items-center justify-end font-semibold">LOW</span>
            </div>

            {/* Heatmap Grid */}
            <div className="col-span-3 grid grid-cols-3 gap-2">
              {/* Row 1 (High Impact) */}
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[0][0].length > 0 ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[0][0].length > 0 ? `${matrix[0][0].length} sys` : "-"}
              </div>
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[0][1].length > 0 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[0][1].length > 0 ? `${matrix[0][1].length} sys` : "-"}
              </div>
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[0][2].length > 0 ? 'bg-red-500/20 text-red-400 border border-red-500/40 pulsing-red' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[0][2].length > 0 ? `${matrix[0][2].length} sys` : "-"}
              </div>

              {/* Row 2 (Medium Impact) */}
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[1][0].length > 0 ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[1][0].length > 0 ? `${matrix[1][0].length} sys` : "-"}
              </div>
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[1][1].length > 0 ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[1][1].length > 0 ? `${matrix[1][1].length} sys` : "-"}
              </div>
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[1][2].length > 0 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[1][2].length > 0 ? `${matrix[1][2].length} sys` : "-"}
              </div>

              {/* Row 3 (Low Impact) */}
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[2][0].length > 0 ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[2][0].length > 0 ? `${matrix[2][0].length} sys` : "-"}
              </div>
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[2][1].length > 0 ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[2][1].length > 0 ? `${matrix[2][1].length} sys` : "-"}
              </div>
              <div className={`h-10 rounded flex items-center justify-center font-bold text-xs transition-colors ${matrix[2][2].length > 0 ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40' : 'bg-slate-900/40 text-slate-600 border border-slate-900/60'}`}>
                {matrix[2][2].length > 0 ? `${matrix[2][2].length} sys` : "-"}
              </div>
            </div>

            {/* Likelihood Label columns */}
            <div></div>
            <div className="font-semibold text-slate-500 py-1">LOW</div>
            <div className="font-semibold text-slate-500 py-1">MED</div>
            <div className="font-semibold text-slate-500 py-1">HIGH</div>
          </div>
        </div>

        <div className="mt-4 text-[10px] font-mono text-slate-500 leading-relaxed border-t border-slate-900 pt-3">
          Grid plots systems by access level (Impact) and actions autonomy + missing controls (Likelihood). Glowing red represents critical enclaves requiring immediate control mitigation.
        </div>
      </div>

      {/* Right side: Detailed Scoring Rationale */}
      <div className="xl:col-span-2 rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            RISK ASSESSMENT SCORING & RATIONALE
          </h3>
        </div>

        <div className="space-y-3 font-mono text-xs max-h-[300px] overflow-y-auto pr-1">
          {systems.map((sys) => {
            const result = scoreAiSystemRisk(sys);
            return (
              <div
                key={sys.system_id}
                className="rounded border border-slate-900 bg-slate-950/40 p-3 hover:border-slate-800 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="font-bold text-slate-200 text-sm">{sys.name}</span>
                    <span className="ml-2 rounded bg-slate-900 px-1.5 py-0.5 text-[9px] text-slate-400">
                      ID: {sys.system_id}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 text-[10px]">Score:</span>
                    <span className={`font-bold ${result.score >= 80 ? 'text-red-500' : result.score >= 55 ? 'text-orange-500' : 'text-yellow-500'}`}>
                      {result.score}/100
                    </span>
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${sys.risk_tier === 'critical' ? 'bg-red-500/10 text-red-500 border border-red-500/30' : sys.risk_tier === 'high' ? 'bg-orange-500/10 text-orange-400 border border-orange-500/30' : sys.risk_tier === 'medium' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30' : 'bg-green-500/10 text-green-400 border border-green-500/30'}`}>
                      {sys.risk_tier}
                    </span>
                  </div>
                </div>

                {result.reasons.length > 0 ? (
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-slate-500 font-semibold">Elevating Factors:</span>
                    <ul className="list-inside list-disc pl-2 space-y-1 text-slate-400 text-[11px]">
                      {result.reasons.map((r, idx) => (
                        <li key={idx} className="flex items-center gap-1.5">
                          <AlertCircle className="h-3 w-3 text-slate-600 flex-shrink-0" />
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="text-[11px] text-green-400 flex items-center gap-1.5">
                    <CheckCircle className="h-3 w-3" />
                    <span>No negative risk triggers mapped for this capability.</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
