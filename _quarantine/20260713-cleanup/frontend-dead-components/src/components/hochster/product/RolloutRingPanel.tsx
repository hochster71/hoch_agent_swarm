import React from "react";

export const RolloutRingPanel: React.FC = () => {
  return (
    <div className="glass-panel p-4 rounded-xl border border-white/10 bg-white/2 text-left space-y-2">
      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Active Rollout Rings</h4>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-400">Current active ring:</span>
          <span className="text-blue-400 font-semibold uppercase">pilot_tenants</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Enabled tenants count:</span>
          <span className="text-white font-mono">3 tenants</span>
        </div>
      </div>
    </div>
  );
};
