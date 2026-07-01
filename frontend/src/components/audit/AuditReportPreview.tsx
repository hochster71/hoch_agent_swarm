import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { buildAuditReport } from "../../lib/audit/auditExport";
import { auditReportToMarkdown } from "../../lib/audit/auditMarkdown";

type Props = {
  events: AuditEvent[];
  onClose: () => void;
};

export const AuditReportPreview: React.FC<Props> = ({ events, onClose }) => {
  const [format, setFormat] = React.useState<"json" | "markdown">("json");

  const report = React.useMemo(() => buildAuditReport({ events }), [events]);
  const previewContent = React.useMemo(() => {
    if (format === "json") {
      return JSON.stringify(report, null, 2);
    } else {
      return auditReportToMarkdown(report);
    }
  }, [report, format]);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(11, 15, 25, 0.8)",
        backdropFilter: "blur(8px)",
        zIndex: 1000,
        display: "flex",
        justifyContent: "center",
        alignItems: "center"
      }}
    >
      <div
        style={{
          width: "80%",
          maxWidth: "800px",
          height: "80%",
          background: "rgba(22, 28, 45, 0.95)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "12px",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
          color: "#fff"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "16px", fontWeight: "bold" }}>Report Preview</h2>
            <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              ID: {report.report_id} · generated at {report.generated_at}
            </span>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => setFormat("json")}
              style={{
                background: format === "json" ? "rgba(255,255,255,0.15)" : "transparent",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff",
                fontSize: "11px",
                padding: "4px 10px",
                borderRadius: "4px",
                cursor: "pointer"
              }}
            >
              JSON
            </button>
            <button
              onClick={() => setFormat("markdown")}
              style={{
                background: format === "markdown" ? "rgba(255,255,255,0.15)" : "transparent",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff",
                fontSize: "11px",
                padding: "4px 10px",
                borderRadius: "4px",
                cursor: "pointer"
              }}
            >
              Markdown
            </button>
          </div>
        </div>

        <div
          style={{
            flexGrow: 1,
            background: "rgba(0,0,0,0.3)",
            border: "1px solid rgba(255,255,255,0.05)",
            borderRadius: "8px",
            padding: "12px",
            overflowY: "auto",
            fontFamily: "monospace",
            fontSize: "11px",
            lineHeight: "1.5",
            textAlign: "left",
            whiteSpace: "pre-wrap",
            color: "#38bdf8"
          }}
        >
          {previewContent}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              background: "rgba(239, 68, 68, 0.2)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#fff",
              borderRadius: "6px",
              padding: "6px 16px",
              fontSize: "12px",
              fontWeight: "bold",
              cursor: "pointer"
            }}
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
};
