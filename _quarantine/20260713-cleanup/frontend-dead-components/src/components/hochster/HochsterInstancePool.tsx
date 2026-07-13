import React from "react";
import { Cpu, Server, ShieldCheck, UserCheck } from "lucide-react";
import { HochsterInstance } from "../../lib/hochster/hochsterTypes";

interface Props {
  instances: HochsterInstance[];
}

export const HochsterInstancePool: React.FC<Props> = ({ instances }) => {
  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Server className="w-5 h-5 text-blue-400" /> Instance Pool <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full font-bold">8 / 12 Running</span>
        </h3>
        <span className="text-xs text-indigo-400 cursor-pointer hover:underline font-semibold">View All Instances</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {instances.map(inst => {
          let statusBadge = "bg-green-500/20 text-green-400 border border-green-500/20";
          if (inst.status === "busy") statusBadge = "bg-orange-500/20 text-orange-400 border border-orange-500/20";
          if (inst.status === "offline") statusBadge = "bg-slate-500/20 text-slate-500 border border-slate-500/20";

          return (
            <div key={inst.instance_id} className="p-4 rounded-xl bg-white/2 border border-white/5 space-y-3 hover:border-white/10 transition">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-bold text-sm text-white flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${inst.status === "online" ? "bg-green-400 animate-pulse" : "bg-orange-400"}`}></span>
                    {inst.instance_id}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">{inst.region}</span>
                </div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase ${statusBadge}`}>
                  {inst.status === "online" ? "Running" : inst.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs border-t border-white/5 pt-2.5">
                <div>
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">CPU</span>
                  <span className="font-semibold text-white font-mono">{inst.cpu_percent}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">Memory</span>
                  <span className="font-semibold text-white font-mono">{inst.memory_usage_gb} GB</span>
                </div>
                <div className="col-span-2">
                  <span className="text-[10px] text-slate-400 block font-bold uppercase">Swarm (Primary)</span>
                  <span className="text-slate-300 truncate block font-medium">{inst.primary_swarm}</span>
                </div>
              </div>
            </div>
          );
        })}

        {/* Empty slots placeholders matching the prototype image */}
        <div className="p-4 rounded-xl border border-dashed border-white/10 bg-white/1 flex flex-col justify-center items-center text-center opacity-40">
          <span className="text-[11px] text-slate-400 font-bold uppercase">Available Slot</span>
        </div>
        <div className="p-4 rounded-xl border border-dashed border-white/10 bg-white/1 flex flex-col justify-center items-center text-center opacity-40">
          <span className="text-[11px] text-slate-400 font-bold uppercase">Available Slot</span>
        </div>
        <div className="p-4 rounded-xl border border-dashed border-white/10 bg-white/1 flex flex-col justify-center items-center text-center opacity-40">
          <span className="text-[11px] text-slate-400 font-bold uppercase">Available Slot</span>
        </div>
        <div className="p-4 rounded-xl border border-dashed border-white/10 bg-white/1 flex flex-col justify-center items-center text-center opacity-40">
          <span className="text-[11px] text-slate-400 font-bold uppercase">Toolbox Slot</span>
        </div>
      </div>
    </div>
  );
};
