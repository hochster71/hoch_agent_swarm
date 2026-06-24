import React from "react";
import type { AuditReportFilters } from "../../lib/audit/auditReportTypes";

type Props = {
  filters: AuditReportFilters;
  onChange: (filters: AuditReportFilters) => void;
  onClear: () => void;
  eventsCount: number;
};

export const AuditFilterPanel: React.FC<Props> = ({
  filters,
  onChange,
  onClear,
  eventsCount,
}) => {
  const handleSelectChange = (key: keyof AuditReportFilters, value: string) => {
    onChange({
      ...filters,
      [key]: value || undefined,
    });
  };

  return (
    <div
      style={{
        width: "220px",
        background: "rgba(22, 28, 45, 0.4)",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        textAlign: "left",
        flexShrink: 0
      }}
    >
      <div style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "8px" }}>
        <h3 style={{ margin: 0, fontSize: "12px", letterSpacing: "0.5px", color: "#818cf8", fontWeight: "bold" }}>
          AUDIT FILTERS
        </h3>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "11px" }}>
        {/* Severity */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ color: "var(--text-secondary)", fontWeight: "500" }}>Severity</label>
          <select
            value={filters.severity || ""}
            onChange={(e) => handleSelectChange("severity", e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px",
              color: "#fff",
              outline: "none"
            }}
          >
            <option value="">All Severities</option>
            <option value="info">Info</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        {/* Result */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ color: "var(--text-secondary)", fontWeight: "500" }}>Result</label>
          <select
            value={filters.result || ""}
            onChange={(e) => handleSelectChange("result", e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px",
              color: "#fff",
              outline: "none"
            }}
          >
            <option value="">All Results</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="blocked">Blocked</option>
            <option value="warning">Warning</option>
          </select>
        </div>

        {/* Policy Result */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ color: "var(--text-secondary)", fontWeight: "500" }}>Policy Status</label>
          <select
            value={filters.policy_result || ""}
            onChange={(e) => handleSelectChange("policy_result", e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px",
              color: "#fff",
              outline: "none"
            }}
          >
            <option value="">All Checks</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
            <option value="not_required">Not Required</option>
          </select>
        </div>

        {/* Actor Type */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ color: "var(--text-secondary)", fontWeight: "500" }}>Actor Type</label>
          <select
            value={filters.actor_type || ""}
            onChange={(e) => handleSelectChange("actor_type", e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px",
              color: "#fff",
              outline: "none"
            }}
          >
            <option value="">All Actors</option>
            <option value="human">Human</option>
            <option value="agent">Agent</option>
            <option value="system">System</option>
            <option value="swarm">Swarm</option>
          </select>
        </div>

        {/* Target Type */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ color: "var(--text-secondary)", fontWeight: "500" }}>Target Type</label>
          <select
            value={filters.target_type || ""}
            onChange={(e) => handleSelectChange("target_type", e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px",
              color: "#fff",
              outline: "none"
            }}
          >
            <option value="">All Targets</option>
            <option value="asset">Asset</option>
            <option value="swarm">Swarm</option>
            <option value="task">Task</option>
            <option value="policy">Policy</option>
            <option value="command">Command</option>
            <option value="system">System</option>
          </select>
        </div>

        {/* Correlation ID */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ color: "var(--text-secondary)", fontWeight: "500" }}>Correlation ID</label>
          <input
            type="text"
            placeholder="Search ID..."
            value={filters.correlation_id || ""}
            onChange={(e) => handleSelectChange("correlation_id", e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px 8px",
              color: "#fff",
              outline: "none",
              fontSize: "11px"
            }}
          />
        </div>
      </div>

      <div style={{ flexGrow: 1 }} />

      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <button
          onClick={onClear}
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            color: "#fff",
            borderRadius: "4px",
            padding: "6px",
            fontSize: "11px",
            cursor: "pointer"
          }}
        >
          Clear Filters
        </button>
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", textAlign: "center" }}>
          Filtered: <strong style={{ color: "#fff" }}>{eventsCount}</strong> events
        </div>
      </div>
    </div>
  );
};
