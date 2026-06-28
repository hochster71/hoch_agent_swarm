import React from "react";
import { Cpu, HardDrive, Clock, HelpCircle } from "lucide-react";
import { HochsterInstance } from "../../lib/hochster/hochsterTypes";

interface Props {
  instances: HochsterInstance[];
}

export const HochsterInstanceTable: React.FC<Props> = ({ instances }) => {
  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <h3 className="text-lg font-bold flex items-center gap-2">
        <Cpu className="w-5 h-5 text-blue-400" /> Running HOCHSTER Instances
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-slate-400 uppercase font-bold">
              <th className="pb-2">Instance ID</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">CPU</th>
              <th className="pb-2">Memory</th>
              <th className="pb-2">Uptime</th>
              <th className="pb-2">Requests</th>
              <th className="pb-2">Queue</th>
              <th className="pb-2">Swarm (Primary)</th>
              <th className="pb-2 text-right">Region</th>
            </tr>
          </thead>
          <tbody>
            {instances.map(inst => (
              <tr key={inst.instance_id} className="border-b border-white/5 hover:bg-white/1">
                <td className="py-3 font-bold text-white flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                  {inst.instance_id}
                </td>
                <td className="py-3">
                  <span
                    className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase ${
                      inst.status === "online"
                        ? "bg-green-500/10 text-green-400 border border-green-500/20"
                        : inst.status === "busy"
                        ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                        : "bg-slate-500/10 text-slate-400 border border-slate-500/20"
                    }`}
                  >
                    {inst.status}
                  </span>
                </td>
                <td className="py-3 font-mono">{inst.cpu_percent}%</td>
                <td className="py-3 font-mono">{inst.memory_usage_gb} GB</td>
                <td className="py-3">
                  {Math.floor(inst.uptime_seconds / 3600)}h {Math.floor((inst.uptime_seconds % 3600) / 60)}m
                </td>
                <td className="py-3 font-mono">{inst.total_requests}</td>
                <td className="py-3 font-mono text-blue-400 font-bold">{inst.queue_length}</td>
                <td className="py-3 text-slate-300">{inst.primary_swarm}</td>
                <td className="py-3 text-right text-slate-400">{inst.region}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
