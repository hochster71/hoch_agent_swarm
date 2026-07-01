import React from "react";
import { BarChart3, TrendingUp, Sparkles, Zap, Percent, Clock } from "lucide-react";

export const HochsterMetricsPanel: React.FC = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
      {/* Total Active Instances */}
      <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
        <div className="flex justify-between items-center text-slate-400 text-xs font-bold uppercase tracking-wider">
          <span>Active Instances</span>
          <Zap className="w-4 h-4 text-yellow-400" />
        </div>
        <div className="text-2xl font-bold text-white">8 / 12</div>
        <p className="text-[10px] text-slate-400 font-semibold">66% capacity utilization</p>
      </div>

      {/* Requests */}
      <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
        <div className="flex justify-between items-center text-slate-400 text-xs font-bold uppercase tracking-wider">
          <span>Requests (24h)</span>
          <BarChart3 className="w-4 h-4 text-blue-400" />
        </div>
        <div className="text-2xl font-bold">126</div>
        <p className="text-[10px] text-green-400 font-semibold flex items-center gap-1">
          <TrendingUp className="w-3 h-3" /> +18% vs yesterday
        </p>
      </div>

      {/* Solutions */}
      <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
        <div className="flex justify-between items-center text-slate-400 text-xs font-bold uppercase tracking-wider">
          <span>Solutions (24h)</span>
          <Sparkles className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold text-emerald-400">98</div>
        <p className="text-[10px] text-green-400 font-semibold flex items-center gap-1">
          <TrendingUp className="w-3 h-3" /> 77.8% Success Rate
        </p>
      </div>

      {/* Avg Response Time */}
      <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
        <div className="flex justify-between items-center text-slate-400 text-xs font-bold uppercase tracking-wider">
          <span>Avg Response Time</span>
          <Clock className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="text-2xl font-bold text-white">3.42s</div>
        <p className="text-[10px] text-green-400 font-semibold flex items-center gap-1">
          <Percent className="w-3 h-3" /> -0.8% vs yesterday
        </p>
      </div>

      {/* Version */}
      <div className="glass-panel p-4 rounded-xl border border-white/5 bg-white/2 space-y-1">
        <div className="flex justify-between items-center text-slate-400 text-xs font-bold uppercase tracking-wider">
          <span>Runtime Version</span>
          <Percent className="w-4 h-4 text-purple-400" />
        </div>
        <div className="text-xl font-bold text-white">v1.0.0-GA</div>
        <p className="text-[10px] text-slate-500 font-mono">Build: 2026.06.24</p>
      </div>
    </div>
  );
};
