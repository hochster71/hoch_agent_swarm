import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { buildAuditReport } from "../../lib/audit/auditExport";
import { auditEventsToCsv } from "../../lib/audit/auditCsv";
import { auditReportToMarkdown } from "../../lib/audit/auditMarkdown";
import { createAuditEvent } from "../../lib/audit/auditEvents";
import { useAuditStore } from "../../lib/audit/auditStore";

type Format = "json" | "csv" | "markdown";

type Props = {
  events: AuditEvent[];
  onExportRecorded?: (filename: string, format: Format) => void;
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

export const AuditExportMenu: React.FC<Props> = ({ events, onExportRecorded }) => {
  const addEvent = useAuditStore((state) => state.addEvent);

  function recordExport(filename: string, format: Format) {
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
          summary: `Exported ${events.length} audit events as ${format.toUpperCase()} (${filename}).`,
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
        metadata: {
          format,
          filename,
          event_count: events.length,
        },
      })
    );
    if (onExportRecorded) {
      onExportRecorded(filename, format);
    }
  }

  function exportJson() {
    const report = buildAuditReport({ events });
    const filename = `${report.report_id}.json`;
    downloadTextFile({
      filename,
      content: JSON.stringify(report, null, 2),
      type: "application/json",
    });
    recordExport(filename, "json");
  }

  function exportCsv() {
    const filename = `operational-audit-${Date.now()}.csv`;
    downloadTextFile({
      filename,
      content: auditEventsToCsv(events),
      type: "text/csv;charset=utf-8",
    });
    recordExport(filename, "csv");
  }

  function exportMarkdown() {
    const report = buildAuditReport({ events });
    const filename = `${report.report_id}.md`;
    downloadTextFile({
      filename,
      content: auditReportToMarkdown(report),
      type: "text/markdown;charset=utf-8",
    });
    recordExport(filename, "markdown");
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
      <button
        onClick={exportJson}
        style={{
          background: "rgba(59, 130, 246, 0.2)",
          border: "1px solid rgba(59, 130, 246, 0.4)",
          borderRadius: "6px",
          padding: "8px 12px",
          color: "#fff",
          fontSize: "11px",
          cursor: "pointer",
          fontWeight: "bold"
        }}
      >
        Export JSON
      </button>
      <button
        onClick={exportCsv}
        style={{
          background: "rgba(16, 185, 129, 0.2)",
          border: "1px solid rgba(16, 185, 129, 0.4)",
          borderRadius: "6px",
          padding: "8px 12px",
          color: "#fff",
          fontSize: "11px",
          cursor: "pointer",
          fontWeight: "bold"
        }}
      >
        Export CSV
      </button>
      <button
        onClick={exportMarkdown}
        style={{
          background: "rgba(168, 85, 247, 0.2)",
          border: "1px solid rgba(168, 85, 247, 0.4)",
          borderRadius: "6px",
          padding: "8px 12px",
          color: "#fff",
          fontSize: "11px",
          cursor: "pointer",
          fontWeight: "bold"
        }}
      >
        Export MD
      </button>
    </div>
  );
};
