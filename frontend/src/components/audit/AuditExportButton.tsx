import type { AuditEvent } from "@/lib/audit/auditTypes";
import { downloadJsonAudit } from "@/lib/audit/auditExport";
import { useAuditStore } from "@/lib/audit/auditStore";
import { createAuditEvent } from "@/lib/audit/auditEvents";

type Props = {
  events: AuditEvent[];
};

export function AuditExportButton({ events }: Props) {
  const addEvent = useAuditStore((state) => state.addEvent);
  
  function handleExport() {
    downloadJsonAudit(events);
    addEvent(
      createAuditEvent({
        actor: {
          id: "michael.hoch",
          name: "Michael Hoch",
          type: "human",
          role: "Operator",
        },
        action: {
          type: "AUDIT_EXPORTED",
          summary: `Exported ${events.length} audit events as JSON.`,
        },
        target: {
          type: "system",
          id: "operational-audit-layer",
          name: "Operational Audit Layer",
        },
        result: "success",
        severity: "info",
        provenance: {
          source: "manual",
          evidence_refs: [],
        },
        policy: {
          required: false,
          result: "not_required",
        },
      })
    );
  }
  
  return (
    <button
      onClick={handleExport}
      className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
    >
      Export JSON
    </button>
  );
}
