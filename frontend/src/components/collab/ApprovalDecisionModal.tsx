import { useState } from "react";
import { useApprovalStore } from "@/lib/collab/approvalStore";
import type { ApprovalRequest, ApprovalDecision } from "@/lib/collab/collaborationTypes";
import { X, Check, AlertTriangle, MessageSquare, ShieldAlert } from "lucide-react";

type Props = {
  request: ApprovalRequest;
  onClose: () => void;
};

export function ApprovalDecisionModal({ request, onClose }: Props) {
  const { addDecision, operators } = useApprovalStore();
  const [selectedOperatorId, setSelectedOperatorId] = useState(
    operators.find((op) => op.status === "online" && (op.role === "approver" || op.role === "admin"))?.id || operators[0]?.id || ""
  );
  const [note, setNote] = useState("");
  const [decisionType, setDecisionType] = useState<ApprovalDecision>("approve");

  function handleSubmit() {
    const decider = operators.find((op) => op.id === selectedOperatorId);
    if (!decider) return;

    addDecision(request.approval_id, {
      decision_id: `dec-${Math.random().toString(36).substr(2, 9)}`,
      decided_at: new Date().toISOString(),
      decided_by: {
        id: decider.id,
        name: decider.name,
        role: decider.role
      },
      decision: decisionType,
      note: note.trim() || `Command ${decisionType}d via console sign-off.`
    });

    onClose();
  }

  const selectedOperator = operators.find((op) => op.id === selectedOperatorId);
  const isUnauthorizedRole = selectedOperator
    ? request.required_approver_role === "admin" && selectedOperator.role !== "admin"
    : true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-lg border border-slate-800 bg-slate-950 p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-900 pb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-amber-500" />
            <h3 className="font-mono text-base font-bold text-slate-100 tracking-wider">
              SWARM SECURITY SIGN-OFF
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="my-4 space-y-4">
          {/* Command Details */}
          <div className="rounded border border-slate-900 bg-slate-950/40 p-3">
            <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest block mb-1">
              Command payload
            </span>
            <code className="font-mono text-xs text-rose-400 break-all">
              {request.command.raw_text}
            </code>
            <div className="mt-2 flex items-center gap-4 text-xs font-mono">
              <span className="text-slate-400">
                Risk Level:{" "}
                <span
                  className={
                    request.command.risk === "critical"
                      ? "text-rose-500 font-bold"
                      : request.command.risk === "high"
                      ? "text-amber-500 font-bold"
                      : "text-cyan-400"
                  }
                >
                  {request.command.risk.toUpperCase()}
                </span>
              </span>
              <span className="text-slate-400">
                Required Role:{" "}
                <span className="text-amber-400 uppercase">{request.required_approver_role}</span>
              </span>
            </div>
          </div>

          {/* Actor selection to simulate different peers */}
          <div>
            <label className="block font-mono text-xs text-slate-400 mb-1.5">
              Select Signing Authority (Simulate Peer)
            </label>
            <select
              value={selectedOperatorId}
              onChange={(e) => setSelectedOperatorId(e.target.value)}
              className="w-full h-9 rounded border border-slate-800 bg-slate-900 px-3 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              {operators.map((op) => (
                <option key={op.id} value={op.id}>
                  {op.name} ({op.role.toUpperCase()}) — {op.status}
                </option>
              ))}
            </select>
            {isUnauthorizedRole && selectedOperator && (
              <div className="mt-1.5 flex items-center gap-1 text-[11px] text-rose-400">
                <AlertTriangle className="h-3 w-3 shrink-0" />
                <span>
                  Role "{selectedOperator.role}" is insufficient. Required: "{request.required_approver_role}"
                </span>
              </div>
            )}
          </div>

          {/* Decision Type */}
          <div>
            <label className="block font-mono text-xs text-slate-400 mb-2">
              Decision Action
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setDecisionType("approve")}
                className={`flex h-9 items-center justify-center gap-1.5 rounded border text-xs font-mono tracking-wider transition-all ${
                  decisionType === "approve"
                    ? "bg-emerald-500/10 border-emerald-500 text-emerald-400 font-semibold"
                    : "border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-900"
                }`}
              >
                <Check className="h-3.5 w-3.5" />
                APPROVE
              </button>
              <button
                type="button"
                onClick={() => setDecisionType("reject")}
                className={`flex h-9 items-center justify-center gap-1.5 rounded border text-xs font-mono tracking-wider transition-all ${
                  decisionType === "reject"
                    ? "bg-rose-500/10 border-rose-500 text-rose-400 font-semibold"
                    : "border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-900"
                }`}
              >
                <X className="h-3.5 w-3.5" />
                REJECT
              </button>
              <button
                type="button"
                onClick={() => setDecisionType("request_changes")}
                className={`flex h-9 items-center justify-center gap-1.5 rounded border text-xs font-mono tracking-wider transition-all ${
                  decisionType === "request_changes"
                    ? "bg-amber-500/10 border-amber-500 text-amber-400 font-semibold"
                    : "border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-900"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                RE-ROUTE
              </button>
            </div>
          </div>

          {/* Decision Note */}
          <div>
            <label className="block font-mono text-xs text-slate-400 mb-1.5">
              Justification / Audit Note
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Provide context or instructions for this decision..."
              className="w-full min-h-[80px] rounded border border-slate-800 bg-slate-900 p-2.5 text-xs text-slate-200 placeholder-slate-600 focus:border-cyan-500 focus:outline-none resize-none"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-slate-900 pt-4">
          <button
            onClick={onClose}
            className="h-8 rounded border border-slate-800 bg-slate-900 px-4 text-xs font-mono text-slate-400 hover:bg-slate-850"
          >
            CANCEL
          </button>
          <button
            onClick={handleSubmit}
            disabled={isUnauthorizedRole}
            className={`h-8 rounded px-4 text-xs font-mono font-bold tracking-wider text-slate-950 ${
              isUnauthorizedRole
                ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                : decisionType === "approve"
                ? "bg-emerald-400 hover:bg-emerald-500"
                : decisionType === "reject"
                ? "bg-rose-400 hover:bg-rose-500"
                : "bg-amber-400 hover:bg-amber-500"
            }`}
          >
            COMMIT DECISION
          </button>
        </div>
      </div>
    </div>
  );
}
