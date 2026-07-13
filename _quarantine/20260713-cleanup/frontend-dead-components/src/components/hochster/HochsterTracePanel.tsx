import React from "react";
import { List } from "lucide-react";

interface Props {
  traces: { timestamp: string; event: string; summary: string }[];
  correlationId: string;
}

export const HochsterTracePanel: React.FC<Props> = ({ traces, correlationId }) => {
  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold flex items-center gap-2">
            <List className="w-5 h-5 text-blue-400" /> Audit &amp; Trace
          </h3>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">Correlation ID: {correlationId}</p>
        </div>
        <span className="text-[10px] text-indigo-400 hover:underline cursor-pointer font-semibold">View Full Trace</span>
      </div>

      <div className="space-y-3.5 font-mono text-xs max-h-[350px] overflow-y-auto pr-2">
        {traces.map((trace, idx) => (
          <div key={idx} className="flex gap-4 items-start border-l border-white/10 pl-4 relative pb-1">
            <span className="absolute -left-1.5 top-1 w-3 h-3 bg-blue-500 rounded-full border border-slate-900"></span>
            <div className="text-slate-500 text-[10px] font-bold mt-0.5">{trace.timestamp}</div>
            <div className="flex-1">
              <div className="font-bold text-blue-400 text-[11px] uppercase tracking-wider">{trace.event}</div>
              <div className="text-slate-300 mt-1 text-[11px] leading-relaxed">{trace.summary}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
