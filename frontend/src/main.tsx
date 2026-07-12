import React from "react";
import ReactDOM from "react-dom/client";
import { AuditHeaderButton } from "./components/audit/AuditHeaderButton";
import { AuditDrawer } from "./components/audit/AuditDrawer";
import { CommandInput } from "./components/command/CommandInput";
import { CommandPreviewModal } from "./components/command/CommandPreviewModal";
import { AssetDrilldownPanel } from "./components/assets/AssetDrilldownPanel";

import { useAuditStore } from "./lib/audit/auditStore";
import { useAssetStore } from "./lib/assets/assetStore";
import { seedAuditEvents } from "./lib/audit/seedAuditEvents";
import { createAuditEvent } from "./lib/audit/auditEvents";

// Extend window interface
declare global {
  interface Window {
    addAuditEvent: (event: any) => void;
    updateAssetsFromLegacy: (nodes: any[]) => void;
    openModalForNodeById: (nodeId: string) => void;
    reactSelectAsset?: (nodeId: string) => void;
    executeTaskWithMode?: (prompt: string, taskType: string, mode: string) => Promise<void>;
    spawnTaskParticles?: (nodeId: string) => void;
    updateMermaidTopology?: (nodes: any[], targetId?: string) => void;
    onReplayTabActive?: () => void;
    onCollabTabActive?: () => void;
    onLedgerTabActive?: () => void;
    onGovernanceTabActive?: () => void;
    onRedTeamTabActive?: () => void;
    onExecutiveTabActive?: () => void;
    onCapabilitiesTabActive?: () => void;
    onRemediationTabActive?: () => void;
    onTenancyTabActive?: () => void;
    onComplianceTabActive?: () => void;
    onCustomerSuccessTabActive?: () => void;
    onRevenueOpsTabActive?: () => void;
    onHochsterTabActive?: () => void;
  }
}

// Seed the events exactly once
const auditState = useAuditStore.getState();
if (auditState.events.length === 0) {
  auditState.addEvents(seedAuditEvents);
}

// Expose store dispatch functions to window so legacy code can interact with React
window.addAuditEvent = (input: any) => {
  const formattedEvent = createAuditEvent(input);
  useAuditStore.getState().addEvent(formattedEvent);
};

window.updateAssetsFromLegacy = (nodes: any[]) => {
  useAssetStore.getState().updateAssetsFromLegacy(nodes);
};

window.openModalForNodeById = (nodeId: string) => {
  useAssetStore.getState().selectAsset(nodeId);
};

window.reactSelectAsset = (nodeId: string) => {
  useAssetStore.getState().selectAsset(nodeId);
};

// Mount Header Button
const headerRoot = document.getElementById("react-header-audit-root");
if (headerRoot) {
  ReactDOM.createRoot(headerRoot).render(
    <React.StrictMode>
      <AuditHeaderButton />
    </React.StrictMode>
  );
}

// Mount Audit Drawer
const drawerRoot = document.getElementById("react-audit-drawer-root");
if (drawerRoot) {
  ReactDOM.createRoot(drawerRoot).render(
    <React.StrictMode>
      <AuditDrawer />
    </React.StrictMode>
  );
}

// Mount Command Input bar at the bottom center
const commandInputRoot = document.getElementById("react-command-root");
if (commandInputRoot) {
  ReactDOM.createRoot(commandInputRoot).render(
    <React.StrictMode>
      <CommandInput />
    </React.StrictMode>
  );
}

// Mount Command Safety Preview Modal
const previewModalRoot = document.getElementById("react-command-preview-root");
if (previewModalRoot) {
  ReactDOM.createRoot(previewModalRoot).render(
    <React.StrictMode>
      <CommandPreviewModal />
    </React.StrictMode>
  );
}

// Mount Asset Detail/Drilldown drawer
const assetDrilldownRoot = document.getElementById("react-asset-drilldown-root");
if (assetDrilldownRoot) {
  ReactDOM.createRoot(assetDrilldownRoot).render(
    <React.StrictMode>
      <AssetDrilldownPanel />
    </React.StrictMode>
  );
}

// Import new dashboards
import { TimelineReplayDashboard } from "./components/replay/TimelineReplayDashboard";
import { CollaborationDashboard } from "./components/collab/CollaborationDashboard";
import { SystemDashboard } from "./components/system/SystemDashboard";
import { useLedgerStore } from "./lib/ledger/ledgerClient";

import { GovernanceControlPlane } from "./components/governance/GovernanceControlPlane";
import { RedTeamDashboard } from "./components/adversarial/RedTeamDashboard";
import { ExecutiveMissionControl } from "./components/executive/ExecutiveMissionControl";

import { CapabilityMarketplace } from "./components/capabilities/CapabilityMarketplace";
import { RemediationDashboard } from "./components/remediation/RemediationDashboard";
import { EnterpriseAdminConsole } from "./components/tenancy/EnterpriseAdminConsole";

import { ComplianceDashboard } from "./components/compliance/ComplianceDashboard";
import { CustomerSuccessDashboard } from "./components/customer-success/CustomerSuccessDashboard";
import { RevenueOpsDashboard } from "./components/revenue-ops/RevenueOpsDashboard";
import { HochsterDashboard } from "./components/hochster/HochsterDashboard";
import { OverviewControlPlane } from "./components/overview/OverviewControlPlane";
import { PertCriticalPathTab } from "./components/overview/PertCriticalPathTab";
// HochNeuroPanel removed: depends on missing helm shell modules
// (helmCouncilState, HelmApprovedPlatformShell, etc.) that are not in this checkout.
// Mount point #react-neuro-root is intentionally inert until those modules exist.

// Mount Timeline Replay Dashboard
const replayRoot = document.getElementById("react-replay-root");
if (replayRoot) {
  ReactDOM.createRoot(replayRoot).render(
    <React.StrictMode>
      <TimelineReplayDashboard />
    </React.StrictMode>
  );
}

// Mount Collaboration Dashboard
const collabRoot = document.getElementById("react-collab-root");
if (collabRoot) {
  ReactDOM.createRoot(collabRoot).render(
    <React.StrictMode>
      <CollaborationDashboard />
    </React.StrictMode>
  );
}

// Mount System Dashboard
const ledgerRoot = document.getElementById("react-ledger-root");
if (ledgerRoot) {
  ReactDOM.createRoot(ledgerRoot).render(
    <React.StrictMode>
      <SystemDashboard />
    </React.StrictMode>
  );
}

// Mount AI Governance Control Plane
const governanceRoot = document.getElementById("react-governance-root");
if (governanceRoot) {
  ReactDOM.createRoot(governanceRoot).render(
    <React.StrictMode>
      <GovernanceControlPlane />
    </React.StrictMode>
  );
}

// Mount Red-Team Dashboard
const redTeamRoot = document.getElementById("react-red-team-root");
if (redTeamRoot) {
  ReactDOM.createRoot(redTeamRoot).render(
    <React.StrictMode>
      <RedTeamDashboard />
    </React.StrictMode>
  );
}

// Mount Executive Mission Control
const executiveRoot = document.getElementById("react-executive-root");
if (executiveRoot) {
  ReactDOM.createRoot(executiveRoot).render(
    <React.StrictMode>
      <ExecutiveMissionControl />
    </React.StrictMode>
  );
}

// Mount Capability Marketplace
const capabilitiesRoot = document.getElementById("react-capabilities-root");
if (capabilitiesRoot) {
  ReactDOM.createRoot(capabilitiesRoot).render(
    <React.StrictMode>
      <CapabilityMarketplace />
    </React.StrictMode>
  );
}

// Mount Remediation Dashboard
const remediationRoot = document.getElementById("react-remediation-root");
if (remediationRoot) {
  ReactDOM.createRoot(remediationRoot).render(
    <React.StrictMode>
      <RemediationDashboard />
    </React.StrictMode>
  );
}

// Mount Enterprise Console
const tenancyRoot = document.getElementById("react-tenancy-root");
if (tenancyRoot) {
  ReactDOM.createRoot(tenancyRoot).render(
    <React.StrictMode>
      <EnterpriseAdminConsole />
    </React.StrictMode>
  );
}

// Mount Compliance Control Plane
const complianceRoot = document.getElementById("react-compliance-root");
if (complianceRoot) {
  ReactDOM.createRoot(complianceRoot).render(
    <React.StrictMode>
      <ComplianceDashboard />
    </React.StrictMode>
  );
}

// Mount Customer Success Dashboard
const customerSuccessRoot = document.getElementById("react-customer-success-root");
if (customerSuccessRoot) {
  ReactDOM.createRoot(customerSuccessRoot).render(
    <React.StrictMode>
      <CustomerSuccessDashboard />
    </React.StrictMode>
  );
}

// Mount Revenue Operations Dashboard
const revenueOpsRoot = document.getElementById("react-revenue-ops-root");
if (revenueOpsRoot) {
  ReactDOM.createRoot(revenueOpsRoot).render(
    <React.StrictMode>
      <RevenueOpsDashboard />
    </React.StrictMode>
  );
}

// Mount HOCHSTER Debugger Dashboard
const hochsterRoot = document.getElementById("react-hochster-root");
if (hochsterRoot) {
  ReactDOM.createRoot(hochsterRoot).render(
    <React.StrictMode>
      <HochsterDashboard />
    </React.StrictMode>
  );
}

// Mount canonical control-plane Overview (S2) — reads the single S1 status feed.
// Guarded: inert until index.html provides #react-overview-root.
const overviewRoot = document.getElementById("react-overview-root");
if (overviewRoot) {
  ReactDOM.createRoot(overviewRoot).render(
    <React.StrictMode>
      <OverviewControlPlane />
    </React.StrictMode>
  );
}

// Mount PERT / Critical-Path tab (S3). Guarded: inert until #react-pert-root exists.
const pertRoot = document.getElementById("react-pert-root");
if (pertRoot) {
  ReactDOM.createRoot(pertRoot).render(
    <React.StrictMode>
      <PertCriticalPathTab />
    </React.StrictMode>
  );
}

// Mount HOCH NEURO: inert until Helm shell modules are restored with fail-closed feeds.
// Do not render a mock-green neuro panel when dependencies are absent.
const neuroRoot = document.getElementById("react-neuro-root");
if (neuroRoot) {
  neuroRoot.textContent =
    "HOCH NEURO panel unavailable — Helm shell modules not present in this checkout (no simulated GO).";
}

// Register window callbacks to sync state on tab selection
window.onReplayTabActive = () => {
  console.log("Replay tab selected");
};

window.onCollabTabActive = () => {
  console.log("Collab tab selected");
};

window.onLedgerTabActive = () => {
  console.log("Ledger tab selected");
  useLedgerStore.getState().fetchBlocks();
};

window.onGovernanceTabActive = () => {
  console.log("Governance tab selected");
};

window.onRedTeamTabActive = () => {
  console.log("Red-Team tab selected");
};

window.onExecutiveTabActive = () => {
  console.log("Executive tab selected");
};

window.onCapabilitiesTabActive = () => {
  console.log("Capabilities tab selected");
};

window.onRemediationTabActive = () => {
  console.log("Remediation tab selected");
};

window.onTenancyTabActive = () => {
  console.log("Tenancy tab selected");
};

window.onComplianceTabActive = () => {
  console.log("Compliance tab selected");
};

window.onCustomerSuccessTabActive = () => {
  console.log("Customer Success tab selected");
};

window.onRevenueOpsTabActive = () => {
  console.log("Revenue Ops tab selected");
};

window.onHochsterTabActive = () => {
  console.log("HOCHSTER tab selected");
};

