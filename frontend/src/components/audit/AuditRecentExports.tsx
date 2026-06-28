import React from "react";

type ExportLog = {
  timestamp: string;
  filename: string;
  format: "json" | "csv" | "markdown";
  recordsCount: number;
};

type Props = {
  exports: ExportLog[];
};

export const AuditRecentExports: React.FC<Props> = ({ exports }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", textAlign: "left" }}>
      <h3 style={{ fontSize: "12px", color: "#818cf8", margin: 0, fontWeight: "bold" }}>
        RECENT EXPORTS
      </h3>
      {exports.length === 0 ? (
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", padding: "8px 0" }}>
          No files exported in this session yet.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", color: "var(--text-secondary)" }}>
                <th style={{ padding: "6px 4px", textAlign: "left" }}>Time</th>
                <th style={{ padding: "6px 4px", textAlign: "left" }}>Filename</th>
                <th style={{ padding: "6px 4px", textAlign: "center" }}>Format</th>
                <th style={{ padding: "6px 4px", textAlign: "right" }}>Records</th>
              </tr>
            </thead>
            <tbody>
              {exports.map((log, idx) => (
                <tr key={idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={{ padding: "6px 4px", color: "#cbd5e1" }}>
                    {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </td>
                  <td style={{ padding: "6px 4px", color: "#fff", fontFamily: "monospace", maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {log.filename}
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "center" }}>
                    <span
                      style={{
                        background: log.format === "json" ? "rgba(59, 130, 246, 0.2)" : log.format === "csv" ? "rgba(16, 185, 129, 0.2)" : "rgba(168, 85, 247, 0.2)",
                        color: log.format === "json" ? "#3b82f6" : log.format === "csv" ? "#10b981" : "#a855f7",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontSize: "9px",
                        fontWeight: "bold",
                        textTransform: "uppercase"
                      }}
                    >
                      {log.format}
                    </span>
                  </td>
                  <td style={{ padding: "6px 4px", textAlign: "right", color: "#cbd5e1" }}>
                    {log.recordsCount}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
