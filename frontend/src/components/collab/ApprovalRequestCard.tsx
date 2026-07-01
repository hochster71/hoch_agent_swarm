import { useState } from "react";
import type { ApprovalRequest } from "@/lib/collab/collaborationTypes";
import { ApprovalDecisionModal } from "./ApprovalDecisionModal";
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Clock,
  User,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle
} from "lucide-react";

type Props = {
  request: ApprovalRequest;
};

export function ApprovalRequestCard({ request }: Props) {
  const [showModal, setShowModal] = useState(false);

  const getRiskBadgeColor = (risk: ApprovalRequest["command"]["risk"]) => {
    switch (risk) {
      case "critical":
        return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      case "high":
        return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      case "medium":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "low":
        return "bg-slate-800 text-slate-400 border-slate-700/50";
    }
  };

  const getStatusBadge = (status: ApprovalRequest["status"]) => {
    switch (status) {
      case "pending":
        return (
          <span className="flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-500 uppercase tracking-wider">
            <Clock className="h-3 w-3" />
            PENDING PEER SIGNOFF
          </span>
        );
      case "approved":
        return (
          <span className="flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 uppercase tracking-wider">
            <ShieldCheck className="h-3 w-3" />
            APPROVED & SIGNED
          </span>
        );
      case "rejected":
        return (
          <span className="flex items-center gap-1 rounded-full border border-rose-500/20 bg-rose-500/10 px-2 py-0.5 text-[10px] font-medium text-rose-500 uppercase tracking-wider">
            <XCircle className="h-3 w-3" />
            REJECTED / BLOCKED
          </span>
        );
      case "changes_requested":
        return (
          <span className="flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-500 uppercase tracking-wider">
            <AlertTriangle className="h-3 w-3" />
            CHANGES REQUESTED
          </span>
        );
      case "expired":
        return (
          <span className="flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-500 uppercase tracking-wider">
            <Clock className="h-3 w-3" />
            EXPIRED
          </span>
        );
      case "escalated":
        return (
          <span className="flex items-center gap-1 rounded-full border border-rose-500/20 bg-rose-500/10 px-2 py-0.5 text-[10px] font-medium text-rose-400 uppercase tracking-wider">
            <ShieldAlert className="h-3 w-3" />
            ESCALATED TO ADMIN
          </span>
        );
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case "approve":
        return <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />;
      case "reject":
        return <XCircle className="h-3.5 w-3.5 text-rose-400" />;
      case "request_changes":
        return <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />;
      default:
        return <HelpCircle className="h-3.5 w-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 hover:border-slate-700/60 transition-all duration-200">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-900 pb-3">
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="font-bold text-slate-300">REQ: {request.approval_id}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-500">
            {new Date(request.created_at).toLocaleTimeString()}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${getRiskBadgeColor(
              request.command.risk
            )}`}
          >
            {request.command.risk} RISK
          </span>
          {getStatusBadge(request.status)}
        </div>
      </div>

      <div className="my-3 space-y-2">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <User className="h-3.5 w-3.5 text-slate-500" />
          <span>
            Requested by: <span className="text-slate-300">{request.requested_by.name}</span>{" "}
            <span className="text-slate-500 uppercase text-[10px]">({request.requested_by.role})</span>
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Activity className="h-3.5 w-3.5 text-slate-500" />
          <span>
            Target: <span className="text-cyan-400">{request.target.name}</span>{" "}
            <span className="text-slate-600">[{request.target.type}]</span>
          </span>
        </div>

        <div className="rounded border border-slate-900 bg-slate-950/70 p-2.5">
          <code className="font-mono text-xs text-slate-200 select-all block break-all whitespace-pre-wrap">
            {request.command.raw_text}
          </code>
        </div>

        {/* Policy Reasons / Warnings */}
        {request.policy_context.blockers.length > 0 && (
          <div className="rounded border border-rose-950/30 bg-rose-950/10 p-2 text-xs text-rose-400">
            <span className="font-semibold block mb-0.5">Policy Blocks:</span>
            <ul className="list-disc pl-4 space-y-0.5">
              {request.policy_context.blockers.map((b, idx) => (
                <li key={idx} className="font-mono text-[11px]">
                  {b}
                </li>
              ))}
            </ul>
          </div>
        )}

        {request.policy_context.warnings.length > 0 && (
          <div className="rounded border border-amber-950/30 bg-amber-950/10 p-2 text-xs text-amber-400">
            <span className="font-semibold block mb-0.5">Policy Warnings:</span>
            <ul className="list-disc pl-4 space-y-0.5">
              {request.policy_context.warnings.map((w, idx) => (
                <li key={idx} className="font-mono text-[11px]">
                  {w}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Decisions History */}
        {request.decisions.length > 0 && (
          <div className="border-t border-slate-900 pt-3">
            <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider block mb-2">
              Sign-Off Decisions
            </span>
            <div className="space-y-2">
              {request.decisions.map((dec) => (
                <div
                  key={dec.decision_id}
                  className="flex items-start gap-2.5 rounded border border-slate-900 bg-slate-950/30 p-2"
                >
                  <div className="mt-0.5">{getDecisionIcon(dec.decision)}</div>
                  <div className="text-xs">
                    <div className="flex items-center gap-1 font-mono text-[11px]">
                      <span className="font-semibold text-slate-300">{dec.decided_by.name}</span>
                      <span className="text-slate-500 uppercase">({dec.decided_by.role})</span>
                      <span className="text-slate-600">|</span>
                      <span className="text-slate-500">
                        {new Date(dec.decided_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="mt-1 text-slate-400 italic">"{dec.note}"</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {request.status === "pending" && (
        <div className="mt-3 flex justify-end border-t border-slate-900 pt-3">
          <button
            onClick={() => setShowModal(true)}
            className="flex h-8 items-center gap-1.5 rounded bg-cyan-500 px-3 text-xs font-mono font-bold text-slate-950 hover:bg-cyan-400 transition-all shadow-md shadow-cyan-500/10"
          >
            <Shield className="h-3.5 w-3.5" />
            PERFORM SECURE SIGN-OFF
          </button>
        </div>
      )}

      {showModal && (
        <ApprovalDecisionModal request={request} onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}
