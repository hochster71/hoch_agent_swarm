import React from "react";
import { useCommandStore } from "../../lib/command/commandStore";
import { CommandModeSelector } from "./CommandModeSelector";
import { CommandRiskBadge } from "./CommandRiskBadge";
import { CommandImpactPanel } from "./CommandImpactPanel";
import { CommandPolicyPanel } from "./CommandPolicyPanel";
import { CommandRollbackPanel } from "./CommandRollbackPanel";
import { logSimulation, logExecution } from "../../lib/command/commandExecution";
import { ShieldAlert, X, AlertOctagon } from "lucide-react";
import { useZtaPostureStore } from "../../lib/policy/ztaPosture";
import { evaluatePolicy } from "../../lib/policy/policyEngine";
import { useApprovalStore } from "../../lib/collab/approvalStore";
import { createApproval } from "../../lib/api/approvalApi";
import { useAuditStore } from "../../lib/audit/auditStore";
import { createAuditEvent } from "../../lib/audit/auditEvents";

export const CommandPreviewModal: React.FC = () => {
  const { preview, isOpen, selectedMode, closePreview, setMode } = useCommandStore();
  const { identity, device_posture, network_trust, session_integrity, environment } = useZtaPostureStore();
  const { addRequest } = useApprovalStore();
  const addEvent = useAuditStore((state) => state.addEvent);

  if (!isOpen || !preview) return null;

  // Run real-time ZTA policy evaluation
  const evaluation = evaluatePolicy({
    actor: {
      id: "michael.hoch",
      name: "Michael Hoch",
      role: "operator",
    },
    command: {
      command_id: preview.command_id,
      raw_text: preview.parsed.raw_text,
      intent: preview.parsed.intent,
      risk: preview.risk,
    },
    target: {
      id: preview.parsed.affected_assets[0]?.id || "system",
      name: preview.parsed.affected_assets[0]?.name || "System",
      type: "system",
    },
    environment: environment,
    zta: {
      identity,
      device_posture,
      network_trust,
      session_integrity,
    },
    rollback: {
      available: preview.rollback.available,
    },
  });

  const hasFailedZta =
    identity === "failed" ||
    device_posture === "failed" ||
    network_trust === "failed" ||
    session_integrity === "failed";

  const isBlocked = evaluation.decision === "block" || hasFailedZta;
  const isOverrideActive = selectedMode === "override";
  const canDispatch = (!isBlocked || isOverrideActive) && !hasFailedZta;

  const handleCancel = () => {
    closePreview();
  };

  const handleConfirm = async () => {
    const taskTypeSelect = document.getElementById("task-type-select") as HTMLSelectElement;
    const taskType = taskTypeSelect ? taskTypeSelect.value : "general_query";

    if (hasFailedZta) {
      alert("⚠️ ACCESS COMPROMISED: Swarm node execution blocked due to failed Zero Trust parameters.");
      return;
    }

    // Intercept execute mode if approval is required
    if (selectedMode === "execute" && evaluation.approval_required) {
      const approvalId = `app-${Math.random().toString(36).substr(2, 9)}`;
      const approvalReq = {
        approval_id: approvalId,
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 60 * 60000).toISOString(),
        status: "pending" as const,
        requested_by: {
          id: "op-3",
          name: "Michael Hoch",
          role: "operator",
        },
        required_approver_role: preview.risk === "critical" ? ("admin" as const) : ("approver" as const),
        command: {
          command_id: preview.command_id,
          correlation_id: preview.correlation_id,
          raw_text: preview.parsed.raw_text,
          risk: preview.risk,
        },
        target: {
          id: preview.parsed.affected_assets[0]?.id || "system",
          name: preview.parsed.affected_assets[0]?.name || "System",
          type: "asset",
        },
        policy_context: {
          decision: evaluation.decision,
          approval_reason: evaluation.approval_reason || "ZTA Guardrail triggered.",
          blockers: evaluation.blockers,
          warnings: evaluation.warnings,
        },
        decisions: [],
      };

      // Add to local store and attempt to push to backend
      addRequest(approvalReq);
      try {
        await createApproval(approvalReq);
      } catch (err) {
        console.error("Backend approval registration failed:", err);
      }

      // Log audit event for block
      addEvent(
        createAuditEvent({
          actor: {
            id: "michael.hoch",
            name: "Michael Hoch",
            type: "human",
            role: "Operator",
          },
          action: {
            type: "COMMAND_BLOCKED",
            summary: `Command blocked by ZTA guardrails. Rerouted to approval queue: ${preview.parsed.raw_text}`,
          },
          target: {
            type: "system",
            id: preview.command_id,
            name: "Command Execution Filter",
          },
          result: "failed",
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

      alert("🛡️ DUAL SIGN-OFF REQUIRED:\nCommand requires authorization. Request routed to Collaboration Hub.");
      closePreview();
      return;
    }

    closePreview();

    const modeLabel =
      selectedMode === "simulate"
        ? "Simulate"
        : selectedMode === "execute"
        ? "Execute"
        : "Emergency Override";

    // Trigger simulation or execution logging
    if (selectedMode === "simulate") {
      logSimulation(preview);
    } else {
      const isOverride = selectedMode === "override";
      logExecution(preview, true, isOverride);
    }

    // Call global dispatch handler to route backend task and spawn particles
    if (window.executeTaskWithMode) {
      await window.executeTaskWithMode(preview.parsed.raw_text, taskType, modeLabel);
    } else {
      console.warn("window.executeTaskWithMode is not bound. Falling back to local dispatch.");
    }
  };

  // Determine affected enclave
  let enclaveText = "SIPRNET (TACTICAL COMPUTE)";
  if (preview.parsed.affected_assets.length > 0) {
    const asset = preview.parsed.affected_assets[0];
    if (asset.id === "L1") {
      enclaveText = "NIPRNET (CORE SERVICES)";
    } else if (asset.id === "IPAD" || asset.id === "IPHONE") {
      enclaveText = "JWICS (MOBILE EDGE)";
    }
  }

  return (
    <div className="modal-overlay" style={{ zIndex: 1000, display: "flex" }}>
      <div
        className="modal-content card"
        style={{
          maxWidth: "500px",
          padding: "18px",
          background: "rgba(10, 15, 28, 0.95)",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--border-glass)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}
      >
        <div
          className="modal-header"
          style={{
            borderBottom: "1px solid var(--border-glass)",
            paddingBottom: "8px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div className="modal-header-left" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <ShieldAlert style={{ color: "var(--accent-orange)", width: "16px", height: "16px" }} />
            <h2 className="modal-title" style={{ fontSize: "13px", fontWeight: "bold", letterSpacing: "0.5px" }}>
              TACTICAL COMMAND VERIFICATION
            </h2>
          </div>
          <button
            className="icon-btn close-btn"
            onClick={handleCancel}
            aria-label="Cancel command"
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}
          >
            <X style={{ width: "16px", height: "16px" }} />
          </button>
        </div>

        <div
          className="modal-body"
          style={{
            marginTop: "14px",
            fontFamily: "monospace",
            fontSize: "11px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            textAlign: "left",
          }}
        >
          <div>
            <span style={{ color: "var(--text-secondary)", display: "block", marginBottom: "4px", fontSize: "9.5px", fontWeight: "bold" }}>
              COMMAND INSTRUCTION PREVIEW
            </span>
            <div
              style={{
                background: "rgba(0,0,0,0.5)",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.06)",
                color: "#fff",
                wordBreak: "break-all",
                fontSize: "11px",
                maxHeight: "80px",
                overflowY: "auto",
              }}
            >
              {preview.parsed.raw_text}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
            <div>
              <span style={{ color: "var(--text-secondary)", display: "block", marginBottom: "2px", fontSize: "9.5px", fontWeight: "bold" }}>
                AFFECTED ENCLAVE
              </span>
              <span style={{ color: "#fff", fontWeight: "bold" }}>{enclaveText}</span>
            </div>
            <div>
              <span style={{ color: "var(--text-secondary)", display: "block", marginBottom: "2px", fontSize: "9.5px", fontWeight: "bold" }}>
                ZTA COMPLIANCE RISK
              </span>
              <div style={{ display: "inline-flex", marginTop: "2px" }}>
                <CommandRiskBadge risk={preview.risk} />
              </div>
            </div>
          </div>

          <div>
            <span style={{ color: "var(--text-secondary)", display: "block", marginBottom: "2px", fontSize: "9.5px", fontWeight: "bold" }}>
              AFFECTED ASSETS
            </span>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "2px" }}>
              {preview.parsed.affected_assets.map((asset) => (
                <span
                  key={asset.id}
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    color: "var(--accent-teal)",
                    fontSize: "10px",
                    fontWeight: "bold",
                  }}
                >
                  {asset.name} ({asset.id})
                </span>
              ))}
              {preview.parsed.affected_assets.length === 0 && (
                <span style={{ color: "var(--text-secondary)", fontStyle: "italic" }}>None resolved</span>
              )}
            </div>
          </div>

          <CommandPolicyPanel policy={preview.policy} />
          <CommandImpactPanel impact={preview.impact} />
          <CommandRollbackPanel rollback={preview.rollback} />
          <CommandModeSelector selectedMode={selectedMode} onChange={setMode} />

          {/* Block Warnings */}
          {hasFailedZta && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                padding: "8px 10px",
                borderRadius: "6px",
                color: "#f87171",
                fontSize: "9.5px",
                lineHeight: "1.4",
              }}
            >
              <div className="flex items-start gap-1.5 font-bold">
                <AlertOctagon className="h-4 w-4 shrink-0 text-rose-500" />
                <span>ZERO TRUST SYSTEM COMPROMISE:</span>
              </div>
              <p className="mt-1 leading-normal">
                Critical device posture, identity, or session checks failed. All commands are strictly blocked.
              </p>
            </div>
          )}

          {!hasFailedZta && isBlocked && !isOverrideActive && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                padding: "8px 10px",
                borderRadius: "6px",
                color: "#f87171",
                fontSize: "9.5px",
                lineHeight: "1.4",
              }}
            >
              <strong>⚠️ COMMAND BLOCKED:</strong> {preview.blockers.join(" ")} Select <strong>OVERRIDE</strong> to
              force emergency dispatch.
            </div>
          )}

          {!hasFailedZta && isOverrideActive && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                padding: "8px 10px",
                borderRadius: "6px",
                color: "#f87171",
                fontSize: "9.5px",
                lineHeight: "1.4",
              }}
            >
              <strong>⚠️ EMERGENCY OVERRIDE ACTIVE:</strong> Bypassing policy filters. This action will be flagged
              in ZTA Audit reports.
            </div>
          )}

          <div
            style={{
              background: "rgba(234, 179, 8, 0.04)",
              border: "1px solid rgba(234, 179, 8, 0.15)",
              padding: "6px 8px",
              borderRadius: "6px",
              color: "#fbbf24",
              fontSize: "9px",
              lineHeight: "1.3",
            }}
          >
            <strong>ℹ️ GOVERNANCE NOTICE:</strong> Actions are authenticated and logged. ZTA Correlation ID:{" "}
            <code>{preview.correlation_id}</code>.
          </div>

          <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
            <button
              className="btn btn-outline"
              style={{ flex: 1, height: "32px", fontSize: "11px", cursor: "pointer" }}
              onClick={handleCancel}
            >
              CANCEL
            </button>
            <button
              className="btn btn-primary"
              style={{
                flex: 1,
                height: "32px",
                fontSize: "11px",
                cursor: canDispatch ? "pointer" : "not-allowed",
                background: canDispatch
                  ? selectedMode === "override"
                    ? "#ef4444"
                    : "var(--accent-teal)"
                  : "rgba(255,255,255,0.05)",
                border: canDispatch
                  ? selectedMode === "override"
                    ? "1px solid #ef4444"
                    : "1px solid var(--accent-teal)"
                  : "1px solid rgba(255,255,255,0.08)",
                color: canDispatch ? "#fff" : "var(--text-secondary)",
                fontWeight: "bold",
              }}
              disabled={!canDispatch}
              onClick={handleConfirm}
            >
              {selectedMode === "simulate" ? "CONFIRM SIMULATION" : "CONFIRM DISPATCH"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

