import React from "react";

type Props = {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
};

export const OverrideJustificationModal: React.FC<Props> = ({ onConfirm, onCancel }) => {
  const [reason, setReason] = React.useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim()) {
      onConfirm(reason.trim());
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(11, 15, 25, 0.7)",
        backdropFilter: "blur(4px)",
        zIndex: 1100,
        display: "flex",
        justifyContent: "center",
        alignItems: "center"
      }}
    >
      <div
        style={{
          width: "400px",
          background: "rgba(22, 28, 45, 0.95)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
          boxShadow: "0 10px 30px rgba(239, 68, 68, 0.15)",
          borderRadius: "8px",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          color: "#fff",
          textAlign: "left"
        }}
      >
        <div style={{ color: "#ef4444", fontWeight: "bold", fontSize: "13px" }}>
          ⚠️ SECURITY BYPASS: OPERATOR OVERRIDE
        </div>
        <p style={{ margin: 0, fontSize: "11px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
          You are about to override a security block. This emergency bypass requires a documented justification, which will be logged in the immutable audit trail.
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <textarea
            placeholder="Document override justification here..."
            required
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "6px",
              padding: "8px",
              color: "#fff",
              fontSize: "11px",
              outline: "none",
              resize: "none"
            }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
            <button
              type="button"
              onClick={onCancel}
              style={{
                background: "transparent",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff",
                borderRadius: "4px",
                padding: "6px 12px",
                fontSize: "11px",
                cursor: "pointer"
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={{
                background: "#ef4444",
                border: "none",
                color: "#fff",
                borderRadius: "4px",
                padding: "6px 16px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer"
              }}
            >
              Confirm Override
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
