import React from "react";
import { useZtaPostureStore } from "../../lib/policy/ztaPosture";
import { evaluatePolicy } from "../../lib/policy/policyEngine";
import { ZtaPosturePanel } from "./ZtaPosturePanel";
import { PolicyDecisionCard } from "./PolicyDecisionCard";
import { GuardrailStatusList } from "./GuardrailStatusList";
import { PolicyViolationList } from "./PolicyViolationList";
import type { Environment, ZtaStatus } from "../../lib/policy/policyTypes";

export const PolicyDashboard: React.FC = () => {
  const ztaState = useZtaPostureStore();

  // Simulated active query evaluation
  const activeEvaluationInput = React.useMemo(() => {
    return {
      actor: {
        id: "michael.hoch",
        name: "Michael Hoch",
        role: "operator" as const,
      },
      command: {
        command_id: "cmd_active_eval",
        raw_text: "rebalance workload from Michael's iMac to Dell 9440",
        intent: "rebalance_workload",
        risk: "medium" as const,
      },
      target: {
        id: "asset-imac",
        name: "Michael's iMac",
        type: "asset" as const,
        trust_score: 92,
      },
      environment: ztaState.environment,
      zta: {
        identity: ztaState.identity,
        device_posture: ztaState.device_posture,
        network_trust: ztaState.network_trust,
        session_integrity: ztaState.session_integrity,
      },
      rollback: {
        available: true,
      },
    };
  }, [ztaState]);

  const activeResult = React.useMemo(() => {
    return evaluatePolicy(activeEvaluationInput);
  }, [activeEvaluationInput]);

  return (
    <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px", height: "100%", overflowY: "auto", boxSizing: "border-box" }}>
      {/* Title Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "10px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "16px", fontWeight: "bold", color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
            🛡️ POLICY ENFORCEMENT & ZTA GUARDRAILS
          </h1>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginTop: "4px" }}>
            Real-time policy decision logs and cryptographic Zero Trust enclaves posture checks.
          </span>
        </div>
        
        {/* Environment Switcher */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px" }}>
          <span style={{ color: "var(--text-secondary)" }}>Environment:</span>
          <select
            value={ztaState.environment}
            onChange={(e) => ztaState.setEnvironment(e.target.value as Environment)}
            style={{
              background: "rgba(0,0,0,0.3)",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: "4px",
              padding: "4px 8px",
              color: "#fff",
              cursor: "pointer",
              outline: "none"
            }}
          >
            <option value="LOCAL">LOCAL</option>
            <option value="DEV">DEV</option>
            <option value="STAGING">STAGING</option>
            <option value="PROD">PROD</option>
          </select>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        
        {/* Left Side Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Posture Panel with Interactive Toggles */}
          <div className="card" style={{ padding: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h2 className="card-title" style={{ fontSize: "12px", margin: 0 }}>ZERO TRUST POSTURE PILLARS</h2>
              <button
                onClick={ztaState.resetPosture}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "4px",
                  fontSize: "9px",
                  padding: "2px 8px",
                  color: "#fff",
                  cursor: "pointer"
                }}
              >
                Reset Verifications
              </button>
            </div>
            
            <ZtaPosturePanel posture={ztaState} />
            
            {/* Toggles to change statuses for testing */}
            <div style={{ marginTop: "12px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "10px", textAlign: "left" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <label style={{ color: "var(--text-secondary)" }}>Identity Status</label>
                <select
                  value={ztaState.identity}
                  onChange={(e) => ztaState.setIdentity(e.target.value as ZtaStatus)}
                  style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "2px", borderRadius: "4px" }}
                >
                  <option value="verified">verified</option>
                  <option value="warning">warning</option>
                  <option value="failed">failed</option>
                </select>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <label style={{ color: "var(--text-secondary)" }}>Device Posture</label>
                <select
                  value={ztaState.device_posture}
                  onChange={(e) => ztaState.setDevicePosture(e.target.value as ZtaStatus)}
                  style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "2px", borderRadius: "4px" }}
                >
                  <option value="verified">verified</option>
                  <option value="warning">warning</option>
                  <option value="failed">failed</option>
                </select>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <label style={{ color: "var(--text-secondary)" }}>Network Trust</label>
                <select
                  value={ztaState.network_trust}
                  onChange={(e) => ztaState.setNetworkTrust(e.target.value as ZtaStatus)}
                  style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "2px", borderRadius: "4px" }}
                >
                  <option value="verified">verified</option>
                  <option value="warning">warning</option>
                  <option value="failed">failed</option>
                </select>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <label style={{ color: "var(--text-secondary)" }}>Session Integrity</label>
                <select
                  value={ztaState.session_integrity}
                  onChange={(e) => ztaState.setSessionIntegrity(e.target.value as ZtaStatus)}
                  style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", padding: "2px", borderRadius: "4px" }}
                >
                  <option value="verified">verified</option>
                  <option value="warning">warning</option>
                  <option value="failed">failed</option>
                </select>
              </div>
            </div>
          </div>

          {/* Active Guardrails */}
          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "10px" }}>ACTIVE COMPLIANCE GUARDRAILS</h2>
            <GuardrailStatusList />
          </div>
        </div>

        {/* Right Side Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Simulated Decision Card */}
          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "10px" }}>LIVE DECISION TELEMETRY EVALUATOR</h2>
            <PolicyDecisionCard result={activeResult} />
          </div>

          {/* Violations List */}
          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "10px" }}>VIOLATIONS & BLOCKS (LAST 24 HOURS)</h2>
            <PolicyViolationList />
          </div>
        </div>

      </div>
    </div>
  );
};
