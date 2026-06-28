import React from "react";
import { defaultPolicyRules } from "../../lib/policy/policyRules";

export const GuardrailStatusList: React.FC = () => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", textAlign: "left" }}>
      {defaultPolicyRules.map((rule, idx) => (
        <div
          key={idx}
          style={{
            background: "rgba(0,0,0,0.15)",
            border: "1px solid rgba(255,255,255,0.04)",
            borderRadius: "6px",
            padding: "8px 12px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <span style={{ fontWeight: "bold", color: "#fff" }}>
              {rule.rule_id}: {rule.name}
            </span>
            <span
              style={{
                background: "rgba(16, 185, 129, 0.15)",
                color: "#10b981",
                border: "1px solid rgba(16, 185, 129, 0.25)",
                borderRadius: "4px",
                padding: "1px 6px",
                fontSize: "8px",
                fontWeight: "bold"
              }}
            >
              ENABLED
            </span>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: "10px", lineHeight: "1.3" }}>
            {rule.description}
          </div>
          <div style={{ display: "flex", gap: "10px", marginTop: "6px", fontSize: "9px", fontFamily: "monospace", color: "#38bdf8" }}>
            <span>intent: {rule.target_intent}</span>
            <span>rollback: {rule.requires_rollback ? "YES" : "NO"}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
