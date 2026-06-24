import { AlertTriangle, ShieldCheck, Flame } from "lucide-react";
import type { CapabilityRecord } from "../../lib/capabilities/capabilityTypes";
import { scoreCapabilityRisk } from "../../lib/capabilities/capabilityRisk";

type Props = {
  capability: CapabilityRecord;
};

export function CapabilityRiskPanel({ capability }: Props) {
  const { risk, score, reasons } = scoreCapabilityRisk(capability);

  const getRiskColors = () => {
    switch (risk) {
      case "critical":
        return { bg: "bg-red-950/30 border-red-500/40 text-red-400", bar: "bg-red-500" };
      case "high":
        return { bg: "bg-orange-950/30 border-orange-500/40 text-orange-400", bar: "bg-orange-500" };
      case "medium":
        return { bg: "bg-yellow-950/30 border-yellow-500/40 text-yellow-400", bar: "bg-yellow-500" };
      default:
        return { bg: "bg-green-950/30 border-green-500/40 text-green-400", bar: "bg-green-500" };
    }
  };

  const colors = getRiskColors();

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[11px]">
      <h3 className="text-xs font-bold tracking-wider text-slate-400 mb-3 uppercase flex items-center gap-2">
        <Flame className="h-4 w-4 text-orange-400" />
        Capability Risk Profile
      </h3>

      <div className={`flex items-center justify-between p-3 rounded border mb-4 ${colors.bg}`}>
        <div className="flex items-center gap-2">
          {risk === "low" ? (
            <ShieldCheck className="h-5 w-5 text-green-400" />
          ) : (
            <AlertTriangle className="h-5 w-5 animate-pulse" />
          )}
          <div>
            <div className="text-xs font-bold uppercase">{risk} Risk Tier</div>
            <div className="text-[9px] opacity-75 mt-0.5">Computed score out of 120 max limit</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold">{score} / 120</div>
        </div>
      </div>

      <div className="w-full bg-slate-900 rounded-full h-1.5 mb-4">
        <div className={`h-1.5 rounded-full ${colors.bar}`} style={{ width: `${Math.min(100, (score / 120) * 100)}%` }} />
      </div>

      <div>
        <div className="text-slate-500 font-bold mb-2 uppercase text-[10px]">Audit Findings ({reasons.length})</div>
        {reasons.length === 0 ? (
          <div className="text-slate-600 italic">No significant threat vectors identified. Low autonomy profile.</div>
        ) : (
          <ul className="space-y-1.5">
            {reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-slate-400">
                <span className="text-slate-600">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
