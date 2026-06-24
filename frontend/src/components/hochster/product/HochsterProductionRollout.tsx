import React from "react";
import { CheckCircle2, Shield, Settings, Play } from "lucide-react";

export const HochsterProductionRollout: React.FC = () => {
  const rings = [
    { name: "Internal Dev", progress: 100, count: "5/5" },
    { name: "Platform Team", progress: 100, count: "12/12" },
    { name: "Trusted Internal Swarms", progress: 70, count: "7/10" },
    { name: "Pilot Tenants", progress: 20, count: "9/45" },
    { name: "Enterprise Tenants", progress: 0, count: "0/15" }
  ];

  return (
    <div className="glass-panel p-5 rounded-2xl border border-white/10 bg-white/2 space-y-5 text-left">
      <div>
        <h3 className="text-md font-bold text-white tracking-wide uppercase">Production Rollout rings</h3>
        <p className="text-xs text-slate-400">Operate at scale. Meet SLAs. Package, monetize, and support.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Rollout Rings progress */}
        <div className="space-y-3">
          <span className="text-xs font-bold text-slate-300 uppercase">Rollout Rings & Adoption</span>
          <div className="space-y-2 text-xs">
            {rings.map((r, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-300 font-semibold">{r.name}</span>
                  <span className="text-slate-400 font-mono">{r.count}</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${r.progress}%` }}></div>
                </div>
              </div>
            ))}
          </div>
          <button className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-1.5 text-xs font-bold transition flex items-center justify-center gap-1.5 mt-2">
            <Play className="w-3.5 h-3.5" />
            Advance Ring
          </button>
        </div>

        {/* Rollout Controls */}
        <div className="space-y-3">
          <span className="text-xs font-bold text-slate-300 uppercase">Rollout Controls</span>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between border-b border-white/5 pb-1">
              <span className="text-slate-400">Version</span>
              <span className="text-white font-semibold">v1.0.0-GA</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-1">
              <span className="text-slate-400">Feature Flags</span>
              <span className="text-green-400 font-bold">6 Active</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-1">
              <span className="text-slate-400">Kill Switch</span>
              <span className="text-red-400 font-bold">Inactive</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-1">
              <span className="text-slate-400">Auto Rollback</span>
              <span className="text-green-400 font-bold">Enabled</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-1">
              <span className="text-slate-400">Canary Analysis</span>
              <span className="text-green-400 font-bold">Healthy</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
