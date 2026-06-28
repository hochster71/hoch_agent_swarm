import { useApprovalStore } from "@/lib/collab/approvalStore";
import { checkRequestEscalation, DEFAULT_ESCALATION_POLICIES } from "@/lib/collab/escalationRules";
import { ShieldAlert, Zap } from "lucide-react";
import { useAuditStore } from "@/lib/audit/auditStore";
import { createAuditEvent } from "@/lib/audit/auditEvents";

export function EscalationPanel() {
  const { requests, updateStatus } = useApprovalStore();
  const addEvent = useAuditStore((state) => state.addEvent);

  function runEscalationCheck() {
    let count = 0;
    requests.forEach((req) => {
      if (req.status === "pending") {
        const { shouldEscalate, action, reason } = checkRequestEscalation(req);
        if (shouldEscalate && action === "escalate_to_admin") {
          updateStatus(req.approval_id, "escalated");
          count++;

          // Create audit event for escalation
          addEvent(
            createAuditEvent({
              actor: {
                id: "system-escalator",
                name: "System Policy Engine",
                type: "system",
                role: "Core Engine",
              },
              action: {
                type: "COMMAND_BLOCKED",
                summary: `Request ${req.approval_id} escalated: ${reason}`,
              },
              target: {
                type: "swarm",
                id: req.target.id,
                name: req.target.name,
              },
              result: "blocked",
              severity: "high",
              provenance: {
                source: "observed",
                evidence_refs: [],
              },
              policy: {
                required: true,
                result: "failed",
              },
            })
          );
        } else if (shouldEscalate && action === "auto_reject") {
          updateStatus(req.approval_id, "expired");
          count++;
          
          addEvent(
            createAuditEvent({
              actor: {
                id: "system-escalator",
                name: "System Policy Engine",
                type: "system",
                role: "Core Engine",
              },
              action: {
                type: "COMMAND_BLOCKED",
                summary: `Request ${req.approval_id} auto-rejected: ${reason}`,
              },
              target: {
                type: "swarm",
                id: req.target.id,
                name: req.target.name,
              },
              result: "blocked",
              severity: "high",
              provenance: {
                source: "observed",
                evidence_refs: [],
              },
              policy: {
                required: true,
                result: "failed",
              },
            })
          );
        }
      }
    });

    alert(`Escalation sweep complete. Checked ${requests.filter(r => r.status === "pending").length} pending requests. ${count} actions triggered.`);
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-rose-500" />
          <h3 className="font-mono text-sm font-semibold tracking-wider text-slate-200">
            ESCALATION CONTROLLER
          </h3>
        </div>
        <button
          onClick={runEscalationCheck}
          className="flex items-center gap-1 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 px-2 py-1 text-xs font-mono font-medium text-rose-400 transition-all"
        >
          <Zap className="h-3 w-3" />
          SWEEP QUEUE
        </button>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {DEFAULT_ESCALATION_POLICIES.map((policy) => (
          <div
            key={policy.id}
            className="rounded border border-slate-900 bg-slate-950/40 p-3 hover:border-slate-800 transition-colors"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-slate-300">{policy.name}</span>
              <span className="rounded bg-rose-500/10 px-1.5 py-0.5 text-[9px] text-rose-400 font-semibold tracking-wider uppercase">
                {policy.action.replace(/_/g, " ")}
              </span>
            </div>
            <p className="text-slate-500 leading-normal text-[11px]">{policy.description}</p>
            <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-400">
              <span className="font-semibold text-rose-500">Trigger:</span>
              <span>
                {policy.triggerMinutes === 0 ? "Upon timestamp expiration" : `${policy.triggerMinutes} minutes pending`}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
