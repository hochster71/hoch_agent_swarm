import { ApprovalQueue } from "./ApprovalQueue";
import { OperatorPresencePanel } from "./OperatorPresencePanel";
import { EscalationPanel } from "./EscalationPanel";
import { ApprovalHistory } from "./ApprovalHistory";
import { MessageSquare } from "lucide-react";

export function CollaborationDashboard() {
  return (
    <div className="p-6 space-y-6 max-h-[calc(100vh-120px)] overflow-y-auto w-full">
      {/* Header Info */}
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <div>
          <h1 className="text-xl font-bold tracking-wider font-mono text-slate-100 flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-cyan-400" />
            SWARM SECURE COLLABORATION PANEL
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Dual-operator approval workflows, presence logs, and safety delegation controls.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Columns (Queue & History) */}
        <div className="lg:col-span-2 space-y-6">
          <ApprovalQueue />
          <ApprovalHistory />
        </div>

        {/* Right Column (Presence & Escalations) */}
        <div className="space-y-6">
          <OperatorPresencePanel />
          <EscalationPanel />
        </div>
      </div>
    </div>
  );
}
