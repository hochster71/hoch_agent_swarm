import React from "react";

interface SloItem {
  slo_id: string;
  name: string;
  target: number;
  current: number;
  status: string;
}

interface HochsterSlaDashboardProps {
  slos: SloItem[];
}

export const HochsterSlaDashboard: React.FC<HochsterSlaDashboardProps> = ({ slos }) => {
  const getDisplayValue = (s: SloItem) => {
    if (s.slo_id === "p95_response_time" || s.slo_id === "queue_latency_p95") {
      return `${s.current.toFixed(2)}s`;
    }
    if (s.slo_id === "error_rate") {
      return `${(s.current * 100).toFixed(2)}%`;
    }
    return `${(s.current * 100).toFixed(1)}%`;
  };

  const getDisplayTarget = (s: SloItem) => {
    if (s.slo_id === "p95_response_time" || s.slo_id === "queue_latency_p95") {
      return `${s.target}s`;
    }
    if (s.slo_id === "error_rate") {
      return `<${s.target * 100}%`;
    }
    return `${s.target * 100}%`;
  };

  const getChangeValue = (s: SloItem) => {
    if (s.slo_id === "solve_success_rate") return "+6.2%";
    if (s.slo_id === "callback_delivery_rate") return "+0.8%";
    if (s.slo_id === "p95_response_time") return "-0.41s";
    if (s.slo_id === "queue_latency_p95") return "+0.22s";
    return "-0.18%";
  };

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">SLO / SLA Dashboard (30d)</h4>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        {slos.map((s) => (
          <div key={s.slo_id} className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-1">
            <span className="text-[9px] text-slate-400 font-bold block uppercase truncate w-full">{s.name}</span>
            <div className="flex items-baseline gap-1">
              <span className="text-sm font-bold text-white">{getDisplayValue(s)}</span>
              <span className="text-[9px] text-green-400 font-semibold">{getChangeValue(s)}</span>
            </div>
            <span className="text-[8px] text-slate-400 block">Target: {getDisplayTarget(s)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
