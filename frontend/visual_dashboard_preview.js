// Sandboxed read-only preview.

const FIXTURES = {
  "cockpit_healthy": {
    "truth": "LIVE",
    "generated_at": "2026-06-27T18:00:00Z",
    "cards": {
      "runtime_process": { "truth": "LIVE" },
      "approval_gate": { "state": "LIVE", "pending_count": 0 }
    }
  },
  "cockpit_missing": null,
  "cockpit_stale": {
    "truth": "LIVE",
    "generated_at": "2026-06-27T12:00:00Z",
    "cards": {
      "runtime_process": { "truth": "LIVE" }
    }
  },
  "prompt_registry_103": {
    "prompts": [
      { "id": "P1", "title": "Lead Dev" }
    ],
    "count": 103,
    "timestamp": "2026-06-27T18:00:00Z"
  },
  "prompt_registry_missing": null,
  "known_assets_9_devices": {
    "timestamp": "2026-06-27T18:00:00Z",
    "devices": [
      { "id": "d1", "ip": "10.0.0.6", "name": "command-node", "active": true }
    ],
    "count": 9
  },
  "approval_queue_pending": {
    "approvals": [
      {
        "approval_id": "app-12345",
        "status": "PENDING",
        "task_description": "Deploy code to cluster",
        "risk_level": "HIGH",
        "human_approval_required": true
      }
    ]
  },
  "approval_queue_fail_closed": {
    "approvals": [
      {
        "approval_id": "app-67890",
        "status": "FAIL_CLOSED",
        "task_description": "Unauthorized bypass attempt",
        "risk_level": "FAIL_CLOSED",
        "human_approval_required": true
      }
    ]
  },
  "evidence_manifest_present": {
    "release": "0.1.6-ERROR-BUDGET-AWARE-AUTONOMY",
    "artifacts": [
      { "path": "mission.json", "sha256": "abc123xyz" }
    ]
  },
  "evidence_manifest_missing": null,
  "prompt_router_plan_approval": {
    "task_description": "Publish release code",
    "route_plan": {
      "mission_type": "RELEASE",
      "risk_level": "HIGH",
      "human_approval_required": true
    }
  },
  "prompt_router_fail_closed": {
    "task_description": "Force delete models",
    "route_plan": {
      "mission_type": "ADMIN",
      "risk_level": "FAIL_CLOSED",
      "human_approval_required": true
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const adapters = window.visualAdapters;
  if (!adapters) {
    console.error("visualAdapters script not loaded.");
    return;
  }

  // 1. Render Section Rail Sidebar
  const railContainer = document.getElementById("section-rail-container");
  if (railContainer) {
    railContainer.innerHTML = `
      <div class="section-rail" style="width: 100%;">
        <a href="#ops-header-container" class="active">OPS BAR HEADER</a>
        <a href="#metric-strip-container">METRICS STRIP</a>
        <a href="#telemetry-cards-container">TELEMETRY CARDS</a>
        <a href="#approval-queue-container">APPROVAL GATE</a>
        <a href="#evidence-manifest-container">EVIDENCE INDEX</a>
        <a href="#state-registry-container">STATE REGISTRY</a>
        <a href="#terminal-panel-container">TERMINAL CONSOLE</a>
      </div>
    `;
  }

  // 2. Render Ops Header Component
  const opsHeaderContainer = document.getElementById("ops-header-container");
  if (opsHeaderContainer) {
    const vm = adapters.adaptCockpitTelemetry(FIXTURES.cockpit_healthy);
    opsHeaderContainer.innerHTML = `
      <header class="global-ops-bar" style="margin-bottom: 0;">
        <h1>HOCH SWARM COCKPIT [PREVIEW]</h1>
        <div class="breadcrumbs">
          <span>SOURCE: ${vm.source}</span>
        </div>
        <span class="status-badge status-${vm.state.toLowerCase()}">${vm.state}</span>
      </header>
    `;
  }

  // 3. Render Metric Strip Component
  const metricStripContainer = document.getElementById("metric-strip-container");
  if (metricStripContainer) {
    const vm = adapters.adaptMetricStrip({ "Sync Status": "ONLINE", "Active Devices": 9, "Detections": 0 });
    metricStripContainer.innerHTML = `
      <div class="metric-strip">
        ${Object.entries(vm.metrics).map(([k, v]) => `
          <div>
            <div style="font-size: 11px; color: var(--text-muted);">${k}</div>
            <div style="font-size: 14px; font-weight: bold; color: ${k === 'Sync Status' ? 'var(--accent-green)' : 'var(--text-primary)'};">${v}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  // 4. Render Telemetry Cards Grid
  const telemetryContainer = document.getElementById("telemetry-cards-container");
  if (telemetryContainer) {
    // Generate various state card mockups driven by adapters
    const healthyCockpit = adapters.adaptCockpitTelemetry(FIXTURES.cockpit_healthy);
    const staleCockpit = adapters.adaptCockpitTelemetry(FIXTURES.cockpit_stale);
    const missingCockpit = adapters.adaptCockpitTelemetry(FIXTURES.cockpit_missing);
    
    const registry103 = adapters.adaptPromptRegistry(FIXTURES.prompt_registry_103);
    const registryMissing = adapters.adaptPromptRegistry(FIXTURES.prompt_registry_missing);
    
    const assets9 = adapters.adaptKnownAssets(FIXTURES.known_assets_9_devices);
    const assetsMissing = adapters.adaptKnownAssets(null);

    const routerPlanApproval = adapters.adaptPromptRouterPlan(FIXTURES.prompt_router_plan_approval);
    const routerFailClosed = adapters.adaptPromptRouterPlan(FIXTURES.prompt_router_fail_closed);

    const cardsHTML = [
      renderCardHTML("SIEM Event Bus (Healthy)", healthyCockpit),
      renderCardHTML("SIEM Event Bus (Stale)", staleCockpit),
      renderCardHTML("SIEM Event Bus (Missing)", missingCockpit),
      renderCardHTML("Prompt Registry (Active)", registry103),
      renderCardHTML("Prompt Registry (Unavailable)", registryMissing),
      renderCardHTML("Asset Mesh Map (Topography)", assets9),
      renderCardHTML("Asset Mesh Map (Unavailable)", assetsMissing),
      renderCardHTML("Router Plan (Risk Badge)", routerPlanApproval),
      renderCardHTML("Router Plan (Fail-Closed)", routerFailClosed)
    ].join('');
    
    telemetryContainer.innerHTML = cardsHTML;
  }

  // 5. Render Approval Queue Components
  const approvalContainer = document.getElementById("approval-queue-container");
  if (approvalContainer) {
    const pendingQueue = adapters.adaptApprovalQueue(FIXTURES.approval_queue_pending);
    const failClosedQueue = adapters.adaptApprovalQueue(FIXTURES.approval_queue_fail_closed);

    approvalContainer.innerHTML = `
      <div class="approval-card" style="border-top: 3px solid var(--accent-cyan);">
        <div class="agent-header">
          <h4>Deploy code to cluster</h4>
          <span class="status-badge status-${pendingQueue.state.toLowerCase()}">${pendingQueue.state}</span>
        </div>
        <p style="font-size: 13px; margin-bottom: var(--space-sm); color: var(--text-secondary);">Action: Deploy mockup assets to Macbook Pro node</p>
        <div style="display: flex; gap: 8px;">
          <button disabled style="background: var(--text-muted); color: var(--text-secondary); border: none; padding: 4px 8px; border-radius: 4px; cursor: not-allowed; font-weight: bold;">APPROVE (VISUAL ONLY)</button>
          <button disabled style="background: var(--text-muted); color: var(--text-secondary); border: none; padding: 4px 8px; border-radius: 4px; cursor: not-allowed; font-weight: bold;">DENY (VISUAL ONLY)</button>
        </div>
        <div class="meta-label-block">
          <div><span style="color: var(--text-muted);">Source:</span> ${pendingQueue.source}</div>
          <div><span style="color: var(--text-muted);">Evidence:</span> ${pendingQueue.evidence.present ? 'PASSED' : 'MISSING'}</div>
        </div>
      </div>

      <div class="approval-card fail-closed" style="border-top: 3px solid var(--accent-red);">
        <div class="agent-header">
          <h4>Unauthorized bypass attempt</h4>
          <span class="status-badge status-${failClosedQueue.state.toLowerCase()}">${failClosedQueue.state}</span>
        </div>
        <p style="font-size: 13px; margin-bottom: var(--space-sm); color: var(--accent-red);">BLOCKED: Attempt to bypass operator signature matches fail-closed policy.</p>
        <button disabled style="background: var(--text-muted); color: var(--text-secondary); border: none; padding: 4px 8px; border-radius: 4px; cursor: not-allowed;">ACTION BLOCKED</button>
        <div class="meta-label-block">
          <div><span style="color: var(--text-muted);">Source:</span> ${failClosedQueue.source}</div>
          <div><span style="color: var(--text-muted);">Fail Closed:</span> TRUE</div>
        </div>
      </div>
    `;
  }

  // 6. Render Evidence Manifest Components
  const evidenceContainer = document.getElementById("evidence-manifest-container");
  if (evidenceContainer) {
    const presentEv = adapters.adaptEvidenceManifest(FIXTURES.evidence_manifest_present);
    const missingEv = adapters.adaptEvidenceManifest(FIXTURES.evidence_manifest_missing);

    evidenceContainer.innerHTML = `
      ${renderCardHTML("Verification Attestation (SBOM Present)", presentEv)}
      ${renderCardHTML("Verification Attestation (SBOM Missing)", missingEv)}
    `;
  }

  // 7. Render State Registry Definition
  const stateRegistryContainer = document.getElementById("state-registry-container");
  if (stateRegistryContainer) {
    stateRegistryContainer.innerHTML = `
      <div class="card" style="border-top: 3px solid var(--accent-cyan);">
        <h3>Dashboard State Registry <span class="status-badge status-simulated">SAMPLE</span></h3>
        <div class="card-body">
          <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">
            Recognized visual status labels and CSS states mapping:
          </p>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <span class="status-badge status-live">LIVE</span>
            <span class="status-badge status-degraded">DEGRADED</span>
            <span class="status-badge status-pending">PENDING</span>
            <span class="status-badge status-simulated">SIMULATED</span>
            <span class="status-badge status-stale">STALE</span>
            <span class="status-badge status-fail-closed">FAIL-CLOSED</span>
            <span class="status-badge status-unavailable">UNAVAILABLE</span>
            <span class="status-badge status-unknown">UNKNOWN</span>
          </div>
        </div>
      </div>
    `;
  }

  // 8. Render Terminal logs output panel
  const terminalPanelContainer = document.getElementById("terminal-panel-container");
  if (terminalPanelContainer) {
    terminalPanelContainer.innerHTML = `
      <div class="terminal-panel" style="font-family: var(--font-mono); font-size: 12px;">
        <div>[2026-06-27T18:00:00.000Z] INFO: Initializing Visual Control Plane Preview...</div>
        <div>[2026-06-27T18:00:00.050Z] PASS: Loaded visual_adapters.js data adapters successfully.</div>
        <div style="color: var(--accent-cyan);">[2026-06-27T18:00:00.120Z] PREVIEW: Sandbox environment active. Real-time control bindings are BLOCKED.</div>
      </div>
    `;
  }
});

function renderCardHTML(title, vm) {
  const badgeClass = `status-${vm.state.toLowerCase()}`;
  const evidencePresent = vm.evidence.present ? "PASSED" : "MISSING";
  const evidenceClass = vm.evidence.present ? "color: var(--accent-green)" : "color: var(--accent-red)";
  
  let approvalHTML = '';
  if (vm.approval.required) {
    approvalHTML = `
      <div style="margin-top: 8px; padding: 4px; border: 1px solid var(--accent-red); background: rgba(220, 53, 69, 0.05); font-size: 11px; border-radius: 2px;">
        <span style="color: var(--accent-red); font-weight: bold;">⚠️ APPROVAL REQUIRED:</span> ${vm.approval.reason}
      </div>
    `;
  }

  let failClosedHTML = '';
  if (vm.fail_closed_triggers && vm.fail_closed_triggers.length > 0) {
    failClosedHTML = `
      <div style="margin-top: 8px; padding: 4px; border: 1px solid var(--accent-red); background: rgba(220, 53, 69, 0.1); font-size: 11px; border-radius: 2px; color: var(--accent-red); font-weight: bold;">
        🚨 FAIL-CLOSED ACTIVE: ${vm.fail_closed_triggers.join(', ')}
      </div>
    `;
  }

  const isFailClosed = vm.state === 'FAIL-CLOSED';
  const cardStyle = isFailClosed
    ? 'border: 2px solid var(--accent-red); background: rgba(239, 68, 68, 0.05); shadow: 0 0 10px rgba(239, 68, 68, 0.2);'
    : 'border-top: 3px solid var(--border-subtle);';

  return `
    <div class="card" style="${cardStyle}">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-xs);">
        <h3 style="margin: 0; font-size: 14px;">${title}</h3>
        <span class="status-badge ${badgeClass}">${vm.state}</span>
      </div>
      <div class="card-body">
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: var(--space-sm);">${vm.summary}</p>
        <div style="font-size: 12px; font-family: var(--font-mono); display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
          ${Object.entries(vm.metrics).map(([k, v]) => `
            <div><span style="color: var(--text-muted); font-weight: 600;">${k}:</span> ${typeof v === 'object' ? JSON.stringify(v) : v}</div>
          `).join('')}
        </div>
        ${approvalHTML}
        ${failClosedHTML}
      </div>
      <div class="meta-label-block">
        <div><span style="color: var(--accent-cyan); font-weight: bold;">[SRC] Source:</span> ${vm.source}</div>
        <div><span style="color: ${vm.freshness.fresh ? 'var(--accent-green)' : 'var(--accent-amber)'}; font-weight: bold;">[TIME] Freshness:</span> ${vm.freshness.timestamp ? (vm.freshness.fresh ? "FRESH" : "STALE") : "UNKNOWN"}</div>
        <div><span style="${evidenceClass}; font-weight: bold;">[EVID] Evidence:</span> ${evidencePresent} (${vm.evidence.paths.join(', ') || 'none'})</div>
      </div>
    </div>
  `;
}
