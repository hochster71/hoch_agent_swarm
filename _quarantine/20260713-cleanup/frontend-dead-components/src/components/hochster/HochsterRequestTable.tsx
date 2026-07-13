import React from "react";
import { Clock, HelpCircle, User } from "lucide-react";
import { HochsterSolveRequest } from "../../lib/hochster/hochsterTypes";

interface Props {
  requests: HochsterSolveRequest[];
  selectedRequestId: string | null;
  onSelectRequest: (id: string) => void;
}

export const HochsterRequestTable: React.FC<Props> = ({
  requests,
  selectedRequestId,
  onSelectRequest
}) => {
  return (
    <div className="glass-panel p-5 rounded-xl border border-white/10 bg-white/2 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-bold text-white">Active Requests</h3>
        <span className="text-xs text-slate-400">Total in queue: {requests.length}</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-slate-400 uppercase font-bold">
              <th className="pb-2">ID</th>
              <th className="pb-2">Problem Summary</th>
              <th className="pb-2">Type</th>
              <th className="pb-2">Swarm</th>
              <th className="pb-2">Instances</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Progress</th>
              <th className="pb-2 text-right">Updated</th>
            </tr>
          </thead>
          <tbody>
            {requests.map(req => {
              const isSelected = selectedRequestId === req.request_id;
              
              // Map status logic
              let statusColor = "bg-blue-500/10 text-blue-400 border border-blue-500/20";
              let progressColor = "bg-blue-400";
              let progress = 50;

              if (req.status === "queued") {
                statusColor = "bg-slate-500/10 text-slate-400 border border-slate-500/20";
                progress = 10;
                progressColor = "bg-slate-400";
              } else if (req.status === "assigned") {
                statusColor = "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
                progress = 25;
                progressColor = "bg-indigo-400";
              } else if (req.status === "analyzing") {
                statusColor = "bg-purple-500/10 text-purple-400 border border-purple-500/20";
                progress = 45;
                progressColor = "bg-purple-400";
              } else if (req.status === "executing_tools") {
                statusColor = "bg-amber-500/10 text-amber-400 border border-amber-500/20";
                progress = 70;
                progressColor = "bg-amber-400";
              } else if (req.status === "validating") {
                statusColor = "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20";
                progress = 90;
                progressColor = "bg-cyan-400";
              } else if (req.status === "solved") {
                statusColor = "bg-green-500/10 text-green-400 border border-green-500/20";
                progress = 100;
                progressColor = "bg-green-400";
              } else if (req.status === "failed") {
                statusColor = "bg-red-500/10 text-red-400 border border-red-500/20";
                progress = 100;
                progressColor = "bg-red-500";
              } else if (req.status === "cancelled") {
                statusColor = "bg-slate-500/10 text-slate-500 border border-slate-500/25";
                progress = 100;
                progressColor = "bg-slate-500";
              }

              return (
                <tr
                  key={req.request_id}
                  onClick={() => onSelectRequest(req.request_id)}
                  className={`border-b border-white/5 hover:bg-white/1 cursor-pointer transition ${
                    isSelected ? "bg-blue-500/5 border-blue-500/30" : ""
                  }`}
                >
                  <td className="py-3 font-mono text-slate-400">{req.request_id}</td>
                  <td className="py-3 font-bold text-white max-w-[200px] truncate">{req.problem.summary}</td>
                  <td className="py-3 capitalize text-slate-400">{req.problem.type.replace("_", " ")}</td>
                  <td className="py-3 text-slate-300">{req.caller.swarm_name}</td>
                  <td className="py-3 font-mono">{req.max_instances}</td>
                  <td className="py-3">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${statusColor}`}>
                      {req.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="py-3 min-w-[80px]">
                    <div className="flex items-center gap-2">
                      <div className="w-12 bg-white/10 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${progressColor} transition-all duration-300`}
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">{progress}%</span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-slate-400 font-mono">
                    {new Date(req.requested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
