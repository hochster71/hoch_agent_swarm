import { useApprovalStore } from "@/lib/collab/approvalStore";
import type { OperatorPresence } from "@/lib/collab/collaborationTypes";
import { Users, Circle, Power } from "lucide-react";

export function OperatorPresencePanel() {
  const { operators, updateOperatorStatus } = useApprovalStore();

  const getStatusColor = (status: OperatorPresence["status"]) => {
    switch (status) {
      case "online":
        return "text-emerald-400 fill-emerald-400";
      case "away":
        return "text-amber-400 fill-amber-400";
      case "offline":
        return "text-slate-500 fill-slate-500";
      default:
        return "text-slate-500";
    }
  };

  const getStatusBadgeClass = (status: OperatorPresence["status"]) => {
    switch (status) {
      case "online":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "away":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "offline":
        return "bg-slate-800/50 text-slate-400 border-slate-700/50";
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-cyan-400" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            OPERATOR MESH PRESENCE
          </h3>
        </div>
        <span className="font-mono text-xs text-slate-500">
          Active Sessions: {operators.filter((o) => o.status === "online").length}/{operators.length}
        </span>
      </div>

      <div className="space-y-3">
        {operators.map((operator) => (
          <div
            key={operator.id}
            className="flex items-center justify-between rounded-md border border-slate-900 bg-slate-950/40 p-2.5 hover:border-slate-800/80 transition-all duration-200"
          >
            <div className="flex items-center gap-3">
              <Circle className={`h-2 w-2 ${getStatusColor(operator.status)}`} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-medium text-slate-300">
                    {operator.name}
                  </span>
                  <span className="rounded bg-slate-900 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 uppercase tracking-tight">
                    {operator.id}
                  </span>
                </div>
                <span className="text-xs text-slate-500 capitalize">{operator.role}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize tracking-wider ${getStatusBadgeClass(
                  operator.status
                )}`}
              >
                {operator.status}
              </span>
              
              <select
                value={operator.status}
                onChange={(e) => updateOperatorStatus(operator.id, e.target.value as OperatorPresence["status"])}
                className="h-7 rounded border border-slate-800 bg-slate-900 px-1 text-[11px] text-slate-400 focus:border-cyan-500 focus:outline-none"
              >
                <option value="online">Online</option>
                <option value="away">Away</option>
                <option value="offline">Offline</option>
              </select>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 border-t border-slate-900 pt-3">
        <div className="flex items-start gap-2 rounded-md bg-cyan-950/20 border border-cyan-900/30 p-2">
          <Power className="mt-0.5 h-3.5 w-3.5 text-cyan-400 shrink-0" />
          <p className="text-[10px] leading-relaxed text-cyan-300/80">
            Status modifications simulate mesh peer signals. Dual-approver requirements require two different online "approver" or "admin" roles to review critical commands.
          </p>
        </div>
      </div>
    </div>
  );
}
