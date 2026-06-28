import React from "react";
import type { IncidentSummary } from "../../lib/replay/replayTypes";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { useAuditStore } from "../../lib/audit/auditStore";
import { createAuditEvent } from "../../lib/audit/auditEvents";

type Props = {
  summary: IncidentSummary;
  events: AuditEvent[];
};

function downloadTextFile(params: {
  filename: string;
  content: string;
  type: string;
}) {
  const blob = new Blob([params.content], { type: params.type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = params.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const IncidentExportButton: React.FC<Props> = ({ summary, events }) => {
  const addEvent = useAuditStore((state) => state.addEvent);

  const handleExport = () => {
    const reportData = {
      summary,
      manifest: {
        total_events: events.length,
        evidence_files_count: summary.evidence_refs.length,
        policy_rules_evaluated: summary.policy_findings.length,
      },
      events
    };

    const filename = `incident-pack-${summary.incident_id}.json`;
    downloadTextFile({
      filename,
      content: JSON.stringify(reportData, null, 2),
      type: "application/json",
    });

    // Audit log the export
    addEvent(
      createAuditEvent({
        actor: {
          id: "michael.hoch",
          name: "Michael Hoch",
          type: "human",
          role: "Operator"
        },
        action: {
          type: "AUDIT_EXPORTED",
          summary: `Exported Incident Pack ${summary.incident_id} containing ${events.length} correlated events.`,
        },
        target: {
          type: "system",
          id: "incident-reconstruction-layer",
          name: "Incident Reconstruction Layer"
        },
        result: "success",
        severity: "info",
        provenance: {
          source: "manual",
          evidence_refs: []
        },
        policy: {
          required: false,
          result: "not_required"
        }
      })
    );
  };

  return (
    <button
      onClick={handleExport}
      style={{
        background: "rgba(239, 68, 68, 0.2)",
        border: "1px solid rgba(239, 68, 68, 0.4)",
        borderRadius: "6px",
        padding: "8px 12px",
        color: "#fff",
        fontSize: "11px",
        fontWeight: "bold",
        cursor: "pointer",
        textAlign: "center"
      }}
    >
      Export Incident Packet (.json)
    </button>
  );
};
