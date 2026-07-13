import React from "react";

type Props = {
  approverRole: "approver" | "admin";
  reason?: string;
  onSign?: (operatorName: string) => void;
};

export const ApprovalRequirementPanel: React.FC<Props> = ({ approverRole, reason, onSign }) => {
  const [signer, setSigner] = React.useState("");

  const handleSign = (e: React.FormEvent) => {
    e.preventDefault();
    if (signer.trim() && onSign) {
      onSign(signer.trim());
      setSigner("");
    }
  };

  return (
    <div
      style={{
        background: "rgba(129, 140, 248, 0.06)",
        border: "1px solid rgba(129, 140, 248, 0.2)",
        borderRadius: "6px",
        padding: "10px",
        fontSize: "11px",
        textAlign: "left",
        color: "#cbd5e1"
      }}
    >
      <div style={{ color: "#818cf8", fontWeight: "bold", marginBottom: "4px" }}>
        🔐 ELEVATED APPROVAL GATEWAY
      </div>
      {reason && <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginBottom: "8px" }}>{reason}</div>}
      
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <span>Required Role Authority:</span>
        <span
          style={{
            background: "rgba(129, 140, 248, 0.15)",
            color: "#818cf8",
            border: "1px solid rgba(129, 140, 248, 0.3)",
            borderRadius: "4px",
            padding: "1px 6px",
            fontWeight: "bold",
            fontSize: "9px",
            textTransform: "uppercase"
          }}
        >
          {approverRole}
        </span>
      </div>

      {onSign && (
        <form onSubmit={handleSign} style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
          <input
            type="text"
            placeholder="Operator signature name..."
            value={signer}
            onChange={(e) => setSigner(e.target.value)}
            style={{
              flexGrow: 1,
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              padding: "4px 8px",
              color: "#fff",
              fontSize: "11px",
              outline: "none"
            }}
          />
          <button
            type="submit"
            style={{
              background: "#818cf8",
              border: "none",
              color: "#0b0f19",
              fontWeight: "bold",
              borderRadius: "4px",
              padding: "4px 10px",
              fontSize: "11px",
              cursor: "pointer"
            }}
          >
            Sign Approval
          </button>
        </form>
      )}
    </div>
  );
};
