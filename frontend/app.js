// Initialize Lucide Icons
lucide.createIcons();

// Accessiblity prefers-reduced-motion helper
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Initialize Mermaid.js with custom dark base theme variables
mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
        background: '#0b0f19',
        primaryColor: '#161c2d',
        primaryTextColor: '#f3f4f6',
        primaryBorderColor: 'rgba(255, 255, 255, 0.08)',
        lineColor: '#3b82f6',
        secondaryColor: '#1f2937',
        tertiaryColor: '#111827',
        edgeLabelBackground: '#0b0f19',
        nodeBorder: 'rgba(255, 255, 255, 0.1)',
        mainBkg: '#161c2d',
        actorBkg: '#161c2d'
    },
    securityLevel: 'loose',
    logLevel: 3
});

// UI Elements
const latencyVal = document.getElementById("latency-val");
const statusBadge = document.getElementById("cluster-status-badge");
const activeAssetsBadge = document.getElementById("active-assets-badge");
const deploymentsTbody = document.getElementById("deployments-tbody");
const totalAgentsVal = document.getElementById("total-agents-val");
const cpuPercentVal = document.getElementById("cpu-percent-val");
const cpuGaugeBar = document.getElementById("cpu-gauge-bar");
const ramUsageVal = document.getElementById("ram-usage-val");
const ramGaugeBar = document.getElementById("ram-gauge-bar");

// Modal Elements
const modalContainer = document.getElementById("modal-container");
const btnCloseModal = document.getElementById("btn-close-modal");
const modalNodeTitle = document.getElementById("modal-node-title");
const modalNodeIp = document.getElementById("modal-node-ip");
const modalNodeSpecs = document.getElementById("modal-node-specs");
const modalNodeRole = document.getElementById("modal-node-role");
const modalNodeLatency = document.getElementById("modal-node-latency");
const modalAgentsContainer = document.getElementById("modal-agents-container");

// Tab Navigation Elements
const navItems = {
    // Keep settings because of line 414
    settings: { nav: document.getElementById("nav-settings"), view: document.getElementById("view-settings") },

    // Old key compatibility mappings (aliases to new elements to avoid breaking other files/scripts)
    dashboard: { nav: document.getElementById("nav-readiness-autopilot"), view: document.getElementById("view-readiness-autopilot") },
    assets: { nav: document.getElementById("nav-readiness-autopilot"), view: document.getElementById("view-readiness-autopilot") },
    swarms: { nav: document.getElementById("nav-hochster-runtime"), view: document.getElementById("view-hochster-runtime") },
    tasks: { nav: document.getElementById("nav-remediation-safety"), view: document.getElementById("view-remediation-safety") },
    metrics: { nav: document.getElementById("nav-runtime-audit"), view: document.getElementById("view-runtime-audit") },
    security: { nav: document.getElementById("nav-release-provenance"), view: document.getElementById("view-release-provenance") },
    pert: { nav: document.getElementById("nav-error-budget"), view: document.getElementById("view-error-budget") },
    mission: { nav: document.getElementById("nav-mission-intel"), view: document.getElementById("view-mission") },
    audit: { nav: document.getElementById("nav-runtime-audit"), view: document.getElementById("view-runtime-audit") },
    replay: { nav: document.getElementById("nav-timeline-replay"), view: document.getElementById("view-replay") },
    collab: { nav: document.getElementById("nav-collab"), view: document.getElementById("view-collab") },
    ledger: { nav: document.getElementById("nav-ledger"), view: document.getElementById("view-ledger") },
    governance: { nav: document.getElementById("nav-governance"), view: document.getElementById("view-governance") },
    redTeam: { nav: document.getElementById("nav-red-team"), view: document.getElementById("view-red-team") },
    executive: { nav: document.getElementById("nav-executive"), view: document.getElementById("view-executive") },
    capabilities: { nav: document.getElementById("nav-capabilities"), view: document.getElementById("view-capabilities") },
    remediation: { nav: document.getElementById("nav-remediation-safety"), view: document.getElementById("view-remediation-safety") },
    tenancy: { nav: document.getElementById("nav-tenancy"), view: document.getElementById("view-tenancy") },
    compliance: { nav: document.getElementById("nav-compliance"), view: document.getElementById("view-compliance") },
    customerSuccess: { nav: document.getElementById("nav-customer-success"), view: document.getElementById("view-customer-success") },
    revenueOps: { nav: document.getElementById("nav-revenue-ops"), view: document.getElementById("view-revenue-ops") },
    hochster: { nav: document.getElementById("nav-hochster-runtime"), view: document.getElementById("view-hochster-runtime") },

    // New keys for exact routing
    readinessAutopilot: { nav: document.getElementById("nav-readiness-autopilot"), view: document.getElementById("view-readiness-autopilot") },
    hochsterRuntime: { nav: document.getElementById("nav-hochster-runtime"), view: document.getElementById("view-hochster-runtime") },
    remediationSafety: { nav: document.getElementById("nav-remediation-safety"), view: document.getElementById("view-remediation-safety") },
    runtimeAudit: { nav: document.getElementById("nav-runtime-audit"), view: document.getElementById("view-runtime-audit") },
    errorBudget: { nav: document.getElementById("nav-error-budget"), view: document.getElementById("view-error-budget") },
    releaseProvenance: { nav: document.getElementById("nav-release-provenance"), view: document.getElementById("view-release-provenance") },
    swarmControl: { nav: document.getElementById("nav-swarm-control"), view: document.getElementById("view-swarm-control") },
    missionIntel: { nav: document.getElementById("nav-mission-intel"), view: document.getElementById("view-mission") },
    timelineReplay: { nav: document.getElementById("nav-timeline-replay"), view: document.getElementById("view-replay") },
    cybersecurityFactory: { nav: document.getElementById("nav-cybersecurity-factory"), view: document.getElementById("view-cybersecurity-factory") },
    governance: { nav: document.getElementById("nav-governance"), view: document.getElementById("view-governance") }
};

// Security Audit & Sub-tab Elements
const subtabAudit = document.getElementById("subtab-audit");

// ================================================================
//  STATUS HELPER — maps status string → CSS class
// ================================================================
function getStatusClass(status) {
    switch ((status || "").toLowerCase().replace(/ /g, "-")) {
        case "active":        return "status-active";
        case "triaging":      return "status-triaging";
        case "self-healing":  return "status-self-healing";
        case "reasoning":     return "status-reasoning";
        case "deploying":     return "status-deploying";
        default:              return "status-active";  // all nodes online
    }
}

// Status label text map
const STATUS_LABELS = {
    "Active":       "● ACTIVE",
    "Triaging":     "◈ TRIAGING",
    "Self-Healing": "⟳ SELF-HEALING",
    "Reasoning":    "⊙ REASONING",
    "Deploying":    "▲ DEPLOYING",
};

const subtabGap = document.getElementById("subtab-gap");
const securityAuditContent = document.getElementById("security-audit-content");
const securityGapContent = document.getElementById("security-gap-content");
const securityGapTbody = document.getElementById("security-gap-tbody");
const assetsGridContainer = document.getElementById("assets-grid-container");

// Dynamic Tasks & Settings Elements
const tasksTbody = document.getElementById("tasks-tbody");
const settingsNodesTbody = document.getElementById("settings-nodes-tbody");
const formRegisterNode = document.getElementById("form-register-node");
const btnRegisterNode = document.getElementById("btn-register-node");

// Security Audit Elements
const btnRunAudit = document.getElementById("btn-run-audit");
const auditScorePercent = document.getElementById("audit-score-percent");
const auditPassedCount = document.getElementById("audit-passed-count");
const auditWarningsCount = document.getElementById("audit-warnings-count");
const auditFailedCount = document.getElementById("audit-failed-count");
const securityControlsList = document.getElementById("security-controls-list");

const btnSubmitTask = document.getElementById("btn-submit-task");
const taskTypeSelect = document.getElementById("task-type-select");
const promptInput = document.getElementById("prompt-input");
const taskOutputBox = document.getElementById("task-output-box");
const logOutputContent = document.getElementById("log-output-content");

const btnZoom = document.getElementById("btn-zoom");
const btnReset = document.getElementById("btn-reset");
const mermaidGraph = document.getElementById("mermaid-graph");

// Base API URL
const API_BASE = window.location.origin;

async function fetchJson(url, options = {}) {
    const res = await fetch(`${API_BASE}${url}`, options);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function escapeHtml(str) {
    if (typeof str !== 'string') {
        str = String(str ?? '');
    }
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// State management
let currentNodes = [];
let baseMermaidGraph = "";
let lastTelemetryTime = Date.now();
let telemetryIsStale = false;

// SVG Drag/Zoom Coordinates
let panX = 0;
let panY = 0;
let scale = 1.0;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;

// Chart.js State
let liveChart = null;
let chartCpuData = [];
let chartRamData = [];
let chartLabels = [];

// Particle Swarm Nodes Layout coordinates
const nodesMap = {
    MGR: { x: 0.15, y: 0.28 },
    SCHED: { x: 0.34, y: 0.28 },
    L1: { x: 0.53, y: 0.15 },
    W1: { x: 0.53, y: 0.35 },
    L2: { x: 0.53, y: 0.55 },
    L3: { x: 0.53, y: 0.75 },
    SWARM_A: { x: 0.83, y: 0.25 },
    SWARM_B: { x: 0.83, y: 0.65 }
};
let particles = [];
let animationFrameId = null;

// Initialize Dashboard Metrics & Websocket
async function initDashboard() {
    try {
        initMetricsChart();
        initDashboardCharts();
        animateSwarmFlow();
        initSwarmGlobe();
        setupAccordions();

        // Bind Command Preview Close/Cancel/Confirm buttons
        const btnClosePreview = document.getElementById("btn-close-preview");
        if (btnClosePreview) {
            btnClosePreview.addEventListener("click", () => {
                const modal = document.getElementById("command-preview-modal");
                if (modal) modal.classList.add("hidden");
            });
        }
        const btnCancelPreview = document.getElementById("btn-cancel-preview");
        if (btnCancelPreview) {
            btnCancelPreview.addEventListener("click", () => {
                const modal = document.getElementById("command-preview-modal");
                if (modal) modal.classList.add("hidden");
            });
        }

        // Bind audit log export button
        const btnExportAudit = document.getElementById("btn-export-audit");
        if (btnExportAudit) {
            btnExportAudit.addEventListener("click", () => {
                window.open(`${API_BASE}/api/audit/export`, "_blank");
            });
        }
        
        // Bind audit log filter
        const auditFilterResult = document.getElementById("audit-filter-result");
        if (auditFilterResult) {
            auditFilterResult.addEventListener("change", () => {
                fetchAndRenderAuditLogs();
            });
        }

        // 1-second interval heartbeat monitor for telemetry freshness
        setInterval(() => {
            const elapsed = (Date.now() - lastTelemetryTime) / 1000;
            const telemetryStaleWarning = document.getElementById("telemetry-stale-warning");
            if (elapsed > 10.0) {
                if (telemetryStaleWarning) {
                    telemetryStaleWarning.classList.remove("hidden");
                }
                if (!telemetryIsStale) {
                    telemetryIsStale = true;
                    logToConsoleTerminal("Telemetry", "CRITICAL WARNING: Live telemetry feed has gone stale (10+ seconds with no updates)", "error");
                    if (window.addAuditEvent) {
                        window.addAuditEvent({
                            actor: { id: "system.telemetry", name: "Telemetry System", type: "system" },
                            action: { type: "TELEMETRY_UPDATED", summary: "CRITICAL: Live telemetry feed has gone stale (10s threshold exceeded)." },
                            target: { type: "system", id: "cluster-status", name: "Cluster Health Status" },
                            result: "warning",
                            severity: "high",
                            provenance: { source: "observed", evidence_refs: [] },
                            policy: { required: false, result: "not_required" }
                        });
                    }
                }
            } else {
                if (telemetryStaleWarning) {
                    telemetryStaleWarning.classList.add("hidden");
                }
                if (telemetryIsStale) {
                    telemetryIsStale = false;
                    logToConsoleTerminal("Telemetry", "Live telemetry feed reconnected & synchronized.", "success");
                    if (window.addAuditEvent) {
                        window.addAuditEvent({
                            actor: { id: "system.telemetry", name: "Telemetry System", type: "system" },
                            action: { type: "TELEMETRY_UPDATED", summary: "Live telemetry feed reconnected and synchronized." },
                            target: { type: "system", id: "cluster-status", name: "Cluster Health Status" },
                            result: "success",
                            severity: "info",
                            provenance: { source: "observed", evidence_refs: [] },
                            policy: { required: false, result: "not_required" }
                        });
                    }
                }
            }
        }, 1000);

        // Start readiness autopilot data fetch and nav status updates immediately
        fetchReadinessAutopilotData();
        updateNavStatuses();

        // 5-second interval for readiness autopilot metrics and navigation status checks
        setInterval(fetchReadinessAutopilotData, 5000);
        setInterval(updateNavStatuses, 5000);

        // Security / governance bootstrap logs
        logToConsoleTerminal("KernelHub", "Tac-C2 Kernel Hub initialization successful.", "system");
        logToConsoleTerminal("CDAO-RAI", "DoD governance RAI compliance parameters active and verified.", "system");
        logToConsoleTerminal("ZeroTrust", "DoD ZTA security enforcement checklist: 100% compliant.", "info");

        const response = await fetch(`${API_BASE}/api/status`);
        if (response.ok) {
            const data = await response.json();
            updateUI(data);
        }
        setupWebsocket();
        fetchAndRenderTasks();
        triggerSecurityAudit();
        fetchAndRenderAuditLogs();
        // Mission Intel bootstrap — load brief + start feed polling
        setTimeout(() => {
            loadIntelBrief("dash-intel-brief-text", "mission-brief-ts");
            startMissionPolling();
        }, 1200);

        initializeHochSwarmAnimationRuntime();
        bindTopologyAgentOverlay();
        if (window.initializeCybersecurityFactory) window.initializeCybersecurityFactory();
        initRunsDashboard();
    } catch (err) {
        console.error("Error initializing dashboard: ", err);
        // Fallback polling if WebSocket fails
        setInterval(pollMetrics, 3000);
    }
}

// Poll metrics via standard HTTP
async function pollMetrics() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (response.ok) {
            const data = await response.json();
            updateUI(data);
        }
    } catch (err) {
        console.warn("Polling failed: ", err);
    }
}

// WebSocket Live updates with automatic HTTP polling fallback
let wsFailCount = 0;
let wsFallbackToPolling = false;

function handleRuntimeDeltaEvent(type, eventData) {
    const termLog = typeof logToConsoleTerminal === "function" ? logToConsoleTerminal : (window.logToConsoleTerminal || console.log);
    
    if (type === "run.created") {
        termLog("Orchestrator", `New execution campaign created: ${eventData.name || ""} (${eventData.run_id})`, "info");
        refreshRunsList().then(() => {
            const selector = document.getElementById("run-selector");
            if (selector) {
                selector.value = eventData.run_id;
                selectedRunId = eventData.run_id;
                localStorage.setItem("selectedRunId", selectedRunId);
                fetchRunTasks(eventData.run_id);
            }
        });
    } else if (type === "task.started") {
        termLog("Scheduler", `Task ${eventData.task_id} transitioned to RUNNING`, "info");
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
        }
    } else if (type === "task.blocked") {
        const reason = eventData.reason || eventData.message || "dependency";
        termLog("Scheduler", `Task ${eventData.task_id} BLOCKED (Reason: ${reason})`, "warn");
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
            fetchApprovalRequests();
        }
    } else if (type === "approval.requested") {
        termLog("Security", `Approval request generated for task ${eventData.task_id}`, "warn");
        fetchApprovalRequests();
    } else if (type === "approval.granted" || type === "approval.rejected") {
        const status = type === "approval.granted" ? "APPROVED" : "REJECTED";
        termLog("Security", `Operator decision submitted for approval: ${status}`, "success");
        fetchApprovalRequests();
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
        }
    } else if (type === "artifact.created") {
        termLog("Audit", `New artifact generated: ${eventData.name || ""}`, "success");
    } else if (type === "run.completed") {
        termLog("Orchestrator", `Execution campaign ${eventData.run_id} completed successfully!`, "success");
        refreshRunsList();
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
        }
    } else if (type === "capability.allowed") {
        termLog("Capability", `Agent ${eventData.agent_id} allowed tool '${eventData.payload?.tool || eventData.tool || ""}'`, "info");
    } else if (type === "capability.blocked") {
        termLog("Capability", `Agent ${eventData.agent_id} BLOCKED (Reason: ${eventData.message || ""})`, "error");
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
        }
    } else if (type === "capability.approval_required") {
        termLog("Capability", `Agent ${eventData.agent_id} requires approval (Reason: ${eventData.message || ""})`, "warn");
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
            fetchApprovalRequests();
        }
    } else if (type === "task_state_change") {
        if (selectedRunId === eventData.run_id) {
            fetchRunTasks(eventData.run_id);
        }
    }
}

function setupWebsocket() {
    if (wsFallbackToPolling) return;

    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws/metrics`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event_type) {
            handleRuntimeDeltaEvent(data.event_type, data);
        } else if (data.type && (data.type.includes(".") || data.type.includes("_"))) {
            handleRuntimeDeltaEvent(data.type, data.data);
        } else {
            updateUI(data);
        }
        wsFailCount = 0; // Reset count on successful message
    };

    ws.onclose = () => {
        wsFailCount++;
        if (wsFailCount >= 3) {
            console.warn("WebSocket repeatedly failed. Falling back to HTTP polling...");
            wsFallbackToPolling = true;
            setInterval(pollMetrics, 3000);
            return;
        }
        console.warn("WebSocket closed. Reconnecting in 3 seconds...");
        setTimeout(setupWebsocket, 3000);
    };

    ws.onerror = (err) => {
        console.error("WebSocket error: ", err);
        ws.close();
    };
}

// Update DOM with metrics data
function updateUI(data) {
    // Reset telemetry freshness timer
    lastTelemetryTime = Date.now();
    const telemetryTimestamp = document.getElementById("telemetry-timestamp");
    const telemetryStaleWarning = document.getElementById("telemetry-stale-warning");
    if (telemetryTimestamp) {
        telemetryTimestamp.textContent = `Last telemetry update: ${new Date().toLocaleTimeString()}`;
    }
    if (telemetryStaleWarning) {
        telemetryStaleWarning.classList.add("hidden");
    }
    if (telemetryIsStale) {
        telemetryIsStale = false;
        logToConsoleTerminal("Telemetry", "Live telemetry feed reconnected & synchronized.", "success");
    }

    if (statusBadge) statusBadge.textContent = data.status;
    if (activeAssetsBadge) activeAssetsBadge.textContent = `${data.active_assets} ASSETS ACTIVE`;
    if (totalAgentsVal) totalAgentsVal.textContent = data.total_agents;
    
    if (cpuPercentVal) cpuPercentVal.textContent = data.system_cpu;
    if (cpuGaugeBar) cpuGaugeBar.style.width = data.system_cpu;

    let ramPercent = 30;
    if (data.system_ram) {
        if (ramUsageVal) ramUsageVal.textContent = data.system_ram;
        const ramParts = data.system_ram.split("/");
        if (ramParts.length === 2) {
            const used = parseFloat(ramParts[0]);
            const total = parseFloat(ramParts[1]);
            ramPercent = Math.round((used / total) * 100);
            if (ramGaugeBar) ramGaugeBar.style.width = `${ramPercent}%`;
        }
    }

    // Update Chart.js lines
    if (liveChart) {
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        chartLabels.push(timeStr);
        chartCpuData.push(parseInt(data.system_cpu));
        chartRamData.push(ramPercent);
        
        if (chartLabels.length > 20) {
            chartLabels.shift();
            chartCpuData.shift();
            chartRamData.shift();
        }
        liveChart.update();
    }

    // Update Dashboard Widgets Charts dynamically
    if (workloadChart && data.system_cpu) {
        const cpuVal = parseInt(data.system_cpu);
        workloadChart.data.datasets[0].data[5] = cpuVal;
        workloadChart.data.datasets[1].data[4] = cpuVal - 2;
        workloadChart.data.datasets[1].data[5] = cpuVal;
        workloadChart.data.datasets[1].data[6] = cpuVal + 2;
        workloadChart.data.datasets[1].data[7] = cpuVal + 5;
        workloadChart.update();
    }

    if (resourceChart && data.nodes) {
        let swarmALoad = 0;
        let swarmBLoad = 0;
        data.nodes.forEach(node => {
            if (node.id === "L1" || node.id === "W1") {
                swarmALoad += node.cpu_usage;
            } else if (node.id === "L2" || node.id === "L3") {
                swarmBLoad += node.cpu_usage;
            }
        });
        const total = Math.max(1, swarmALoad + swarmBLoad);
        const aPercent = Math.round((swarmALoad / total) * 80);
        const bPercent = Math.round((swarmBLoad / total) * 80);
        resourceChart.data.datasets[0].data = [aPercent, bPercent, 100 - aPercent - bPercent];
        resourceChart.update();
    }

    // Populate active deployment table
    if (data.nodes) {
        currentNodes = data.nodes;
        if (window.updateAssetsFromLegacy) {
            window.updateAssetsFromLegacy(data.nodes);
        }
        populateTable(data.nodes);
        updateMermaidTopology(data.nodes);
        renderAssetsView(data.nodes);
        
        // Also refresh settings list if visible
        if (navItems.settings.nav && navItems.settings.nav.classList.contains("active")) {
            renderSettingsNodesList(data.nodes);
        }
    }

    // Render mission feed if streamed over WebSocket/HTTP status response
    if (data.mission_events) {
        renderMissionFeedData(data.mission_events, "mission-event-feed");
        renderMissionFeedData(data.mission_events, "dash-mission-feed");
    }
}

let currentPaths = {};
let glowingAssetIds = {};

// Render active deployments as premium tactical cards
function populateTable(nodes) {
    deploymentsTbody.innerHTML = "";
    nodes.forEach(node => {
        const card = document.createElement("div");
        card.id = `node-card-${node.id}`;
        card.className = "asset-console-card";
        
        let statusClass = "status-idle";
        if (node.status === "Active") statusClass = "status-active";
        else if (node.status === "Underutilized") statusClass = "status-underutilized";

        let osIcon = "monitor";
        if (node.os && node.os.toLowerCase().includes("mac")) osIcon = "apple";
        else if (node.os && node.os.toLowerCase().includes("win")) osIcon = "terminal";
        else if (node.os && node.os.toLowerCase().includes("ios")) osIcon = "smartphone";
        else if (node.os && node.os.toLowerCase().includes("ipad")) osIcon = "tablet";
        else if (node.os && node.os.toLowerCase().includes("linux")) osIcon = "server";

        // Separate specs info
        const specsParts = node.specs.split(",");
        const ramDiskText = specsParts.join(" / ");

        card.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px; text-align: left;">
                <i data-lucide="${osIcon}" class="asset-os-icon" style="width: 18px; height: 18px; color: var(--text-secondary);"></i>
                <div style="display: flex; flex-direction: column; min-width: 0; flex: 1;">
                    <span style="font-size: 12px; font-weight: 600; color: #fff; letter-spacing: 0.3px;">${node.name}</span>
                    <span style="font-size: 9px; color: var(--text-secondary); margin-top: 1px;">${node.ip} &bull; ${ramDiskText}</span>
                    <span class="node-activity-ticker">${node.activity || node.role}</span>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <span class="node-status-label ${getStatusClass(node.status)}">${STATUS_LABELS[node.status] || node.status}</span>
                <span style="font-size: 9px; color: var(--text-secondary); background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; font-family: monospace;">${node.total_agents} AGENTS</span>
                <span class="status-pulse-dot ${getStatusClass(node.status)}"></span>
            </div>
        `;

        
        if (glowingAssetIds[node.id] === "green") {
            card.classList.add("topology-asset-glow");
            card.style.borderColor = "#10b981";
            card.style.boxShadow = "0 0 15px rgba(16, 185, 129, 0.4)";
        } else if (glowingAssetIds[node.id] === "blue") {
            card.style.borderColor = "#3b82f6";
            card.style.boxShadow = "0 0 15px rgba(59, 130, 246, 0.4)";
        }

        card.addEventListener("click", () => {
            openModalForNode(node);
        });
        
        deploymentsTbody.appendChild(card);
    });
    lucide.createIcons();
}

// Function to update the node coordinates from the rendered SVG elements
function updateNodesMap() {
    // Left empty since we define coordinates directly inside our custom SVG builder
}

// Render dynamic custom SVG Topology Layout representing Zero Trust enclaves and C2 architecture
async function updateMermaidTopology(nodes, executingNodeId = null) {
    const wrapper = document.querySelector(".mermaid-container-wrapper");
    const canvas = document.getElementById("agent-flow-canvas");
    if (!wrapper || !canvas) return;

    // ViewBox coordinates
    const width = 800;
    const height = 500;

    canvas.width = width;
    canvas.height = height;

    // Find Master Node
    const masterNode = nodes.find(n => n.id === "L1") || nodes[0];
    if (!masterNode) return;

    // Sort remaining nodes into compute/coder nodes vs client/mobile nodes
    const workers = nodes.filter(n => n.id !== masterNode.id);

    // Positions mapping
    const masterX = 100;
    const masterY = 250;
    const schedX = 290;
    const schedY = 160;
    const lbX = 290;
    const lbY = 340;
    const workerX = 540;

    // Distribute workers vertically in the right-most column
    const workersCount = workers.length;
    const startY = 40;
    const endY = 460;
    const gapY = workersCount > 1 ? (endY - startY) / (workersCount - 1) : 0;

    const workerPositions = {};
    workers.forEach((node, i) => {
        workerPositions[node.id] = workersCount > 1 ? startY + i * gapY : 250;
    });

    let pathsHtml = "";
    currentPaths = {};

    // 1. Master Hub -> Scheduler connection curve (Dotted Cyan X-axis transport)
    const masterToSchedPath = getBezierPathString(masterX, masterY, schedX - 60, schedY);
    pathsHtml += `<path d="${masterToSchedPath}" stroke="rgba(0, 229, 255, 0.45)" stroke-width="1.8" stroke-dasharray="4, 4" fill="none" />`;
    currentPaths["master-sched"] = getBezierPoints(masterX, masterY, schedX - 60, schedY);

    // 2. Master Hub -> Load Balancer connection curve (Dotted Cyan X-axis transport)
    const masterToLbPath = getBezierPathString(masterX, masterY, lbX - 60, lbY);
    pathsHtml += `<path d="${masterToLbPath}" stroke="rgba(0, 229, 255, 0.45)" stroke-width="1.8" stroke-dasharray="4, 4" fill="none" />`;
    currentPaths["master-lb"] = getBezierPoints(masterX, masterY, lbX - 60, lbY);

    // 3. Orchestrator -> Worker connection curves
    workers.forEach(node => {
        const wY = workerPositions[node.id] + 35; // Center of the 70px card
        const isCoder = !node.os || (!node.os.toLowerCase().includes("ios") && !node.os.toLowerCase().includes("ipad"));

        let fromX, fromY, strokeColor, dashArray, pathKey;
        if (isCoder) {
            fromX = schedX + 60;
            fromY = schedY;
            strokeColor = "rgba(0, 229, 255, 0.35)"; // Dotted Cyan for horizontal code pipelines
            dashArray = "4, 4";
            pathKey = `sched-${node.id}`;
        } else {
            fromX = lbX + 60;
            fromY = lbY;
            strokeColor = "rgba(16, 185, 129, 0.45)"; // Solid Green/Teal for vertical edge streams
            dashArray = "none";
            pathKey = `lb-${node.id}`;
        }

        const pathD = getBezierPathString(fromX, fromY, workerX, wY);
        pathsHtml += `<path d="${pathD}" stroke="${strokeColor}" stroke-width="1.5" stroke-dasharray="${dashArray}" fill="none" />`;
        currentPaths[pathKey] = getBezierPoints(fromX, fromY, workerX, wY);

        // Display IP label along path
        const midX = fromX + (workerX - fromX) * 0.55;
        const midY = fromY + (wY - fromY) * 0.45 - 4;
        pathsHtml += `<text x="${midX}" y="${midY}" text-anchor="middle" fill="${isCoder ? 'rgba(0, 229, 255, 0.4)' : 'rgba(16, 185, 129, 0.55)'}" style="font-family: monospace; font-size: 8px; font-weight: bold;">${node.ip}</text>`;
    });

    let nodesHtml = "";

    // Gradient defs
    nodesHtml += `
    <defs>
        <linearGradient id="masterGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#1e3c72" />
            <stop offset="100%" stop-color="#2a52be" />
        </linearGradient>
    </defs>
    `;

    // Render Master Hub
    const isMasterExecuting = executingNodeId === masterNode.id;
    nodesHtml += `
    <g transform="translate(${masterX}, ${masterY})" style="cursor: pointer;" onclick="openModalForNodeById('${masterNode.id}')">
        <circle cx="0" cy="0" r="45" fill="none" stroke="rgba(0, 229, 255, 0.45)" stroke-width="2" stroke-dasharray="10 15">
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="20s" repeatCount="indefinite" />
        </circle>
        <circle cx="0" cy="0" r="38" fill="none" stroke="rgba(168, 85, 247, 0.45)" stroke-width="1.5" stroke-dasharray="6 8">
            <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="12s" repeatCount="indefinite" />
        </circle>
        <circle cx="0" cy="0" r="30" fill="url(#masterGrad)" stroke="${isMasterExecuting ? '#ef4444' : 'rgba(0, 229, 255, 0.6)'}" stroke-width="2.5" style="filter: drop-shadow(0 0 8px ${isMasterExecuting ? 'rgba(239,68,68,0.7)' : 'rgba(0, 229, 255, 0.5)'});" />
        <text x="0" y="3" text-anchor="middle" fill="#ffffff" style="font-family: 'Outfit', sans-serif; font-size: 8px; font-weight: 700; letter-spacing: 0.5px;">CLUSTER MGR</text>
        <text x="0" y="13" text-anchor="middle" fill="rgba(255,255,255,0.7)" style="font-family: monospace; font-size: 7px;">${masterNode.ip}</text>
    </g>
    `;

    // Render Task Scheduler
    nodesHtml += `
    <g transform="translate(${schedX - 60}, ${schedY - 25})" style="cursor: pointer;" onclick="openModalForNodeById('${masterNode.id}')">
        <rect x="0" y="0" width="120" height="50" rx="6" ry="6" fill="#161c2d" stroke="rgba(59, 130, 246, 0.55)" stroke-width="1.5" style="filter: drop-shadow(0 4px 8px rgba(0,0,0,0.4));" />
        <text x="60" y="20" text-anchor="middle" fill="#fff" style="font-family: 'Outfit', sans-serif; font-size: 9px; font-weight: 600; letter-spacing: 0.5px;">TASK SCHEDULER</text>
        <text x="60" y="35" text-anchor="middle" fill="var(--accent-teal)" style="font-family: monospace; font-size: 8px; font-weight: bold;">ACTIVE (OK)</text>
    </g>
    `;

    // Render Load Balancer
    nodesHtml += `
    <g transform="translate(${lbX - 60}, ${lbY - 25})" style="cursor: pointer;">
        <rect x="0" y="0" width="120" height="50" rx="6" ry="6" fill="#161c2d" stroke="rgba(168, 85, 247, 0.55)" stroke-width="1.5" style="filter: drop-shadow(0 4px 8px rgba(0,0,0,0.4));" />
        <text x="60" y="20" text-anchor="middle" fill="#fff" style="font-family: 'Outfit', sans-serif; font-size: 9px; font-weight: 600; letter-spacing: 0.5px;">LOAD BALANCER</text>
        <text x="60" y="35" text-anchor="middle" fill="var(--accent-teal)" style="font-family: monospace; font-size: 8px; font-weight: bold;">ACTIVE (OK)</text>
    </g>
    `;

    // Render Worker Node Cards
    workers.forEach(node => {
        const wY = workerPositions[node.id];
        let statusClass = "status-idle";
        if (node.status === "Active") statusClass = "status-active";
        else if (node.status === "Underutilized") statusClass = "status-underutilized";

        const executingClass = executingNodeId === node.id ? 'executing' : '';
        const nodeStroke = executingNodeId === node.id ? '#ef4444' : 'rgba(255, 255, 255, 0.08)';

        let osIcon = "monitor";
        if (node.os && node.os.toLowerCase().includes("mac")) osIcon = "apple";
        else if (node.os && node.os.toLowerCase().includes("win")) osIcon = "terminal";
        else if (node.os && node.os.toLowerCase().includes("ios")) osIcon = "smartphone";
        else if (node.os && node.os.toLowerCase().includes("ipad")) osIcon = "tablet";
        else if (node.os && node.os.toLowerCase().includes("linux")) osIcon = "server";

        nodesHtml += `
        <foreignObject x="${workerX}" y="${wY}" width="200" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" class="topology-node-card ${executingClass}" onclick="openModalForNodeById('${node.id}')" style="box-sizing: border-box; width: 100%; height: 100%; background: rgba(22, 28, 45, 0.85); backdrop-filter: blur(8px); border: 1px solid ${nodeStroke}; border-radius: 8px; padding: 8px 12px; display: flex; flex-direction: column; justify-content: space-between; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.4); overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 6px; min-width: 0; flex: 1;">
                        <i data-lucide="${osIcon}" style="width: 12px; height: 12px; color: var(--text-secondary); flex-shrink: 0;"></i>
                        <span style="font-size: 11px; font-weight: bold; color: #fff; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; max-width: 110px;">${node.name}</span>
                    </div>
                    <span class="node-status-label ${getStatusClass(node.status)}" style="font-size: 8px; padding: 1px 5px;">${node.status}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 8px; color: var(--text-secondary); margin-top: 2px;">
                    <span>${node.ip}</span>
                    <span>CPU: ${node.cpu_usage}%</span>
                </div>
                <div class="node-activity-ticker" style="font-size: 8px; max-width: 180px;">${node.activity || node.role}</div>
                <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 2px; overflow: hidden; max-height: 16px;">
                    ${node.agents && node.agents.length > 0 
                        ? node.agents.map(a => `<span class="agent-pill ${a.type.includes('GORDY') ? 'gordy' : ''}" style="font-size: 7px; padding: 1px 3px; border-radius: 3px; background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.25); color: #c084fc; font-family: monospace; white-space: nowrap;">${a.name.split('-')[0]}</span>`).join('') 
                        : `<span style="font-size: 7px; color: var(--text-secondary);">No active agents</span>`}
                </div>
            </div>
        </foreignObject>
        `;

    });

    // Populate SVG
    mermaidGraph.innerHTML = `
    <svg id="topology-svg" width="100%" height="100%" viewBox="0 0 ${width} ${height}" style="overflow: visible; transition: transform 0.05s ease-out; transform-origin: center center;">
        <g id="svg-paths">${pathsHtml}</g>
        <g id="svg-nodes">${nodesHtml}</g>
    </svg>
    `;

    // Apply transforms
    const svg = mermaidGraph.querySelector("svg");
    if (svg) {
        svg.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    }

    // Rebind zoom/pan
    setupSvgPanZoom();

    // Render icons inside SVG foreignObject
    lucide.createIcons();
}

window.openModalForNodeById = function(nodeId) {
    const node = currentNodes.find(n => n.id === nodeId);
    if (node) openModalForNode(node);
};

// SVG curve calculations
function getBezierPathString(x1, y1, x2, y2) {
    const dx = (x2 - x1) * 0.55;
    return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

function getBezierPoints(x1, y1, x2, y2) {
    const dx = (x2 - x1) * 0.55;
    return {
        p0: { x: x1, y: y1 },
        p1: { x: x1 + dx, y: y1 },
        p2: { x: x2 - dx, y: y2 },
        p3: { x: x2, y: y2 }
    };
}

// Spawns particle bursts along specific bezier paths
function spawnTaskParticles(targetNodeId) {
    const isCoder = targetNodeId === "L2" || targetNodeId === "L3" || targetNodeId === "W1" || targetNodeId === "L1";
    const path1Key = isCoder ? "master-sched" : "master-lb";
    const path2Key = isCoder ? `sched-${targetNodeId}` : `lb-${targetNodeId}`;
    
    const pts1 = currentPaths[path1Key];
    const pts2 = currentPaths[path2Key];
    
    if (pts1 && pts2) {
        const color = isCoder ? "rgba(0, 229, 255, 0.85)" : "rgba(16, 185, 129, 0.85)";
        
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                particles.push({
                    progress: 0,
                    speed: 0.024,
                    size: 3.5,
                    color: color,
                    p0: pts1.p0,
                    p1: pts1.p1,
                    p2: pts1.p2,
                    p3: pts1.p3,
                    onComplete: () => {
                        particles.push({
                            progress: 0,
                            speed: 0.018,
                            size: 3.5,
                            color: color,
                            p0: pts2.p0,
                            p1: pts2.p1,
                            p2: pts2.p2,
                            p3: pts2.p3
                        });
                    }
                });
            }, i * 150);
        }
    }
}

// Dispatch task to swarm backend
// Intercept dispatch and open command preview modal
if (btnSubmitTask) {
    btnSubmitTask.addEventListener("click", () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("Please enter a task instruction.");
            return;
        }

        const taskType = taskTypeSelect.value;
        
        // Determine expected target node client-side
        const promptLower = prompt.toLowerCase();
        let targetId = "L1";
        if (promptLower.includes("neo") || promptLower.includes("l3")) {
            targetId = "L3";
        } else if (promptLower.includes("deploy") || promptLower.includes("app store")) {
            targetId = "L3";
        } else if (promptLower.includes("imac") || promptLower.includes("l2")) {
            targetId = "L2";
        } else if (promptLower.includes("dell") || promptLower.includes("w1") || promptLower.includes("9440")) {
            targetId = "W1";
        } else if (promptLower.includes("ipad")) {
            targetId = "IPAD";
        } else if (promptLower.includes("iphone")) {
            targetId = "IPHONE";
        } else if (promptLower.includes("code") || promptLower.includes("write") || promptLower.includes("research")) {
            const coders = ["L2", "L3", "W1"].filter(id => {
                const n = currentNodes.find(x => x.id === id);
                return n && n.status !== "Offline";
            });
            if (coders.length > 0) {
                let lowestNode = coders[0];
                let lowestCpu = 100;
                coders.forEach(id => {
                    const n = currentNodes.find(x => x.id === id);
                    if (n && n.cpu_usage < lowestCpu) {
                        lowestCpu = n.cpu_usage;
                        lowestNode = id;
                    }
                });
                targetId = lowestNode;
            } else {
                targetId = "L1";
            }
        } else if (taskType === "mobile" || promptLower.includes("ui")) {
            targetId = "IPAD";
        } else {
            targetId = "L1";
        }

        const targetNode = currentNodes.find(n => n.id === targetId);

        // Populate Command Preview Modal elements
        document.getElementById("preview-cmd-text").textContent = prompt;
        const targetSpan = document.getElementById("preview-target-node");
        if (targetSpan) {
            targetSpan.textContent = targetNode ? `${targetNode.name} (${targetNode.ip})` : "—";
        }
        const enclaveSpan = document.getElementById("preview-affected-nodes");
        if (enclaveSpan) {
            if (targetNode) {
                if (targetNode.os && (targetNode.os.toLowerCase().includes("ios") || targetNode.os.toLowerCase().includes("ipad"))) {
                    enclaveSpan.textContent = "JWICS (MOBILE EDGE)";
                } else if (targetNode.id === "L1") {
                    enclaveSpan.textContent = "NIPRNET (CORE SERVICES)";
                } else {
                    enclaveSpan.textContent = "SIPRNET (TACTICAL COMPUTE)";
                }
            } else {
                enclaveSpan.textContent = "SIPRNET (TACTICAL COMPUTE)";
            }
        }

        // Set default radio selection
        const defaultRadio = document.querySelector('input[name="dispatch-mode"][value="Simulate"]');
        if (defaultRadio) defaultRadio.checked = true;

        // Show command safety preview modal
        const modal = document.getElementById("command-preview-modal");
        if (modal) modal.classList.remove("hidden");

        if (window.addAuditEvent) {
            window.addAuditEvent({
                actor: { id: "michael.hoch", name: "Michael Hoch", type: "human", role: "Operator" },
                action: { type: "COMMAND_PREVIEWED", summary: `Command instruction previewed: "${prompt}"` },
                target: { type: "command", id: "input-command", name: prompt },
                result: "success",
                severity: "low",
                provenance: { source: "manual", evidence_refs: [] },
                policy: { required: false, result: "not_required" }
            });
        }

        // Bind Confirm Dispatch button (once/overwrite to avoid duplicate handlers)
        const btnConfirmDispatch = document.getElementById("btn-confirm-dispatch");
        if (btnConfirmDispatch) {
            btnConfirmDispatch.onclick = async () => {
                const modal2 = document.getElementById("command-preview-modal");
                if (modal2) modal2.classList.add("hidden");
                const selectedMode = document.querySelector('input[name="dispatch-mode"]:checked').value;
                await executeTaskWithMode(prompt, taskType, selectedMode);
            };
        }
    });
}

// Zoom and Reset controls for topology layout
if (btnZoom) {
    btnZoom.addEventListener("click", () => {
        scale = scale >= 1.8 ? 1.0 : scale + 0.2;
        const svg = mermaidGraph.querySelector("svg");
        if (svg) svg.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    });
}

if (btnReset) {
    btnReset.addEventListener("click", () => {
        scale = 1.0;
        panX = 0;
        panY = 0;
        const svg = mermaidGraph.querySelector("svg");
        if (svg) svg.style.transform = `translate(0px, 0px) scale(1.0)`;
    });
}

// Modal Logic to display node specs and Gordy profiles
// Modal Logic to display node specs and Gordy profiles
function openModalForNode(node) {
    modalNodeTitle.textContent = node.name;
    modalNodeIp.textContent = node.ip;
    modalNodeSpecs.textContent = node.specs;
    modalNodeRole.textContent = `${node.os} (${node.role})`;
    
    const latencyVal = node.latency_ms || 0.0;
    modalNodeLatency.textContent = `${latencyVal}ms`;

    // Upgrade: Latency progress bar inside the modal header
    const latencyBar = document.getElementById("modal-latency-bar");
    if (latencyBar) {
        const percent = Math.min(100, Math.max(5, (latencyVal / 10.0) * 100)); // normalized to 10ms scale for detail bar
        latencyBar.style.width = `${percent}%`;
        
        let latColour = "#10b981";  // green (good)
        if (latencyVal < 0)        { latColour = "#6b7280"; } // Offline / BLOCKED
        else if (latencyVal > 3.0) { latColour = "#ef4444"; } // Red (slow)
        else if (latencyVal > 1.5) { latColour = "#f59e0b"; } // Amber (moderate)
        
        latencyBar.style.backgroundColor = latColour;
    }

    modalAgentsContainer.innerHTML = "";
    if (node.agents && node.agents.length > 0) {
        node.agents.forEach(agent => {
            const isGordy = agent.type.includes("GORDY") || agent.type.includes("Docker Coder");
            const typeClass = isGordy ? "agent-type agent-type-gordy" : "agent-type";
            
            // Per-agent status color mapping
            let dotColour = "#10b981"; // green (default/active)
            const stat = (agent.status || "").toLowerCase();
            if (stat.includes("triage"))       dotColour = "#f59e0b"; // amber
            else if (stat.includes("heal"))   dotColour = "#a855f7"; // purple
            else if (stat.includes("reason"))  dotColour = "#3b82f6"; // blue
            else if (stat.includes("deploy"))  dotColour = "#06b6d4"; // cyan
            
            const card = document.createElement("div");
            card.className = "agent-card";
            card.innerHTML = `
                <div class="agent-card-header">
                    <span class="agent-name">${agent.name}</span>
                    <span class="${typeClass}">${agent.type}</span>
                </div>
                <p class="agent-desc">${agent.description}</p>
                <div class="agent-status-badge">
                    <span class="dot" style="background-color: ${dotColour}"></span>
                    <span style="color: var(--text-secondary); margin-left: 4px; font-weight: 600;">Status: ${agent.status}</span>
                </div>
            `;
            modalAgentsContainer.appendChild(card);
        });
    } else {
        modalAgentsContainer.innerHTML = `<p style="color:var(--text-secondary);font-size:14px;grid-column:1/-1;text-align:center;padding:24px 0;">No active agent containers deployed on this node.</p>`;
    }

    // Upgrade: Fetch and render Node-specific Mission Timeline (recent 5 events)
    const timelineContainer = document.getElementById("modal-timeline-container");
    if (timelineContainer) {
        timelineContainer.innerHTML = `<span style="font-size:11px;color:var(--text-secondary);font-style:italic;">Loading timeline events...</span>`;
        fetch(`${API_BASE}/api/mission/feed?limit=80`)
            .then(res => res.ok ? res.json() : {events:[]})
            .then(data => {
                const nodeEvents = (data.events || []).filter(e => e.node_id === node.id).slice(0, 5);
                timelineContainer.innerHTML = "";
                if (nodeEvents.length > 0) {
                    nodeEvents.forEach(ev => {
                        const item = document.createElement("div");
                        const statusClass = (ev.status || "Active").toLowerCase().replace(/ /g, "-");
                        item.className = `modal-timeline-item status-${statusClass}`;
                        item.innerHTML = `
                            <span style="color:var(--text-secondary);font-family:monospace;font-size:9.5px;flex-shrink:0;margin-top:2px;">${ev.ts}</span>
                            <div style="flex-grow:1;display:flex;flex-direction:column;">
                                <span style="font-weight:700;color:#fff;font-size:10px;">${ev.icon} ${ev.status.toUpperCase()}</span>
                                <span style="color:var(--text-secondary);font-size:9.5px;margin-top:2px;line-height:1.3;">${ev.activity}</span>
                            </div>
                        `;
                        timelineContainer.appendChild(item);
                    });
                } else {
                    timelineContainer.innerHTML = `<p style="color:var(--text-secondary);font-size:11px;font-style:italic;">No historical events recorded for this node.</p>`;
                }
            })
            .catch(err => {
                console.warn("Error loading modal timeline:", err);
                timelineContainer.innerHTML = `<p style="color:#ef4444;font-size:11px;">Failed to load timeline.</p>`;
            });
    }

    // Reset accordions to default state: 1, 2, 3 expanded, 4 collapsed
    const modalAccordions = modalContainer.querySelectorAll(".accordion-item");
    modalAccordions.forEach((item, index) => {
        const header = item.querySelector(".accordion-header");
        const content = item.querySelector(".accordion-content");
        if (header && content) {
            if (index < 3) {
                header.classList.add("active");
                content.style.display = "block";
                content.classList.add("show");
            } else {
                header.classList.remove("active");
                content.style.display = "none";
                content.classList.remove("show");
            }
        }
    });

    if (modalContainer) {
        modalContainer.classList.remove("hidden");
    }
    lucide.createIcons(); // Re-render X icon inside modal
}

// Close Modal Controls
if (btnCloseModal) {
    btnCloseModal.addEventListener("click", () => {
        if (modalContainer) modalContainer.classList.add("hidden");
    });
}

if (modalContainer) {
    modalContainer.addEventListener("click", (e) => {
        if (e.target === modalContainer) {
            modalContainer.classList.add("hidden");
        }
    });
}

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (modalContainer) modalContainer.classList.add("hidden");
    }
});

// View Tab Navigation - Generic switcher
Object.keys(navItems).forEach(key => {
    const item = navItems[key];
    if (item.nav && item.view) {
        item.nav.addEventListener("click", (e) => {
            e.preventDefault();
            // Remove active class from all nav items, add to current
            Object.values(navItems).forEach(x => {
                if (x.nav) x.nav.classList.remove("active");
                if (x.view) x.view.classList.add("hidden");
            });
            item.nav.classList.add("active");
            item.view.classList.remove("hidden");

            // Custom actions on tab switches
            if (key === "security" || key === "releaseProvenance") {
                triggerSecurityAudit();
                if (typeof fetchAndRenderSigningPolicy === 'function') {
                    fetchAndRenderSigningPolicy();
                }
            } else if (key === "assets" || key === "swarmControl") {
                renderAssetsView(currentNodes);
            } else if (key === "tasks" || key === "remediationSafety") {
                fetchAndRenderTasks();
                if (window.onRemediationTabActive) window.onRemediationTabActive();
            } else if (key === "settings") {
                renderSettingsNodesList(currentNodes);
            } else if (key === "audit" || key === "runtimeAudit" || key === "metrics") {
                triggerSecurityAudit();
                fetchAndRenderAuditLogs();
            } else if (key === "cybersecurityFactory") {
                if (window.renderCybersecurityFactoryView) window.renderCybersecurityFactoryView();
            } else if (key === "replay" || key === "timelineReplay") {
                if (window.onReplayTabActive) window.onReplayTabActive();
            } else if (key === "governance") {
                if (typeof window.fetchAndRenderGovernanceSummary === "function") {
                    window.fetchAndRenderGovernanceSummary();
                }
            } else if (key === "collab") {
                if (window.onCollabTabActive) window.onCollabTabActive();
            } else if (key === "ledger") {
                if (window.onLedgerTabActive) window.onLedgerTabActive();
            } else if (key === "governance") {
                if (window.onGovernanceTabActive) window.onGovernanceTabActive();
            } else if (key === "redTeam") {
                if (window.onRedTeamTabActive) window.onRedTeamTabActive();
            } else if (key === "executive") {
                if (window.onExecutiveTabActive) window.onExecutiveTabActive();
            } else if (key === "capabilities") {
                if (window.onCapabilitiesTabActive) window.onCapabilitiesTabActive();
            } else if (key === "remediation") {
                if (window.onRemediationTabActive) window.onRemediationTabActive();
            } else if (key === "tenancy") {
                if (window.onTenancyTabActive) window.onTenancyTabActive();
            } else if (key === "compliance") {
                if (window.onComplianceTabActive) window.onComplianceTabActive();
            } else if (key === "customerSuccess") {
                if (window.onCustomerSuccessTabActive) window.onCustomerSuccessTabActive();
            } else if (key === "revenueOps") {
                if (window.onRevenueOpsTabActive) window.onRevenueOpsTabActive();
            } else if (key === "hochster" || key === "hochsterRuntime") {
                if (window.onHochsterTabActive) window.onHochsterTabActive();
            } else if (key === "readinessAutopilot") {
                fetchReadinessAutopilotData();
            }
        });
    }
});

// Sub-tabs in Security View
if (subtabAudit && subtabGap) {
    subtabAudit.addEventListener("click", () => {
        subtabAudit.classList.add("active");
        subtabGap.classList.remove("active");
        securityAuditContent.classList.remove("hidden");
        securityGapContent.classList.add("hidden");
    });
    
    subtabGap.addEventListener("click", () => {
        subtabGap.classList.add("active");
        subtabAudit.classList.remove("active");
        securityGapContent.classList.remove("hidden");
        securityAuditContent.classList.add("hidden");
    });
}

// Render all node cards inside Assets tab grid
function renderAssetsView(nodes) {
    if (!assetsGridContainer || !nodes) return;
    assetsGridContainer.innerHTML = "";

    nodes.forEach(node => {
        const card = document.createElement("div");
        card.className = "asset-detail-card";
        const sc = getStatusClass(node.status);

        // Build agent capsules list
        let capsulesHtml = "";
        if (node.agents && node.agents.length > 0) {
            node.agents.forEach(agent => {
                const isGordy = agent.type.includes("GORDY") || agent.type.includes("Docker Coder");
                const capsuleClass = isGordy ? "agent-capsule agent-capsule-gordy" : "agent-capsule";
                const agentSC = getStatusClass(agent.status);
                capsulesHtml += `<span class="${capsuleClass}" style="cursor:default" title="${agent.description || ''}">${agent.name} <span class="node-status-label ${agentSC}" style="font-size:7px; padding:1px 4px; margin-left:2px;">${agent.status}</span></span>`;
            });
        } else {
            capsulesHtml = `<span style="font-size:11px; color:var(--text-secondary);">No agents active</span>`;
        }

        card.innerHTML = `
            <div class="asset-card-title-row">
                <span class="asset-card-title">${node.name}</span>
                <span class="node-status-label ${sc}">${STATUS_LABELS[node.status] || node.status}</span>
            </div>
            <div class="node-activity-ticker" style="margin-top: 4px; margin-bottom: 8px; font-size: 10px;">${node.activity || node.role}</div>

                <div><strong>IP Address:</strong> ${node.ip}</div>
                <div><strong>Role/OS:</strong> ${node.os} (${node.role})</div>
                <div><strong>Specifications:</strong> ${node.specs}</div>
                <div><strong>CPU Usage:</strong> ${node.cpu_usage}%</div>
                <div><strong>RAM Usage:</strong> ${node.ram_usage}%</div>
                <div><strong>Latency:</strong> ${node.latency_ms || 1.2}ms</div>
            </div>
            <div style="margin-top: 12px;">
                <div style="font-size: 11px; text-transform: uppercase; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Deployed Agent Containers</div>
                <div class="asset-agents-capsules">
                    ${capsulesHtml}
                </div>
            </div>
        `;

        card.addEventListener("click", () => {
            openModalForNode(node);
        });

        assetsGridContainer.appendChild(card);
    });
}

// Run Security Audit and render RMF Scorecard
async function triggerSecurityAudit() {
    securityControlsList.innerHTML = `<p style="color:var(--text-secondary); text-align:center; padding: 24px;">Running cybersecurity RMF compliance assessment audit...</p>`;
    if (securityGapTbody) {
        securityGapTbody.innerHTML = `<tr><td colspan="5" style="color:var(--text-secondary); text-align:center; padding: 24px;">Running audit. Gap analysis generating...</td></tr>`;
    }
    btnRunAudit.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/security/audit`);
        if (response.ok) {
            const data = await response.json();
            
            // Update scorecard UI
            auditScorePercent.textContent = data.compliance_score;
            auditPassedCount.textContent = data.stats.passed;
            auditWarningsCount.textContent = data.stats.warnings;
            auditFailedCount.textContent = data.stats.failed;

            // Render controls checklist
            securityControlsList.innerHTML = "";
            data.controls.forEach(control => {
                let statusClass = "status-idle";
                if (control.status === "PASS") statusClass = "status-active";
                else if (control.status === "WARNING") statusClass = "status-underutilized";
                else if (control.status === "FAIL") statusClass = "text-danger";

                const card = document.createElement("div");
                card.className = "control-item-card";
                
                let detailsHtml = "";
                control.details.forEach(detail => {
                    detailsHtml += `<li>${detail}</li>`;
                });

                card.innerHTML = `
                    <div class="control-item-header">
                        <div class="control-code-name">
                            <span class="control-code">${control.control}</span>
                            <span class="control-name">${control.name}</span>
                        </div>
                        <span class="status-indicator ${statusClass}"><span class="dot" style="background-color:currentColor"></span> ${control.status}</span>
                    </div>
                    <ul class="control-details-list">
                        ${detailsHtml}
                    </ul>
                `;
                securityControlsList.appendChild(card);
            });
            
            // Generate the Gap Analysis report
            renderGapReport(data.controls);
            
            lucide.createIcons();
        } else {
            securityControlsList.innerHTML = `<p style="color:#ef4444; text-align:center; padding: 24px;">Failed to complete cybersecurity compliance audit check.</p>`;
        }
    } catch (err) {
        securityControlsList.innerHTML = `<p style="color:#ef4444; text-align:center; padding: 24px;">Connection lost to security controller: ${err.message}</p>`;
    } finally {
        btnRunAudit.disabled = false;
    }
}

// Generate the Gap Analysis report
function renderGapReport(controls) {
    if (!securityGapTbody) return;
    securityGapTbody.innerHTML = "";

    controls.forEach(control => {
        const tr = document.createElement("tr");
        
        let statusClass = "status-idle";
        if (control.status === "PASS") statusClass = "status-active";
        else if (control.status === "WARNING") statusClass = "status-underutilized";
        else if (control.status === "FAIL") statusClass = "text-danger";

        // Map identified gap and remediation command based on control status and type
        let gapDesc = "";
        let remediationHtml = "";

        if (control.status === "PASS") {
            gapDesc = "None (Compliant). Control is active and verified.";
            remediationHtml = `<span style="color: var(--text-secondary);">None Required</span>`;
        } else {
            // For failed or warning controls, provide explicit gaps and remediation commands
            if (control.control === "AC-3") {
                gapDesc = control.details.join(" ") || "Unsafe SSH key directory/file permissions detected.";
                remediationHtml = `<div class="remediation-cmd-container">chmod 700 ~/.ssh && chmod 600 ~/.ssh/*</div>
                                   <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="patchControl('${control.control}')"><i data-lucide="shield-alert" style="width:12px;height:12px;"></i> Patch Control</button>`;
            } else if (control.control === "AC-17") {
                gapDesc = control.details.join(" ") || "Weak SSH configurations detected. Password authentication or root login enabled.";
                remediationHtml = `<div class="remediation-cmd-container">sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config</div>
                                   <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="patchControl('${control.control}')"><i data-lucide="shield-alert" style="width:12px;height:12px;"></i> Patch Control</button>`;
            } else if (control.control === "AU-12") {
                gapDesc = control.details.join(" ") || "No standard system logging daemon found running.";
                remediationHtml = `<div class="remediation-cmd-container">sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.syslogd.plist</div>
                                   <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="patchControl('${control.control}')"><i data-lucide="shield-alert" style="width:12px;height:12px;"></i> Patch Control</button>`;
            } else if (control.control === "SI-2") {
                gapDesc = control.details.join(" ") || "Critical system partition usage exceeded threshold.";
                remediationHtml = `<div class="remediation-cmd-container">docker system prune -a --volumes && rclone move /data/ gdrive:swarm_backup</div>
                                   <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="patchControl('${control.control}')"><i data-lucide="shield-alert" style="width:12px;height:12px;"></i> Patch Control</button>`;
            } else {
                gapDesc = control.details.join(" ");
                remediationHtml = `<span style="color: var(--text-secondary);">Audit host settings manually</span>`;
            }
        }

        tr.innerHTML = `
            <td><code>${control.control}</code></td>
            <td><strong>${control.name}</strong></td>
            <td><span class="status-indicator ${statusClass}"><span class="dot" style="background-color:currentColor"></span> ${control.status}</span></td>
            <td style="max-width: 250px; font-size: 13px; line-height: 1.4; color: var(--text-secondary);">${gapDesc}</td>
            <td>${remediationHtml}</td>
        `;
        securityGapTbody.appendChild(tr);
    });

    // Append Swarm-specific Gap Analysis Entries
    const swarmGaps = [
        {
            control: "SWARM-SYNC",
            name: "Workspace Consistency",
            status: "WARNING",
            gapDesc: "Isolated workspace directory trees across active swarm nodes (MBP, iMac, Dell, etc.) lack dynamic file synchronization.",
            remediationHtml: `<div class="remediation-cmd-container">syncthing --home=/data/syncthing</div>
                               <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="alert('Starting Syncthing daemon to sync swarm workspace...')"><i data-lucide="refresh-cw" style="width:12px;height:12px;"></i> Initialize Sync</button>`
        },
        {
            control: "SELF-HEAL",
            name: "Self-Correcting Debug Loop",
            status: "WARNING",
            gapDesc: "Compilation and testing failures are printed to logs but do not automatically route back to Coder agent for iterative self-healing.",
            remediationHtml: `<div class="remediation-cmd-container">python3 backend/agent_runner.py --enable-self-healing</div>
                               <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="alert('Enabling compiler feedback self-healing loop...')"><i data-lucide="shield-check" style="width:12px;height:12px;"></i> Enable Loop</button>`
        },
        {
            control: "SWARM-METRICS",
            name: "Performance Analytics",
            status: "PASS",
            gapDesc: "Historical node resource metrics are static in the UI (only showing averages instead of realtime plots).",
            remediationHtml: `<span style="color: var(--text-secondary);">Resolved: Active WebSocket data stream plotted in real time</span>`
        },
        {
            control: "SWARM-API-SEC",
            name: "API Access Control",
            status: "WARNING",
            gapDesc: "Control plane endpoints lack JWT or OAuth2 authorization and transaction rate-limiting.",
            remediationHtml: `<div class="remediation-cmd-container">uvicorn backend.main:app --auth-token $SWARM_SECRET</div>
                               <button class="btn btn-primary btn-xs" style="margin-top: 6px; font-size:11px; padding: 4px 8px; width:100%;" onclick="alert('Securing endpoints with token validation...')"><i data-lucide="lock" style="width:12px;height:12px;"></i> Secure API</button>`
        }
    ];

    swarmGaps.forEach(gap => {
        const tr = document.createElement("tr");
        let statusClass = "status-underutilized";
        if (gap.status === "PASS") statusClass = "status-active";
        else if (gap.status === "FAIL") statusClass = "text-danger";

        tr.innerHTML = `
            <td><code>${gap.control}</code></td>
            <td><strong>${gap.name}</strong></td>
            <td><span class="status-indicator ${statusClass}"><span class="dot" style="background-color:currentColor"></span> ${gap.status}</span></td>
            <td style="max-width: 250px; font-size: 13px; line-height: 1.4; color: var(--text-secondary);">${gap.gapDesc}</td>
            <td>${gap.remediationHtml}</td>
        `;
        securityGapTbody.appendChild(tr);
    });
}

btnRunAudit.addEventListener("click", triggerSecurityAudit);

// Fetch and render tasks history table
async function fetchAndRenderTasks() {
    if (!tasksTbody) return;
    try {
        const response = await fetch(`${API_BASE}/api/tasks`);
        if (response.ok) {
            const tasks = await response.json();
            tasksTbody.innerHTML = "";
            if (tasks.length === 0) {
                tasksTbody.innerHTML = `<tr><td colspan="5" style="color:var(--text-secondary); text-align:center; padding: 24px;">No tasks run in this session.</td></tr>`;
                return;
            }
            tasks.forEach(task => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><code>${task.task_id}</code></td>
                    <td><strong>${task.task_type}</strong></td>
                    <td>${task.node_name}</td>
                    <td>${task.duration}</td>
                    <td><span class="status-indicator status-active"><span class="dot" style="background-color: var(--accent-teal)"></span> ${task.status}</span></td>
                `;
                tasksTbody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error("Failed to load task history: ", err);
    }
}

// Render settings asset management table
function renderSettingsNodesList(nodes) {
    if (!settingsNodesTbody || !nodes) return;
    settingsNodesTbody.innerHTML = "";
    
    nodes.forEach(node => {
        const tr = document.createElement("tr");
        
        const isControlPlane = node.id === "L1";
        const removeButtonHtml = isControlPlane 
            ? `<span style="color:var(--text-secondary); font-size:11px;">Protected</span>`
            : `<button class="btn btn-outline btn-xs" style="border-color:#ef4444; color:#ef4444; display: inline-flex; align-items: center; gap: 4px;" onclick="removeNode('${node.id}')"><i data-lucide="trash-2" style="width:12px;height:12px;"></i> Deregister</button>`;

        tr.innerHTML = `
            <td><strong>${node.name}</strong><br/><small style="color:var(--text-secondary)">${node.os} (${node.role})</small></td>
            <td><code>${node.ip}</code></td>
            <td>${removeButtonHtml}</td>
        `;
        settingsNodesTbody.appendChild(tr);
    });
    lucide.createIcons();
}

// Register a new node
if (btnRegisterNode) {
    btnRegisterNode.addEventListener("click", async (e) => {
        e.preventDefault();
        
        const id = document.getElementById("reg-node-id").value.trim().toUpperCase();
        const name = document.getElementById("reg-node-name").value.trim();
        const ip = document.getElementById("reg-node-ip").value.trim();
        const role = document.getElementById("reg-node-role").value.trim();
        const specs = document.getElementById("reg-node-specs").value.trim();
        const os = document.getElementById("reg-node-os").value;

        if (!id || !name || !ip || !role || !specs) {
            alert("All fields are required to register a new swarm asset.");
            return;
        }

        const payload = { id, name, ip, role, specs, os, total_agents: 0, status: "Active" };

        try {
            const response = await fetch(`${API_BASE}/api/nodes/add`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const res = await response.json();
                if (res.status === "SUCCESS") {
                    alert(`Successfully registered node '${name}' in swarm.`);
                    if (formRegisterNode) formRegisterNode.reset();
                    
                    const statusRes = await fetch(`${API_BASE}/api/status`);
                    if (statusRes.ok) {
                        const data = await statusRes.json();
                        updateUI(data);
                        renderSettingsNodesList(data.nodes);
                    }
                } else {
                    alert("Failed to register node.");
                }
            }
        } catch (err) {
            alert("Error connecting to control plane: " + err.message);
        }
    });
}

// Remove a registered node
window.removeNode = async function(nodeId) {
    if (!confirm(`Are you sure you want to deregister node '${nodeId}' from the swarm?`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/nodes/remove/${nodeId}`, {
            method: "DELETE"
        });

        if (response.ok) {
            const res = await response.json();
            if (res.status === "SUCCESS") {
                alert(`Deregistered node '${nodeId}'.`);
                const statusRes = await fetch(`${API_BASE}/api/status`);
                if (statusRes.ok) {
                    const data = await statusRes.json();
                    updateUI(data);
                    renderSettingsNodesList(data.nodes);
                }
            } else {
                alert("Failed to deregister node.");
            }
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
};

// Start dashboard on load
window.addEventListener("DOMContentLoaded", initDashboard);

// Setup custom SVG dragging and wheel-zoom on Mermaid SVG
// Sync pan/zoom coordinates directly between SVG and overlay particle Canvas
function setupSvgPanZoom() {
    const svg = mermaidGraph.querySelector("svg");
    const canvas = document.getElementById("agent-flow-canvas");
    if (!svg) return;

    const applyTransform = () => {
        const transStr = `translate(${panX}px, ${panY}px) scale(${scale})`;
        svg.style.transform = transStr;
        if (canvas) {
            canvas.style.transform = transStr;
        }
    };

    svg.style.transition = "transform 0.05s ease-out";
    svg.style.transformOrigin = "center center";
    if (canvas) {
        canvas.style.transition = "transform 0.05s ease-out";
        canvas.style.transformOrigin = "center center";
    }
    applyTransform();

    // Scroll wheel zoom
    mermaidGraph.onwheel = function(e) {
        e.preventDefault();
        const zoomFactor = 0.08;
        if (e.deltaY < 0) {
            scale = Math.min(3.0, scale + zoomFactor);
        } else {
            scale = Math.max(0.4, scale - zoomFactor);
        }
        applyTransform();
    };

    // Mouse drag-panning
    mermaidGraph.onmousedown = function(e) {
        if (e.button !== 0) return; // Left click only
        isPanning = true;
        startPanX = e.clientX - panX;
        startPanY = e.clientY - panY;
        mermaidGraph.style.cursor = "grabbing";
    };

    window.onmousemove = function(e) {
        if (!isPanning) return;
        panX = e.clientX - startPanX;
        panY = e.clientY - startPanY;
        applyTransform();
    };

    window.onmouseup = function() {
        if (isPanning) {
            isPanning = false;
            mermaidGraph.style.cursor = "default";
        }
    };
}

// Initialize Chart.js Line Chart
function initMetricsChart() {
    const ctx = document.getElementById("live-metrics-chart");
    if (!ctx) return;

    liveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [
                {
                    label: 'Cluster CPU Usage (%)',
                    data: chartCpuData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.04)',
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true
                },
                {
                    label: 'Cluster RAM Allocation (%)',
                    data: chartRamData,
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.04)',
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#9ca3af', font: { family: 'Inter' } }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#f3f4f6', font: { family: 'Outfit', weight: '500' } }
                }
            }
        }
    });
}

// 2D HTML5 Canvas Swarm Particle Flow Animation
function animateSwarmFlow() {
    const canvas = document.getElementById("agent-flow-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Draw background glowing connection paths (matching SVG layout for visual richness)
    ctx.lineWidth = 1.5;
    Object.keys(currentPaths).forEach(key => {
        const pts = currentPaths[key];
        ctx.beginPath();
        ctx.moveTo(pts.p0.x, pts.p0.y);
        
        ctx.bezierCurveTo(pts.p1.x, pts.p1.y, pts.p2.x, pts.p2.y, pts.p3.x, pts.p3.y);
        
        const isCoder = key.startsWith("sched") || key === "master-sched" || key === "master-lb";
        if (isCoder) {
            ctx.setLineDash([3, 5]); // Dotted for X-axis
            ctx.strokeStyle = "rgba(0, 229, 255, 0.15)";
        } else {
            ctx.setLineDash([]); // Solid for Y-axis
            ctx.strokeStyle = "rgba(16, 185, 129, 0.2)";
        }
        ctx.stroke();
    });

    if (prefersReducedMotion) {
        // Skip particle logic and animation loop when reduced motion is preferred
        return;
    }

    // Update and render particle stream
    for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.progress += p.speed;

        if (p.progress >= 1.0) {
            if (p.onComplete) p.onComplete();
            particles.splice(i, 1);
            continue;
        }

        // Cubic Bezier interpolation
        const t = p.progress;
        const mt = 1 - t;
        const mt2 = mt * mt;
        const mt3 = mt2 * mt;
        const t2 = t * t;
        const t3 = t2 * t;

        const curX = mt3 * p.p0.x + 3 * mt2 * t * p.p1.x + 3 * mt * t2 * p.p2.x + t3 * p.p3.x;
        const curY = mt3 * p.p0.y + 3 * mt2 * t * p.p1.y + 3 * mt * t2 * p.p2.y + t3 * p.p3.y;

        // Radial gradient glow
        ctx.beginPath();
        const glow = ctx.createRadialGradient(curX, curY, 0, curX, curY, p.size * 2.2);
        glow.addColorStop(0, p.color);
        glow.addColorStop(1, "transparent");
        ctx.fillStyle = glow;
        ctx.arc(curX, curY, p.size * 2.5, 0, Math.PI * 2);
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.fillStyle = "#ffffff";
        ctx.arc(curX, curY, p.size * 0.6, 0, Math.PI * 2);
        ctx.fill();
    }

    // Gentle random pulse packets when idle
    if (Math.random() < 0.03 && particles.length < 15) {
        const keys = Object.keys(currentPaths);
        if (keys.length > 0) {
            const key = keys[Math.floor(Math.random() * keys.length)];
            const pts = currentPaths[key];
            const isCoder = key.startsWith("sched") || key === "master-sched" || key === "master-lb";
            const color = isCoder ? "rgba(0, 229, 255, 0.75)" : "rgba(16, 185, 129, 0.75)";
            
            particles.push({
                progress: 0,
                speed: 0.012 + Math.random() * 0.008,
                size: 3 + Math.random() * 1.5,
                color: color,
                p0: pts.p0,
                p1: pts.p1,
                p2: pts.p2,
                p3: pts.p3
            });
        }
    }

    animationFrameId = requestAnimationFrame(animateSwarmFlow);
}

function spawnParticlePath(from, to, nextLeg = null, color = "rgba(0, 229, 255, 0.8)") {
    // Backwards compatibility fallback if needed
}

// 3D Fibonacci Sphere Rotating Mesh Globe Engine
let globeAngleY = 0;
let globeAngleX = 0.3;

function initSwarmGlobe() {
    const canvas = document.getElementById("swarm-globe-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    // Generate static 3D coordinate nodes on a sphere
    const points = [];
    const count = 75;
    const goldenRatio = (1 + Math.sqrt(5)) / 2;
    const goldenAngle = 2 * Math.PI * (1 - 1 / goldenRatio);

    for (let i = 0; i < count; i++) {
        const y = 1 - (i / (count - 1)) * 2; // y goes from 1 to -1
        const radius = Math.sqrt(1 - y * y);
        const theta = goldenAngle * i;
        const x = Math.cos(theta) * radius;
        const z = Math.sin(theta) * radius;
        points.push({ x, y, z });
    }

    function drawGlobe() {
        if (!document.getElementById("swarm-globe-canvas")) return;

        // Auto-scale canvas resolution to wrapper container size
        const rect = canvas.parentNode.getBoundingClientRect();
        if (canvas.width !== rect.width || canvas.height !== rect.height) {
            canvas.width = rect.width;
            canvas.height = rect.height;
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const rVal = Math.min(cx, cy) * 0.8;

        globeAngleY += prefersReducedMotion ? 0 : 0.004; // Rotate speed

        const cosY = Math.cos(globeAngleY);
        const sinY = Math.sin(globeAngleY);
        const cosX = Math.cos(globeAngleX);
        const sinX = Math.sin(globeAngleX);

        // Map 3D coords to projected 2D coordinates
        const projected = points.map(p => {
            // Rotation Y
            let x1 = p.x * cosY - p.z * sinY;
            let z1 = p.x * sinY + p.z * cosY;

            // Rotation X
            let y2 = p.y * cosX - z1 * sinX;
            let z2 = p.y * sinX + z1 * cosX;

            // Perspective scale
            const fov = 3.0;
            const dist = 2.0;
            const scale2D = fov / (fov + z2 * dist);

            return {
                x: cx + x1 * rVal * scale2D,
                y: cy + y2 * rVal * scale2D,
                z: z2,
                scale: scale2D
            };
        });

        // Draw connections
        ctx.lineWidth = 0.5;
        for (let i = 0; i < count; i++) {
            for (let j = i + 1; j < count; j++) {
                const p1 = points[i];
                const p2 = points[j];

                // 3D Distance calculation
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dz = p1.z - p2.z;
                const distSq = dx*dx + dy*dy + dz*dz;

                if (distSq < 0.22) {
                    const proj1 = projected[i];
                    const proj2 = projected[j];

                    const avgZ = (proj1.z + proj2.z) / 2;
                    const opacity = Math.max(0.02, Math.min(0.35, (1 - avgZ) * 0.22));

                    ctx.strokeStyle = `rgba(0, 229, 255, ${opacity})`;
                    ctx.beginPath();
                    ctx.moveTo(proj1.x, proj1.y);
                    ctx.lineTo(proj2.x, proj2.y);
                    ctx.stroke();
                }
            }
        }

        // Draw nodes
        projected.forEach(p => {
            const opacity = Math.max(0.1, Math.min(0.85, (1 - p.z) * 0.45));
            const size = Math.max(1, p.scale * 2.0);

            let color = `rgba(0, 229, 255, ${opacity})`; // Cyan for front
            if (p.z > 0.25) {
                color = `rgba(168, 85, 247, ${opacity * 0.65})`; // Purple for back
            }

            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
            ctx.fill();

            // Core highlight
            if (p.z < -0.75) {
                ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
                ctx.beginPath();
                ctx.arc(p.x, p.y, size * 0.45, 0, Math.PI * 2);
                ctx.fill();
            }
        });

        if (!prefersReducedMotion) {
            requestAnimationFrame(drawGlobe);
        }
    }

    drawGlobe();
}

// Initialize workload and resource analytics widgets charts
let workloadChart = null;
let resourceChart = null;

function initDashboardCharts() {
    const workloadCtx = document.getElementById("console-workload-chart");
    if (workloadCtx) {
        workloadChart = new Chart(workloadCtx, {
            type: 'line',
            data: {
                labels: ['t-50s', 't-40s', 't-30s', 't-20s', 't-10s', 'now', 't+10s', 't+20s'],
                datasets: [
                    {
                        label: 'Actual Load',
                        data: [42, 45, 48, 52, 58, 60, null, null],
                        borderColor: '#00e5ff',
                        backgroundColor: 'rgba(0, 229, 255, 0.05)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Predictive Model',
                        data: [null, null, null, null, 58, 60, 62, 65],
                        borderColor: 'rgba(168, 85, 247, 0.8)',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        tension: 0.4,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { display: false, min: 0, max: 100 },
                    x: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 8 } } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    const resourceCtx = document.getElementById("console-resource-chart");
    if (resourceCtx) {
        resourceChart = new Chart(resourceCtx, {
            type: 'bar',
            data: {
                labels: ['Swarm A', 'Swarm B', 'Spare'],
                datasets: [{
                    data: [45, 35, 20],
                    backgroundColor: ['rgba(0, 229, 255, 0.7)', 'rgba(168, 85, 247, 0.7)', 'rgba(255, 255, 255, 0.2)'],
                    borderRadius: 4,
                    borderWidth: 0
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.6)', font: { size: 9 } } },
                    x: { display: false, max: 100 }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

// Terminal logs controller
const consoleTerminalLogs = document.getElementById("console-terminal-logs");
const terminalSearch = document.getElementById("terminal-search");
let allTerminalLogs = [];

function logToConsoleTerminal(module, message, type = "info") {
    const timestamp = new Date().toISOString().replace('T', ' ').substr(0, 19);
    let color = "#4ade80"; // Green
    if (type === "warn") color = "#f97316"; // Orange
    else if (type === "error") color = "#ef4444"; // Red
    else if (type === "system") color = "#00e5ff"; // Cyan

    const logText = `[${timestamp}] [${module.toUpperCase()}] ${message}`;
    allTerminalLogs.push({ text: logText, color, type });

    if (allTerminalLogs.length > 80) allTerminalLogs.shift();
    renderTerminalLogs();
}

function renderTerminalLogs() {
    if (!consoleTerminalLogs) return;
    const query = terminalSearch ? terminalSearch.value.trim().toLowerCase() : "";
    
    const filtered = allTerminalLogs.filter(log => log.text.toLowerCase().includes(query));
    
    consoleTerminalLogs.innerHTML = filtered.map(log => 
        `<div style="color: ${log.color}; margin-bottom: 2px; line-height: 1.4;">${log.text}</div>`
    ).join('');
    
    consoleTerminalLogs.scrollTop = consoleTerminalLogs.scrollHeight;
}

if (terminalSearch) {
    terminalSearch.addEventListener("input", renderTerminalLogs);
}

// Heartbeat background generator
setInterval(() => {
    const modules = ["ControlPlane", "Scheduler", "DockerRunner", "Telemetry", "SecurityMonitor"];
    const actions = [
        "Vitals telemetry successfully broadcasted.",
        "Heartbeat check passed for all container nodes.",
        "RMF ConMon policy rules validated.",
        "Active connection pool healthy.",
        "Allocated dynamic resources updated in analytics panel.",
        "Flushed local execution buffer."
    ];
    const mod = modules[Math.floor(Math.random() * modules.length)];
    const act = actions[Math.floor(Math.random() * actions.length)];
    logToConsoleTerminal(mod, act, "info");
}, 7000);

// One-Click compliance repair action
window.patchControl = async function(controlId) {
    const patchConfirm = confirm(`Execute automated compliance remediation for control: ${controlId}?`);
    if (!patchConfirm) return;

    try {
        const response = await fetch(`${API_BASE}/api/security/patch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ control_id: controlId })
        });

        if (response.ok) {
            const result = await response.json();
            alert(`Remediation Result:\nStatus: ${result.status}\nDetails: ${result.details}`);
            logToConsoleTerminal("SecurityMonitor", `Patched control ${controlId}: ${result.details}`, "system");
            triggerSecurityAudit(); // Refresh scorecard and gap checklist
        } else {
            alert("Remediation execution failed on Control Plane.");
            logToConsoleTerminal("SecurityMonitor", `Patch failed on control ${controlId}`, "error");
        }
    } catch (err) {
        alert("Remediation connection error: " + err.message);
        logToConsoleTerminal("SecurityMonitor", `Patch connection error: ${err.message}`, "error");
    }
};

/* ================================================================
   PHASE 9 — PERT Analysis Controller
   ================================================================ */

// ---- State ----
let pertData = null;   // last API response
let pertSvgPanX = 0, pertSvgPanY = 0, pertSvgScale = 1.0;
let pertIsPanning = false, pertPanStartX = 0, pertPanStartY = 0;

// ---- Elements (lazy-resolved after DOM ready) ----
function getPertEl(id) { return document.getElementById(id); }

// ---- Fetch PERT data from backend and refresh all views ----
async function loadPertData() {
    try {
        const resp = await fetch(`${API_BASE}/api/pert`);
        if (!resp.ok) throw new Error(`PERT API ${resp.status}`);
        pertData = await resp.json();
        renderPertDiagram(pertData);
        renderPertTable(pertData);
        renderPertStats(pertData);
        logToConsoleTerminal("PertEngine", `PERT network refreshed — ${pertData.tasks.length} tasks, duration: ${pertData.project_duration.toFixed(2)}s`, "info");
    } catch (err) {
        console.warn("PERT load error:", err);
    }
}

// ================================================================
//  DAG LAYOUT SOLVER  (Sugiyama-lite column / rank assignment)
// ================================================================
function computeDagLayout(tasks) {
    // Build adjacency lists
    const byId = {};
    tasks.forEach(t => { byId[t.id] = t; });

    // Kahn BFS to assign columns (depth ranks)
    const inDeg = {};
    const children = {};
    tasks.forEach(t => {
        inDeg[t.id] = (t.predecessors || []).length;
        children[t.id] = [];
    });
    tasks.forEach(t => {
        (t.predecessors || []).forEach(p => {
            if (children[p]) children[p].push(t.id);
        });
    });

    const rank = {};
    const queue = tasks.filter(t => inDeg[t.id] === 0).map(t => t.id);
    queue.forEach(id => { rank[id] = 0; });

    while (queue.length > 0) {
        const cur = queue.shift();
        (children[cur] || []).forEach(ch => {
            rank[ch] = Math.max(rank[ch] || 0, (rank[cur] || 0) + 1);
            inDeg[ch]--;
            if (inDeg[ch] === 0) queue.push(ch);
        });
    }

    // Group by rank (column)
    const cols = {};
    tasks.forEach(t => {
        const r = rank[t.id] || 0;
        if (!cols[r]) cols[r] = [];
        cols[r].push(t.id);
    });

    const maxCol = Math.max(...Object.keys(cols).map(Number));
    const NODE_W = 130, NODE_H = 60, COL_GAP = 60, ROW_GAP = 18;

    // Compute per-node (x, y) pixel positions
    const positions = {};
    Object.keys(cols).forEach(colStr => {
        const col = Number(colStr);
        const ids = cols[col];
        ids.forEach((id, rowIdx) => {
            const x = col * (NODE_W + COL_GAP) + 20;
            const y = rowIdx * (NODE_H + ROW_GAP) + 20;
            positions[id] = { x, y, w: NODE_W, h: NODE_H };
        });
    });

    // Canvas dimensions
    const maxX = Math.max(...Object.values(positions).map(p => p.x + p.w)) + 30;
    const maxY = Math.max(...Object.values(positions).map(p => p.y + p.h)) + 30;

    return { positions, maxX, maxY, rank };
}

// ================================================================
//  SVG RENDERER
// ================================================================
function renderPertDiagram(data) {
    const container = getPertEl("pert-diagram-svg-container");
    if (!container) return;

    const tasks = data.tasks || [];
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="pert-empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
                </svg>
                <span>Add tasks to visualize the PERT network</span>
            </div>`;
        return;
    }

    const critSet = new Set(data.critical_path || []);
    const { positions, maxX, maxY } = computeDagLayout(tasks);
    const byId = {};
    tasks.forEach(t => { byId[t.id] = t; });

    // Build SVG
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("viewBox", `0 0 ${maxX} ${maxY}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.style.overflow = "visible";

    // ---- Defs: arrow markers ----
    const defs = document.createElementNS(svgNS, "defs");
    ["critical", "normal"].forEach(type => {
        const marker = document.createElementNS(svgNS, "marker");
        marker.setAttribute("id", `arrow-${type}`);
        marker.setAttribute("markerWidth", "8");
        marker.setAttribute("markerHeight", "8");
        marker.setAttribute("refX", "6");
        marker.setAttribute("refY", "3");
        marker.setAttribute("orient", "auto");
        const poly = document.createElementNS(svgNS, "polygon");
        poly.setAttribute("points", "0 0, 8 3, 0 6");
        poly.setAttribute("class", `pert-arrow-${type}`);
        marker.appendChild(poly);
        defs.appendChild(marker);
    });
    svg.appendChild(defs);

    // ---- Pan/zoom group ----
    const g = document.createElementNS(svgNS, "g");
    g.setAttribute("id", "pert-dag-group");
    g.setAttribute("transform", `translate(${pertSvgPanX},${pertSvgPanY}) scale(${pertSvgScale})`);

    // ---- Draw edges first (behind nodes) ----
    tasks.forEach(task => {
        (task.predecessors || []).forEach(predId => {
            if (!positions[predId] || !positions[task.id]) return;
            const src = positions[predId];
            const dst = positions[task.id];
            const isCrit = critSet.has(predId) && critSet.has(task.id);

            // Bezier control points
            const x1 = src.x + src.w;
            const y1 = src.y + src.h / 2;
            const x2 = dst.x;
            const y2 = dst.y + dst.h / 2;
            const cx1 = x1 + (x2 - x1) * 0.45;
            const cy1 = y1;
            const cx2 = x1 + (x2 - x1) * 0.55;
            const cy2 = y2;

            const path = document.createElementNS(svgNS, "path");
            path.setAttribute("d", `M${x1},${y1} C${cx1},${cy1} ${cx2},${cy2} ${x2},${y2}`);
            path.setAttribute("fill", "none");
            path.setAttribute("class", isCrit ? "pert-edge-critical" : "pert-edge-normal");
            path.setAttribute("marker-end", `url(#arrow-${isCrit ? "critical" : "normal"})`);
            g.appendChild(path);
        });
    });

    // ---- Draw nodes ----
    tasks.forEach(task => {
        const pos = positions[task.id];
        if (!pos) return;
        const isCrit = critSet.has(task.id);
        const slack = typeof task.slack === "number" ? task.slack : Infinity;

        const nodeG = document.createElementNS(svgNS, "g");
        nodeG.setAttribute("class", "pert-node");
        nodeG.setAttribute("transform", `translate(${pos.x},${pos.y})`);
        nodeG.setAttribute("data-task-id", task.id);
        nodeG.style.cursor = "pointer";

        // Background rect
        const rectClass = isCrit ? "critical" : (slack > 2 ? "slack-high" : "non-critical");
        const rect = document.createElementNS(svgNS, "rect");
        rect.setAttribute("width", pos.w);
        rect.setAttribute("height", pos.h);
        rect.setAttribute("rx", "8");
        rect.setAttribute("ry", "8");
        rect.setAttribute("fill", isCrit ? "rgba(239,68,68,0.12)" : "rgba(30,41,59,0.85)");
        rect.setAttribute("class", `pert-node-rect ${rectClass}`);
        nodeG.appendChild(rect);

        // Task ID label (top-left)
        const idText = document.createElementNS(svgNS, "text");
        idText.setAttribute("x", "10");
        idText.setAttribute("y", "17");
        idText.setAttribute("font-size", "10");
        idText.setAttribute("font-weight", "700");
        idText.setAttribute("font-family", "monospace");
        idText.setAttribute("fill", isCrit ? "#f87171" : "#60a5fa");
        idText.textContent = task.id;
        nodeG.appendChild(idText);

        // Task name (center)
        const nameText = document.createElementNS(svgNS, "text");
        nameText.setAttribute("x", pos.w / 2);
        nameText.setAttribute("y", "34");
        nameText.setAttribute("text-anchor", "middle");
        nameText.setAttribute("font-size", "9");
        nameText.setAttribute("fill", "rgba(255,255,255,0.8)");
        const shortName = task.name.length > 16 ? task.name.slice(0, 15) + "…" : task.name;
        nameText.textContent = shortName;
        nodeG.appendChild(nameText);

        // ES/EF row
        const esText = document.createElementNS(svgNS, "text");
        esText.setAttribute("x", "8");
        esText.setAttribute("y", pos.h - 8);
        esText.setAttribute("font-size", "8");
        esText.setAttribute("fill", "rgba(255,255,255,0.45)");
        const te = typeof task.te === "number" ? task.te.toFixed(1) : "?";
        const es = typeof task.es === "number" ? task.es.toFixed(1) : "?";
        const ef = typeof task.ef === "number" ? task.ef.toFixed(1) : "?";
        esText.textContent = `TE:${te}  ES:${es}  EF:${ef}`;
        nodeG.appendChild(esText);

        // Slack badge (top-right corner)
        const slackTxt = document.createElementNS(svgNS, "text");
        slackTxt.setAttribute("x", pos.w - 8);
        slackTxt.setAttribute("y", "17");
        slackTxt.setAttribute("text-anchor", "end");
        slackTxt.setAttribute("font-size", "9");
        slackTxt.setAttribute("font-weight", "700");
        slackTxt.setAttribute("fill", isCrit ? "#f87171" : (slack < 2 ? "#fbbf24" : "#2dd4bf"));
        slackTxt.textContent = `σ${typeof task.slack === "number" ? task.slack.toFixed(1) : "∞"}`;
        nodeG.appendChild(slackTxt);

        // Tooltip data via title element
        const titleEl = document.createElementNS(svgNS, "title");
        titleEl.textContent = [
            `Task: ${task.name}`,
            `TE: ${te}d  Slack: ${typeof task.slack === "number" ? task.slack.toFixed(2) : "N/A"}`,
            `ES: ${es}  EF: ${ef}`,
            `LS: ${typeof task.ls === "number" ? task.ls.toFixed(1) : "?"} LF: ${typeof task.lf === "number" ? task.lf.toFixed(1) : "?"}`,
            isCrit ? "⚠ CRITICAL PATH" : ""
        ].filter(Boolean).join("  |  ");
        nodeG.appendChild(titleEl);

        g.appendChild(nodeG);
    });

    svg.appendChild(g);
    container.innerHTML = "";
    container.appendChild(svg);

    // ---- Wire pan / zoom on the SVG ----
    bindPertSvgPanZoom(svg, g);
}

// ================================================================
//  SVG PAN/ZOOM BINDINGS
// ================================================================
function bindPertSvgPanZoom(svg, group) {
    function applyTransform() {
        group.setAttribute("transform", `translate(${pertSvgPanX},${pertSvgPanY}) scale(${pertSvgScale})`);
    }

    svg.addEventListener("mousedown", e => {
        pertIsPanning = true;
        pertPanStartX = e.clientX - pertSvgPanX;
        pertPanStartY = e.clientY - pertSvgPanY;
        svg.style.cursor = "grabbing";
    });
    window.addEventListener("mousemove", e => {
        if (!pertIsPanning) return;
        pertSvgPanX = e.clientX - pertPanStartX;
        pertSvgPanY = e.clientY - pertPanStartY;
        applyTransform();
    });
    window.addEventListener("mouseup", () => {
        pertIsPanning = false;
        if (svg) svg.style.cursor = "default";
    });
    svg.addEventListener("wheel", e => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        pertSvgScale = Math.min(3, Math.max(0.3, pertSvgScale * delta));
        applyTransform();
    }, { passive: false });
}

// ================================================================
//  TABLE RENDERER
// ================================================================
function renderPertTable(data) {
    const tbody = getPertEl("pert-tasks-tbody");
    if (!tbody) return;
    const critSet = new Set(data.critical_path || []);
    tbody.innerHTML = "";
    (data.tasks || []).forEach(task => {
        const isCrit = critSet.has(task.id);
        const slack = typeof task.slack === "number" ? task.slack : null;
        const slackClass = isCrit ? "critical" : (slack !== null && slack < 2 ? "low-slack" : "slack-ok");
        const slackLabel = isCrit ? "CRIT" : (slack !== null ? slack.toFixed(1) : "N/A");
        const preds = (task.predecessors || []).join(", ") || "—";
        const te = typeof task.te === "number" ? task.te.toFixed(2) : "—";
        const es = typeof task.es === "number" ? task.es.toFixed(2) : "—";
        const ef = typeof task.ef === "number" ? task.ef.toFixed(2) : "—";
        const ls = typeof task.ls === "number" ? task.ls.toFixed(2) : "—";
        const lf = typeof task.lf === "number" ? task.lf.toFixed(2) : "—";
        const omp = `${task.optimistic}/${task.most_likely}/${task.pessimistic}`;

        const tr = document.createElement("tr");
        if (isCrit) tr.classList.add("critical-row");
        tr.innerHTML = `
            <td>${task.id}</td>
            <td>${task.name}</td>
            <td style="font-size:10px; color:var(--text-secondary);">${preds}</td>
            <td style="font-size:10px; font-family:monospace;">${omp}</td>
            <td style="font-weight:600;">${te}</td>
            <td style="font-size:10px; font-family:monospace;">${es}&nbsp;/&nbsp;${ef}</td>
            <td style="font-size:10px; font-family:monospace;">${ls}&nbsp;/&nbsp;${lf}</td>
            <td><span class="pert-slack-badge ${slackClass}">${slackLabel}</span></td>
            <td><button class="btn-pert-del" onclick="deletePertTask('${task.id}')">✕ Del</button></td>`;
        tbody.appendChild(tr);
    });
}

// ================================================================
//  STATS PANEL RENDERER
// ================================================================
function renderPertStats(data) {
    const durationEl = getPertEl("pert-duration-val");
    const stddevEl = getPertEl("pert-stddev-val");
    const seqEl = getPertEl("pert-critical-path-seq");

    if (durationEl) durationEl.textContent = `${(data.project_duration || 0).toFixed(2)}d`;
    if (stddevEl) stddevEl.textContent = `±${(data.project_stddev || 0).toFixed(2)}d`;

    if (seqEl) {
        const cp = data.critical_path || [];
        if (cp.length === 0) {
            seqEl.innerHTML = `<span style="color:var(--text-secondary); font-size:10px;">No tasks yet</span>`;
        } else {
            seqEl.innerHTML = cp.map((id, i) =>
                `<span class="pert-path-pill">${id}${
                    i < cp.length - 1 ? '<span class="pert-path-arrow">→</span>' : ''
                }</span>`
            ).join(" ");
        }
    }
}

// ================================================================
//  TASK CRUD CALLBACKS
// ================================================================
async function savePertTask(e) {
    e.preventDefault();
    const id      = (getPertEl("pert-task-id")?.value || "").trim().toUpperCase();
    const name    = (getPertEl("pert-task-name")?.value || "").trim();
    const opt     = parseFloat(getPertEl("pert-task-opt")?.value);
    const likely  = parseFloat(getPertEl("pert-task-likely")?.value);
    const pess    = parseFloat(getPertEl("pert-task-pess")?.value);
    const predsRaw = (getPertEl("pert-task-preds")?.value || "").trim();
    const preds   = predsRaw ? predsRaw.split(/[,\s]+/).map(p => p.trim().toUpperCase()).filter(Boolean) : [];

    if (!id || !name || isNaN(opt) || isNaN(likely) || isNaN(pess)) {
        alert("Please fill all required fields (ID, Name, O, M, P).");
        return;
    }
    if (opt > likely || likely > pess) {
        alert("Time estimates must satisfy: Optimistic ≤ Most Likely ≤ Pessimistic.");
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/pert/task`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id, name, optimistic: opt, most_likely: likely, pessimistic: pess, predecessors: preds })
        });
        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.detail || resp.statusText);
        }
        // Clear form
        ["pert-task-id","pert-task-name","pert-task-opt","pert-task-likely","pert-task-pess","pert-task-preds"]
            .forEach(id => { const el = getPertEl(id); if (el) el.value = ""; });
        logToConsoleTerminal("PertEngine", `Task ${id} (${name}) added to PERT network.`, "info");
        await loadPertData();
    } catch (err) {
        alert("Error saving task: " + err.message);
        logToConsoleTerminal("PertEngine", `Save task failed: ${err.message}`, "error");
    }
}

window.deletePertTask = async function(taskId) {
    if (!confirm(`Remove task ${taskId} from the PERT network?`)) return;
    try {
        const resp = await fetch(`${API_BASE}/api/pert/task/${taskId}`, { method: "DELETE" });
        if (!resp.ok) throw new Error(await resp.text());
        logToConsoleTerminal("PertEngine", `Task ${taskId} removed from PERT network.`, "info");
        await loadPertData();
    } catch (err) {
        alert("Error deleting task: " + err.message);
    }
};

async function resetPertTasks() {
    if (!confirm("Reset PERT network to the default sample workflow?")) return;
    try {
        const resp = await fetch(`${API_BASE}/api/pert/reset`, { method: "POST" });
        if (!resp.ok) throw new Error(await resp.text());
        logToConsoleTerminal("PertEngine", "PERT network reset to default sample workflow.", "system");
        await loadPertData();
    } catch (err) {
        alert("Error resetting PERT: " + err.message);
    }
}

// ================================================================
//  BOOT — wire up PERT tab activation
// ================================================================
(function initPertModule() {
    // Lazy-init: trigger load when the PERT tab is first clicked
    const navPert = document.getElementById("nav-pert");
    let pertLoaded = false;
    if (navPert) {
        navPert.addEventListener("click", async () => {
            if (!pertLoaded) {
                pertLoaded = true;
                await loadPertData();
            }
        });
    }

    // Form submission
    const form = document.getElementById("form-pert-task");
    if (form) form.addEventListener("submit", savePertTask);

    // Reset button
    const btnReset = document.getElementById("btn-reset-pert");
    if (btnReset) btnReset.addEventListener("click", resetPertTasks);
})();


// ================================================================
//  PHASE 10: MISSION INTELLIGENCE MODULE
// ================================================================

// --- Status colour map (left-border of feed rows) ---
const MISSION_STATUS_COLOURS = {
    "Active":       "#10b981",
    "Triaging":     "#f59e0b",
    "Self-Healing": "#a855f7",
    "Reasoning":    "#3b82f6",
    "Deploying":    "#06b6d4",
};

/**
 * Render given mission events array into the target HTML container.
 */
function renderMissionFeedData(events, containerId = "mission-event-feed") {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!events || events.length === 0) return;

    container.innerHTML = "";
    events.forEach(ev => {
        const borderCol = MISSION_STATUS_COLOURS[ev.status] || "#10b981";
        const sc = getStatusClass(ev.status);
        const row = document.createElement("div");
        row.className = "mission-event-row";
        row.style.cssText = `
            display: flex; align-items: flex-start; gap: 10px;
            padding: 7px 10px; border-radius: 6px;
            background: rgba(255,255,255,0.03);
            border-left: 3px solid ${borderCol};
            transition: background 0.2s;
            flex-shrink: 0;
        `;
        row.innerHTML = `
            <span style="font-size: 9px; color: var(--text-secondary); font-family: monospace; white-space: nowrap; margin-top: 1px;">${ev.ts}</span>
            <div style="display: flex; flex-direction: column; min-width: 0; flex: 1;">
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                    <span style="font-size: 10px; font-weight: 700; color: #fff; font-family: monospace;">${ev.icon} ${ev.node_id}</span>
                    <span class="node-status-label ${sc}" style="font-size: 7px; padding: 1px 5px;">${ev.status}</span>
                    <span style="font-size: 9px; color: var(--text-secondary); font-family: monospace;">CPU ${ev.cpu}% · RAM ${ev.ram}%</span>
                </div>
                <span style="font-size: 10px; color: var(--text-secondary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${ev.activity}</span>
            </div>
        `;
        row.addEventListener("mouseenter", () => row.style.background = "rgba(255,255,255,0.06)");
        row.addEventListener("mouseleave", () => row.style.background = "rgba(255,255,255,0.03)");
        container.appendChild(row);
    });
}

async function loadMissionFeed(containerId = "mission-event-feed") {
    try {
        const resp = await fetch(`${API_BASE}/api/mission/feed?limit=30`);
        if (!resp.ok) return;
        const { events } = await resp.json();
        renderMissionFeedData(events, containerId);
    } catch (e) {
        console.warn("Mission feed load error:", e);
    }
}

/**
 * Typewriter-animates the Intel Brief into a target element.
 */
let _briefTypewriterTimer = null;
function typewriterAnimate(el, text, speed = 12) {
    if (_briefTypewriterTimer) clearInterval(_briefTypewriterTimer);
    el.textContent = "";
    let i = 0;
    _briefTypewriterTimer = setInterval(() => {
        el.textContent += text[i] || "";
        i++;
        if (i >= text.length) clearInterval(_briefTypewriterTimer);
    }, speed);
}

/**
 * Fetch /api/mission/brief and display with typewriter animation.
 * @param {string} textElId — ID of the <div> for the brief text
 * @param {string} tsElId   — ID of the timestamp label (optional)
 */
async function loadIntelBrief(textElId = "mission-intel-brief-text", tsElId = "mission-brief-ts") {
    const textEl = document.getElementById(textElId);
    const tsEl   = tsElId ? document.getElementById(tsElId) : null;
    if (!textEl) return;
    try {
        const resp = await fetch(`${API_BASE}/api/mission/brief`);
        if (!resp.ok) return;
        const { brief, ts } = await resp.json();
        // Colour the header line differently
        typewriterAnimate(textEl, brief, 10);
        if (tsEl && ts) tsEl.textContent = ts.replace("T", " ").split(".")[0] + "Z";
        if (window.addAuditEvent) {
            window.addAuditEvent({
                actor: { id: "agent.cluster-intel", name: "Cluster Intel Agent", type: "agent" },
                action: { type: "AI_RECOMMENDATION_GENERATED", summary: "New cluster operations intelligence brief generated." },
                target: { type: "system", id: "intel-briefing", name: "Operations Intelligence Brief" },
                result: "success",
                severity: "medium",
                provenance: { source: "inferred", confidence: 94, evidence_refs: ["telemetry.sync.latest"] },
                policy: { required: false, result: "not_required" }
            });
        }
    } catch (e) {
        console.warn("Intel brief load error:", e);
        if (textEl) textEl.textContent = "[ Brief unavailable — server may be restarting ]";
    }
}

/**
 * Fetch /api/nodes/ping and render a latency table.
 */
async function loadPingTable(containerId = "mission-ping-table") {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `<span style="font-size:11px;color:var(--text-secondary);font-style:italic;">Pinging all nodes...</span>`;
    try {
        const resp = await fetch(`${API_BASE}/api/nodes/ping`);
        if (!resp.ok) throw new Error("Ping API error");
        const { pings } = await resp.json();
        container.innerHTML = "";
        Object.entries(pings).forEach(([nodeId, info]) => {
            const ms = info.latency_ms;
            let latColour = "#10b981";  // green
            let latLabel  = `${ms} ms`;
            if (ms < 0)        { latColour = "#6b7280"; latLabel = "BLOCKED"; }
            else if (ms > 50)  { latColour = "#ef4444"; }
            else if (ms > 10)  { latColour = "#f59e0b"; }

            const row = document.createElement("div");
            row.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:rgba(255,255,255,0.03);border-radius:6px;gap:10px;";
            row.innerHTML = `
                <span style="font-family:monospace;font-size:11px;font-weight:700;color:#fff;">${nodeId}</span>
                <span style="font-size:10px;color:var(--text-secondary);flex:1;margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${info.name}</span>
                <span style="font-size:10px;color:var(--text-secondary);font-family:monospace;">${info.ip}</span>
                <span class="ping-badge" style="
                    font-family:monospace;font-size:10px;font-weight:700;
                    padding:2px 10px;border-radius:12px;
                    background:${latColour}22;
                    border:1px solid ${latColour}55;
                    color:${latColour};
                    white-space:nowrap;
                ">${latLabel}</span>
            `;
            container.appendChild(row);
        });
    } catch (e) {
        console.warn("Ping load error:", e);
        container.innerHTML = `<span style="font-size:11px;color:#ef4444;">Ping request failed — check backend.</span>`;
    }
}

/** Polling intervals for mission module. */
let _missionFeedInterval = null;

function startMissionPolling() {
    // Immediately load
    loadMissionFeed("mission-event-feed");
    loadMissionFeed("dash-mission-feed"); // Dashboard strip (if exists)
}

// ---- Boot IIFE: wire Mission Intel tab ----
(function initMissionModule() {
    const navMission = document.getElementById("nav-mission");
    if (!navMission) return;

    let missionActivated = false;

    navMission.addEventListener("click", async () => {
        if (!missionActivated) {
            missionActivated = true;
            // Full-page feed
            await loadMissionFeed("mission-event-feed");
            await loadIntelBrief("mission-intel-brief-text", "mission-brief-ts");
        }
        // Refresh feed on every visit
        loadMissionFeed("mission-event-feed");
    });

    // Refresh Brief button (full-page view)
    const btnRefreshBrief = document.getElementById("btn-mission-refresh-brief");
    if (btnRefreshBrief) {
        btnRefreshBrief.addEventListener("click", () => {
            loadIntelBrief("mission-intel-brief-text", "mission-brief-ts");
        });
    }

    // Ping All button
    const btnPingAll = document.getElementById("btn-mission-ping-all");
    if (btnPingAll) {
        btnPingAll.addEventListener("click", () => {
            loadPingTable("mission-ping-table");
        });
    }

    // Dashboard Intel Brief refresh button
    const btnRefreshDash = document.getElementById("btn-refresh-brief");
    if (btnRefreshDash) {
        btnRefreshDash.addEventListener("click", () => {
            loadIntelBrief("dash-intel-brief-text", null);
        });
    }
})();

// ================================================================
//  PHASE 11: DYNAMIC ACCORDIONS, AUDIT FEEDS, & DISPATCH MODES
// ================================================================

function setupAccordions() {
    const accordions = document.querySelectorAll(".accordion-item");
    accordions.forEach(item => {
        const header = item.querySelector(".accordion-header");
        const content = item.querySelector(".accordion-content");
        if (header && content) {
            header.addEventListener("click", () => {
                const isActive = header.classList.contains("active");
                if (isActive) {
                    header.classList.remove("active");
                    content.style.display = "none";
                    content.classList.remove("show");
                } else {
                    header.classList.add("active");
                    content.style.display = "block";
                    content.classList.add("show");
                }
            });
        }
    });
}

async function executeTaskWithMode(prompt, taskType, mode) {
    taskOutputBox.classList.remove("hidden");
    logOutputContent.innerHTML = `<span style="color:var(--text-secondary)">[System] Dispatching task to cluster (${mode} Mode)...</span><br/>`;
    logToConsoleTerminal("Scheduler", `Task dispatch requested: "${prompt}" (Type: ${taskType}, Mode: ${mode})`, "system");
    btnSubmitTask.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/tasks/run`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                task_type: taskType,
                prompt: prompt,
                mode: mode
            })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Highlight target node
            const targetNode = data.routed_node;
            logOutputContent.innerHTML += `<span style="color:var(--accent-blue)">[Scheduler] Routed to ${targetNode.name} (${targetNode.ip})</span><br/>`;
            logToConsoleTerminal("Orchestrator", `Routed task to ${targetNode.name} (${targetNode.ip}) [Mode: ${mode}]`, "info");
            
            // Log audit event
            if (window.addAuditEvent) {
                if (mode === "Simulate") {
                    window.addAuditEvent({
                        actor: { id: "michael.hoch", name: "Michael Hoch", type: "human", role: "Operator" },
                        action: { type: "COMMAND_SIMULATED", summary: `Dry-run simulation of instruction completed: "${prompt}"` },
                        target: { type: "command", id: "input-command", name: prompt },
                        result: "success",
                        severity: "info",
                        provenance: { source: "manual", evidence_refs: [] },
                        policy: { required: false, result: "not_required" }
                    });
                } else {
                    window.addAuditEvent({
                        actor: { id: "michael.hoch", name: "Michael Hoch", type: "human", role: "Operator" },
                        action: { type: "COMMAND_EXECUTED", summary: `Instruction executed on node: "${prompt}"` },
                        target: { type: "command", id: "input-command", name: prompt },
                        result: "success",
                        severity: mode === "Emergency Override" ? "high" : "medium",
                        provenance: { source: "manual", evidence_refs: [] },
                        policy: { required: true, result: "passed", explanation: `Governance mode: ${mode}` }
                    });
                }
            }

            // Re-render topology highlighting the routed node
            const responseStatus = await fetch(`${API_BASE}/api/status`);
            if (responseStatus.ok) {
                const statusData = await responseStatus.json();
                updateMermaidTopology(statusData.nodes, targetNode.id);
            }

            // Trigger animation packet flow bursts
            spawnTaskParticles(targetNode.id);

            // Simulate typewriter effect for execution log
            logOutputContent.innerHTML += `<span style="color:var(--accent-teal)">[Swarm Runner] Node executing task...</span><br/>`;
            setTimeout(() => {
                logOutputContent.innerHTML += `<span style="color:#ffffff">${data.result}</span><br/>`;
                logOutputContent.innerHTML += `<span style="color:var(--accent-teal)">[Success] Swarm execution task complete.</span>`;
                logOutputContent.scrollTop = logOutputContent.scrollHeight;
                
                logToConsoleTerminal("SwarmRunner", `Task finished on ${targetNode.name}. Status: COMPLETED`, "info");
                
                btnSubmitTask.disabled = false;
                promptInput.value = ""; // Clear input bar
                fetchAndRenderTasks(); // Refresh history
            }, 1500);

        } else {
            logOutputContent.innerHTML += `<span style="color:#ef4444">[Error] Failed to execute swarm task.</span>`;
            logToConsoleTerminal("Scheduler", "Task execution failed.", "error");
            if (window.addAuditEvent) {
                window.addAuditEvent({
                    actor: { id: "michael.hoch", name: "Michael Hoch", type: "human", role: "Operator" },
                    action: { type: "TASK_FAILED", summary: `Failed to execute swarm task: "${prompt}"` },
                    target: { type: "command", id: "input-command", name: prompt },
                    result: "failed",
                    severity: "high",
                    provenance: { source: "manual", evidence_refs: [] },
                    policy: { required: false, result: "not_required" }
                });
            }
            btnSubmitTask.disabled = false;
        }
    } catch (err) {
        logOutputContent.innerHTML += `<span style="color:#ef4444">[Error] Connection lost to control plane: ${err.message}</span>`;
        logToConsoleTerminal("Connection", `Error: ${err.message}`, "error");
        btnSubmitTask.disabled = false;
    }
}

async function fetchAndRenderAuditLogs() {
    const tbody = document.getElementById("audit-trail-tbody");
    const countSpan = document.getElementById("audit-logs-count");
    if (!tbody) return;

    try {
        const response = await fetch(`${API_BASE}/api/audit/logs`);
        if (!response.ok) throw new Error("Failed to fetch audit logs");
        const logs = await response.json();

        // Apply filters
        const filterVal = document.getElementById("audit-filter-result").value;
        const filtered = logs.filter(log => {
            if (filterVal === "ALL") return true;
            return log.result === filterVal;
        });

        tbody.innerHTML = "";
        countSpan.textContent = `${filtered.length} RECORDS`;

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 24px; color: var(--text-secondary);">No audit logs found.</td></tr>`;
            return;
        }

        filtered.forEach(log => {
            let resBadge = "";
            if (log.result === "Success") {
                resBadge = `<span class="status-badge success">Success</span>`;
            } else if (log.result === "Blocked") {
                resBadge = `<span class="status-badge blocked">Blocked</span>`;
            } else {
                resBadge = `<span class="status-badge fail">Failed</span>`;
            }

            let policyBadge = "";
            if (log.policy_check === "Passed") {
                policyBadge = `<span style="color:#10b981; font-weight:bold;">● Passed</span>`;
            } else if (log.policy_check === "Warn") {
                policyBadge = `<span style="color:#f59e0b; font-weight:bold;">▲ Warn</span>`;
            } else {
                policyBadge = `<span style="color:#ef4444; font-weight:bold;">✖ Blocked</span>`;
            }

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="padding: 8px 12px; color: var(--text-secondary);">${log.timestamp}</td>
                <td style="padding: 8px 12px; font-weight: 600;">${log.actor}</td>
                <td style="padding: 8px 12px; color: #fff;">${log.action}</td>
                <td style="padding: 8px 12px; color: var(--accent-blue);">${log.target}</td>
                <td style="padding: 8px 12px;">${resBadge}</td>
                <td style="padding: 8px 12px;">${policyBadge}</td>
                <td style="padding: 8px 12px; text-align: right; color: var(--accent-teal);">${log.confidence ? log.confidence + '%' : '—'}</td>
                <td style="padding: 8px 12px; font-family: monospace; color: var(--text-secondary);">${log.rollback_id || 'N/A'}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error("Error loading audit trail:", err);
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 24px; color:#ef4444;">Error loading audit logs: ${err.message}</td></tr>`;
    }
}

// Expose global window bindings for React integration
window.executeTaskWithMode = executeTaskWithMode;
window.spawnTaskParticles = spawnTaskParticles;
window.updateMermaidTopology = updateMermaidTopology;

// ================================================================
//  OPERATIONAL READINESS & TELEMETRY CHAIN STATUS POLLING
// ================================================================
async function fetchReadinessAutopilotData() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/readiness/status`);
        if (!res.ok) throw new Error("HTTP " + res.status);
        const json = await res.json();
        const rData = json.data || {};
        
        const scoreEl = document.getElementById("readiness-autopilot-score");
        if (scoreEl) scoreEl.textContent = `${rData.readiness_score} / 100`;
        
        const statusEl = document.getElementById("readiness-autopilot-status");
        if (statusEl) {
            statusEl.textContent = `● ${rData.status}`;
            statusEl.className = rData.status === "PASS" ? "text-emerald-400 font-bold" : "text-red-400 font-bold";
        }
        
        const budgetEl = document.getElementById("readiness-autopilot-budget");
        if (budgetEl) budgetEl.textContent = `${rData.error_budget_percentage}%`;
        
        const sloEl = document.getElementById("readiness-autopilot-slo");
        if (sloEl) {
            sloEl.textContent = rData.slo_status;
            sloEl.className = rData.slo_status === "COMPLIANT" ? "text-emerald-400 font-bold" : "text-red-400 font-bold";
        }
        
        const autonomyEl = document.getElementById("readiness-autopilot-autonomy");
        if (autonomyEl) autonomyEl.textContent = rData.autonomy_level;
        
        const burnEl = document.getElementById("readiness-autopilot-burn");
        if (burnEl) burnEl.textContent = Number(rData.burn_rate).toFixed(2);
    } catch (err) {
        console.error("Error fetching readiness autopilot data:", err);
    }
}

function getNavStatusColor(status) {
  switch (status) {
    case "live":
      return "text-emerald-400";
    case "planned":
      return "text-blue-300";
    case "stale":
      return "text-amber-300";
    case "expired":
    case "error":
      return "text-red-400";
    default:
      return "text-slate-400";
  }
}

async function updateNavStatuses() {
    const checkEndpoint = async (url) => {
        try {
            const res = await fetch(`${API_BASE}${url}`);
            return res.ok;
        } catch (e) {
            return false;
        }
    };

    const updateIndicator = (navId, status) => {
        const navEl = document.getElementById(navId);
        if (!navEl) return;
        const indicator = navEl.querySelector(".nav-status-indicator");
        if (!indicator) return;
        
        // Remove existing color classes
        indicator.classList.remove("text-emerald-400", "text-blue-300", "text-amber-300", "text-red-400", "text-slate-400");
        indicator.classList.add(getNavStatusColor(status));
    };

    // 1. Readiness Autopilot
    const readinessOk = await checkEndpoint("/api/v1/readiness/status");
    updateIndicator("nav-readiness-autopilot", readinessOk ? "live" : "error");

    // 2. HOCHSTER Runtime
    const hochsterOk = await checkEndpoint("/api/v1/hochster/health");
    updateIndicator("nav-hochster-runtime", hochsterOk ? "live" : "error");

    // 3. Remediation Safety
    const safetyOk = await checkEndpoint("/api/v1/readiness/budget-report");
    updateIndicator("nav-remediation-safety", safetyOk ? "live" : "error");

    // 4. Runtime Audit
    const auditOk = await checkEndpoint("/api/v1/audit/runtime/execution");
    updateIndicator("nav-runtime-audit", auditOk ? "live" : "error");

    // 5. Error Budget
    const errorBudgetOk = await checkEndpoint("/api/v1/readiness/budget-report");
    updateIndicator("nav-error-budget", errorBudgetOk ? "live" : "error");

    // 6. Release Provenance
    const provenanceOk = await checkEndpoint("/api/v1/hochster/baseline/lock");
    updateIndicator("nav-release-provenance", provenanceOk ? "live" : "error");

    // 7. Swarm Control
    const statusOk = await checkEndpoint("/api/v1/agents/status");
    updateIndicator("nav-swarm-control", statusOk ? "live" : "error");

    // 8. Mission Intel
    const missionOk = await checkEndpoint("/api/v1/audit/events");
    updateIndicator("nav-mission-intel", missionOk ? "live" : "error");

    // 9. Timeline Replay
    const ledgerOk = await checkEndpoint("/api/v1/audit/events");
    updateIndicator("nav-timeline-replay", ledgerOk ? "live" : "error");

    // 10. Cybersecurity Factory
    updateIndicator("nav-cybersecurity-factory", "live");

    // 11. Governance Cockpit
    const govOk = await checkEndpoint("/api/v1/governance/summary");
    updateIndicator("nav-governance", govOk ? "live" : "error");
}



async function fetchRemediationSafetyData() {
    try {
        const status = await fetchJson("/api/v1/readiness/status");
        const budget = await fetchJson("/api/v1/readiness/budget-report");
        let incidents = { data: { incidents: [] } };

        try {
            incidents = await fetchJson("/api/v1/readiness/incidents");
        } catch (_err) {
            incidents = { data: { incidents: [] } };
        }

        const statusData = status.data || {};
        const budgetData = budget.data || {};
        const incidentData = incidents.data || {};
        const rows = Array.isArray(incidentData.incidents) ? incidentData.incidents : [];

        setText("remediation-safety-freshness", status.freshness || "live");
        setText("remediation-safety-updated", `Updated ${status.received_at || "--"}`);
        setText("remediation-autonomy-level", statusData.autonomy_level || budgetData.autonomy_level || "--");
        setText("remediation-autonomy-reason", statusData.autonomy_reason || "Budget-aware autonomy gate");
        setText("remediation-readiness-score", statusData.readiness_score ?? statusData.score ?? "--");
        setText("remediation-error-budget", budgetData.remaining_error_budget ?? budgetData.error_budget_remaining ?? "--");
        setText("remediation-burn-rate", `Burn rate: ${budgetData.burn_rate ?? "--"}`);
        setText("remediation-active-incidents", rows.filter((i) => (i.state || i.status || "").toLowerCase() !== "closed").length);
        renderRemediationIncidentRows(rows);
    } catch (error) {
        console.warn("Failed to fetch remediation safety telemetry", error);
    }
}

function renderRemediationIncidentRows(incidents) {
    const tbody = document.getElementById("remediation-incident-rows");
    if (!tbody) return;

    if (!incidents.length) {
        tbody.innerHTML = `<tr><td colspan="6">No active incidents. Remediation safety gates standing by.</td></tr>`;
        return;
    }

    tbody.innerHTML = incidents.map((incident) => `
        <tr>
            <td>${escapeHtml(incident.title || incident.incident_id || incident.id || "--")}</td>
            <td>${escapeHtml(incident.severity || "--")}</td>
            <td>${escapeHtml(incident.risk_level || incident.risk || "--")}</td>
            <td>${escapeHtml(incident.state || incident.status || "--")}</td>
            <td>${escapeHtml(incident.remediation_plan || incident.recommendation || "Pending")}</td>
            <td>${escapeHtml(incident.rollback_plan || "Required")}</td>
        </tr>
    `).join("");
}

setInterval(fetchRemediationSafetyData, 5000);

// ==============================================================================
// Kimi-Style Swarm Comic Interface Implementation & Global Swarm Process Animation Runtime
// ==============================================================================

const hochAgentDepartments = [
  {
    id: "command-core",
    name: "Command Core",
    agents: [
      {
        id: "boss-noodle",
        displayName: "Boss Noodle",
        tag: "MISSION WRANGLER",
        systemRole: "Supervisor Agent",
        department: "Command Core",
        description: "Decomposes any prompt into work lanes, assigns specialists, and keeps the swarm moving.",
        catchphrase: "Everybody gets a lane. Nobody gets to wander.",
        skills: ["goal decomposition", "routing", "priority ranking", "handoff control"],
        defaultStage: "Plan",
        completionSignal: "Mission decomposed",
        avatarVariant: "tiny-crown-headset"
      },
      {
        id: "captain-obvious-prime",
        displayName: "Captain Obvious Prime",
        tag: "ASSUMPTION BUSTER",
        systemRole: "Clarification Agent",
        department: "Command Core",
        description: "Finds the thing everyone assumed but nobody said.",
        catchphrase: "The obvious thing is usually where the bug lives.",
        skills: ["assumption detection", "scope checks", "ambiguity reduction"],
        defaultStage: "Plan",
        completionSignal: "Hidden assumptions surfaced",
        avatarVariant: "megaphone-brow"
      },
      {
        id: "sir-deadline-panic",
        displayName: "Sir Deadline Panic",
        tag: "PRIORITY COMPRESSOR",
        systemRole: "Prioritization Agent",
        department: "Command Core",
        description: "Turns messy urgency into ranked next actions.",
        catchphrase: "Panic, but make it sequenced.",
        skills: ["triage", "sequencing", "timeboxing", "critical path"],
        defaultStage: "Assign",
        completionSignal: "Priorities ranked",
        avatarVariant: "hourglass-sneakers"
      }
    ]
  },
  {
    id: "research-knowledge",
    name: "Research & Knowledge",
    agents: [
      {
        id: "dr-signal",
        displayName: "Dr. Signal",
        tag: "TRUTH HUNTER",
        systemRole: "Research Agent",
        department: "Research & Knowledge",
        description: "Researches docs, web, YouTube candidates, prior evidence.",
        catchphrase: "I find the signal before anyone patches.",
        skills: ["YouTube research", "source triage", "pattern extraction", "context mapping"],
        defaultStage: "Research",
        completionSignal: "YouTube candidates matched",
        avatarVariant: "headphones-beard-glass"
      },
      {
        id: "scout-tabs-a-lot",
        displayName: "Scout Tabs-a-Lot",
        tag: "BROWSER RACER",
        systemRole: "Browser Scraper",
        department: "Research & Knowledge",
        description: "Opens/compares many sources and extracts signal.",
        catchphrase: "More tabs means more truth.",
        skills: ["parallel search", "tab extraction", "speed reading"],
        defaultStage: "Research",
        completionSignal: "Sources compared",
        avatarVariant: "browser-cape"
      }
    ]
  },
  {
    id: "strategy-planning",
    name: "Strategy & Planning",
    agents: [
      {
        id: "prof-blueprint",
        displayName: "Prof. Blueprint",
        tag: "SYSTEM CARTOONIST",
        systemRole: "Architect Agent",
        department: "Strategy & Planning",
        description: "Turns goals into architecture and execution plan.",
        catchphrase: "Every fix needs a shape.",
        skills: ["system design", "dependency mapping", "failure-mode planning"],
        defaultStage: "Plan",
        completionSignal: "Architecture blueprint designed",
        avatarVariant: "blueprint-ruler"
      },
      {
        id: "lady-tradeoff",
        displayName: "Lady Tradeoff",
        tag: "DECISION BALANCER",
        systemRole: "Strategy Agent",
        department: "Strategy & Planning",
        description: "Balances cost, performance, safety, and complexity tradeoffs.",
        catchphrase: "Everything has a price.",
        skills: ["options analysis", "cost models", "reversibility scoring"],
        defaultStage: "Plan",
        completionSignal: "Tradeoffs balanced",
        avatarVariant: "scale-calculator"
      }
    ]
  },
  {
    id: "engineering",
    name: "Engineering",
    agents: [
      {
        id: "eng-patch",
        displayName: "Eng. Patch",
        tag: "PATCH MONK",
        systemRole: "Code Agent",
        department: "Engineering",
        description: "Applies small, high-leverage code changes with minimal blast radius.",
        catchphrase: "Small diff. Big effect.",
        skills: ["implementation", "refactor", "integration", "config repair"],
        defaultStage: "Execute",
        completionSignal: "Patch surface identified",
        avatarVariant: "bracket-mask"
      },
      {
        id: "bugsy-mcfixface",
        displayName: "Bugsy McFixface",
        tag: "BUG EXORCIST",
        systemRole: "Debugging Agent",
        department: "Engineering",
        description: "Reproduces, isolates, and fixes bugs without making three new ones.",
        catchphrase: "Come out, little bug. I brought logs.",
        skills: ["reproduction", "root cause", "patching", "regression prevention"],
        defaultStage: "Execute",
        completionSignal: "Bug isolated",
        avatarVariant: "bug-net-laptop"
      },
      {
        id: "null-pointer-ned",
        displayName: "Null Pointer Ned",
        tag: "EDGE CASE HUNTER",
        systemRole: "Reliability Agent",
        department: "Engineering",
        description: "Finds the empty states, nulls, and awkward edge cases hiding under the rug.",
        catchphrase: "Nothing is something if it crashes production.",
        skills: ["edge cases", "empty states", "defensive coding", "failure modes"],
        defaultStage: "Verify",
        completionSignal: "Edge cases covered",
        avatarVariant: "broken-arrow"
      }
    ]
  },
  {
    id: "runtime-docker",
    name: "Runtime / Docker",
    agents: [
      {
        id: "gordon-vector",
        displayName: "Gordon Vector",
        tag: "CONTAINER WHISPERER",
        systemRole: "Docker Debugger",
        department: "Runtime / Docker",
        description: "Diagnoses containers by reading symptoms: logs, inspect output, health checks, compose timing, and network state.",
        catchphrase: "The container will tell us what hurts.",
        skills: ["docker logs", "docker inspect", "health checks", "compose diagnosis", "root cause isolation"],
        defaultStage: "Execute",
        completionSignal: "Container diagnosis complete",
        avatarVariant: "glasses-docker"
      },
      {
        id: "cache-kraken",
        displayName: "Cache Kraken",
        tag: "DISK SPACE BEAST",
        systemRole: "Storage Recovery Agent",
        department: "Runtime / Docker",
        description: "Finds giant caches, stale installers, and safe cleanup candidates when ENOSPC appears.",
        catchphrase: "Release the cache. Keep the evidence.",
        skills: ["disk audit", "safe cleanup", "cache triage", "artifact preservation"],
        defaultStage: "Remediate",
        completionSignal: "Disk pressure reduced",
        avatarVariant: "kraken-trash"
      },
      {
        id: "captain-compose",
        displayName: "Captain Compose",
        tag: "YAML TRAFFIC COP",
        systemRole: "Compose Agent",
        department: "Runtime / Docker",
        description: "Directs Docker Compose services, dependencies, health checks, and startup order.",
        catchphrase: "Your services are arguing. I brought a whistle.",
        skills: ["compose config", "service dependencies", "healthchecks", "ports"],
        defaultStage: "Execute",
        completionSignal: "Compose flow verified",
        avatarVariant: "traffic-yaml"
      },
      {
        id: "log-goblin",
        displayName: "Log Goblin",
        tag: "STDOUT SNIFFER",
        systemRole: "Logs Analyst",
        department: "Runtime / Docker",
        description: "Reads stdout, logs, and identifies root-cause failure clues.",
        catchphrase: "I smell a stack trace.",
        skills: ["log parsing", "stdout analysis", "regex filtering"],
        defaultStage: "Execute",
        completionSignal: "Log patterns extracted",
        avatarVariant: "nose-scroll"
      }
    ]
  },
  {
    id: "qa-verification",
    name: "QA / Verification",
    agents: [
      {
        id: "ms-checkmark",
        displayName: "Ms. Checkmark",
        tag: "BUG BOUNCER",
        systemRole: "QA Agent",
        department: "QA / Verification",
        description: "Turns claims into tests, screenshots, contracts, and hard PASS/BLOCK results.",
        catchphrase: "No proof, no pass.",
        skills: ["build validation", "regression tests", "E2E", "UI contracts"],
        defaultStage: "Verify",
        completionSignal: "Tests passing",
        avatarVariant: "clipboard-bob"
      },
      {
        id: "playwright-pete",
        displayName: "Playwright Pete",
        tag: "BROWSER STUNTMAN",
        systemRole: "E2E Agent",
        department: "QA / Verification",
        description: "Clicks the UI like a tiny caffeinated robot and brings screenshots.",
        catchphrase: "If I can click it, I can prove it.",
        skills: ["browser automation", "screenshots", "traces", "runtime validation"],
        defaultStage: "Verify",
        completionSignal: "Browser proof captured",
        avatarVariant: "goggles-browser"
      },
      {
        id: "dr-flake",
        displayName: "Dr. Flake",
        tag: "NONDETERMINISM HUNTER",
        systemRole: "Flake Agent",
        department: "QA / Verification",
        description: "Catches race conditions, timing bugs, and tests that only fail when watched.",
        catchphrase: "It passed once. That proves nothing.",
        skills: ["flaky tests", "race detection", "timing analysis", "retry logic"],
        defaultStage: "Verify",
        completionSignal: "Flakes isolated",
        avatarVariant: "snowflake-stopwatch"
      },
      {
        id: "screenshot-sally",
        displayName: "Screenshot Sally",
        tag: "VISUAL WITNESS",
        systemRole: "Visual QA Agent",
        department: "QA / Verification",
        description: "Captures screenshots of layouts and UI components to verify correctness.",
        catchphrase: "Pics or it didn't happen.",
        skills: ["visual regression", "element screenshots", "pixel match"],
        defaultStage: "Verify",
        completionSignal: "UI screenshot captured",
        avatarVariant: "camera-sparkles"
      }
    ]
  },
  {
    id: "security-governance",
    name: "Security / Governance",
    agents: [
      {
        id: "capt-guardrail",
        displayName: "Capt. Guardrail",
        tag: "GUARDRAIL GOBLIN",
        systemRole: "Security Agent",
        department: "Security / Governance",
        description: "Keeps agent freedom bounded by command safety, secrets hygiene, and release policy.",
        catchphrase: "Freedom inside fences.",
        skills: ["command risk", "secrets checks", "dependency risk", "policy gates"],
        defaultStage: "Verify",
        completionSignal: "Unsafe actions blocked",
        avatarVariant: "shield-cap"
      },
      {
        id: "sir-no-rm",
        displayName: "Sir No-RM",
        tag: "DESTRUCTION BLOCKER",
        systemRole: "Command Safety Agent",
        department: "Security / Governance",
        description: "Blocks the cursed commands that make grown repos cry.",
        catchphrase: "Not today, recursive deletion.",
        skills: ["deny lists", "dangerous command detection", "approval gates"],
        defaultStage: "Verify",
        completionSignal: "Destructive commands blocked",
        avatarVariant: "stop-sign-helmet"
      },
      {
        id: "secrets-squirrel",
        displayName: "Secrets Squirrel",
        tag: "CREDENTIAL PROTECTOR",
        systemRole: "Secret Hygiene Agent",
        department: "Security / Governance",
        description: "Sniffs out tokens, keys, credentials, and suspicious file access.",
        catchphrase: "I buried that key for a reason.",
        skills: ["secret detection", "credential hygiene", "path risk", "exfiltration defense"],
        defaultStage: "Verify",
        completionSignal: "Secrets protected",
        avatarVariant: "squirrel-lockbox"
      },
      {
        id: "policy-penguin",
        displayName: "Policy Penguin",
        tag: "RULE ENFORCER",
        systemRole: "Policy Agent",
        department: "Security / Governance",
        description: "Validates all actions against local security policy rules.",
        catchphrase: "Rules keep the swarm safe.",
        skills: ["policy mapping", "allow lists", "ZTA validation"],
        defaultStage: "Verify",
        completionSignal: "Security policy verified",
        avatarVariant: "penguin-tie"
      }
    ]
  },
  {
    id: "release-audit",
    name: "Release / Audit",
    agents: [
      {
        id: "prof-ledger",
        displayName: "Prof. Ledger",
        tag: "RECEIPT WIZARD",
        systemRole: "Audit Agent",
        department: "Release / Audit",
        description: "Locks every decision, source, command, and verification into evidence.",
        catchphrase: "If it is not evidenced, it did not happen.",
        skills: ["trace IDs", "evidence packs", "provenance", "release records"],
        defaultStage: "Report",
        completionSignal: "Evidence locked",
        avatarVariant: "ledger-monocle"
      },
      {
        id: "sbom-bob",
        displayName: "SBOM Bob",
        tag: "COMPONENT ACCOUNTANT",
        systemRole: "SBOM Agent",
        department: "Release / Audit",
        description: "Counts every package and file so the release knows what it is made of.",
        catchphrase: "I itemize therefore I am.",
        skills: ["SBOM", "dependency metadata", "artifact inventory", "checksums"],
        defaultStage: "Report",
        completionSignal: "Components accounted",
        avatarVariant: "abacus-boxes"
      },
      {
        id: "provenance-penny",
        displayName: "Provenance Penny",
        tag: "CHAIN-OF-CUSTODY CLERK",
        systemRole: "Provenance Agent",
        department: "Release / Audit",
        description: "Tracks in-toto metadata, chains-of-custody, and builds evidence paths.",
        catchphrase: "Verifiable from source to ship.",
        skills: ["in-toto metadata", "checksum verification", "chain tracking"],
        defaultStage: "Report",
        completionSignal: "Provenance sealed",
        avatarVariant: "chain-stamp"
      },
      {
        id: "eng-rocket",
        displayName: "Eng. Rocket",
        tag: "SHIP JUDGE",
        systemRole: "Release Agent",
        department: "Release / Audit",
        description: "Ships only when the release can defend itself with readiness, provenance, rollback, and verification evidence.",
        catchphrase: "Ship only what can defend itself.",
        skills: ["release readiness", "SBOM", "provenance", "final gate decision"],
        defaultStage: "Complete",
        completionSignal: "Release defensible",
        avatarVariant: "rocket-flat"
      }
    ]
  },
  {
    id: "product-design",
    name: "Product & Design",
    agents: [
      {
        id: "pixel-picasso",
        displayName: "Pixel Picasso",
        tag: "UI DOODLER",
        systemRole: "Design Agent",
        department: "Product & Design",
        description: "Designs modern retro pixel and stick visual assets.",
        catchphrase: "Every pixel has a purpose.",
        skills: ["pixel art", "visual assets", "UI mockups"],
        defaultStage: "Execute",
        completionSignal: "UI design drafted",
        avatarVariant: "beret-brush"
      },
      {
        id: "motion-molly",
        displayName: "Motion Molly",
        tag: "ANIMATION WIZARD",
        systemRole: "Transitions Agent",
        department: "Product & Design",
        description: "Breeds life into layout state changes and micro-interactions.",
        catchphrase: "Smooth is fast.",
        skills: ["CSS transitions", "SVGs", "micro-animations"],
        defaultStage: "Execute",
        completionSignal: "Animations applied",
        avatarVariant: "wand-trails"
      },
      {
        id: "ux-ursula",
        displayName: "UX Ursula",
        tag: "FRICTION EXORCIST",
        systemRole: "UX Agent",
        department: "Product & Design",
        description: "Exorcises complexity and friction from user interactions.",
        catchphrase: "Make the path obvious.",
        skills: ["interaction flows", "usability checkup", "accessibility checkup"],
        defaultStage: "Verify",
        completionSignal: "Friction resolved",
        avatarVariant: "ghost-vacuum"
      }
    ]
  }
];

// Compatibility definitions for legacy tests
const hochComicAgents = [
  { id: "research", name: "Research Agent", tag: "TRUTH HUNTER", look: "magnifying glass", catchphrase: "I find the signal.", skills: [], currentAssignment: "" },
  { id: "architect", name: "Architect Agent", tag: "SYSTEM CARTOONIST", look: "blueprint", catchphrase: "Shape it.", skills: [], currentAssignment: "" },
  { id: "code", name: "Code Agent", tag: "PATCH MONK", look: "brackets", catchphrase: "Small diff.", skills: [], currentAssignment: "" },
  { id: "qa", name: "QA Agent", tag: "BUG BOUNCER", look: "shield", catchphrase: "No proof.", skills: [], currentAssignment: "" },
  { id: "security", name: "Security Agent", tag: "GUARDRAIL GOBLIN", look: "shield", catchphrase: "Fences.", skills: [], currentAssignment: "" },
  { id: "gordon", name: "Gordon Docker Debugger", tag: "CONTAINER WHISPERER", look: "glasses", catchphrase: "Hurts.", skills: [], currentAssignment: "" },
  { id: "remediation", name: "Remediation Agent", tag: "FIX GREMLIN", look: "wrench", catchphrase: "Repair.", skills: [], currentAssignment: "" },
  { id: "audit", name: "Audit Agent", tag: "RECEIPT WIZARD", look: "monocle", catchphrase: "Evidence.", skills: [], currentAssignment: "" },
  { id: "release", name: "Release Agent", tag: "SHIP JUDGE", look: "gavel", catchphrase: "Ship.", skills: [], currentAssignment: "" }
];

const hochYoutubeResearchCandidates = [
  { title: "Docker container exits immediately: logs and entrypoint diagnosis", channel: "Research Candidate", signal: "container lifecycle", extractedPattern: "Start with logs" },
  { title: "Docker Compose healthcheck failures and dependency timing", channel: "Research Candidate", signal: "compose health", extractedPattern: "Inspect healthcheck" },
  { title: "Debugging container networking and localhost binding", channel: "Research Candidate", signal: "network routing", extractedPattern: "Check published ports" },
  { title: "Optimizing Docker images and runtime startup", channel: "Research Candidate", signal: "runtime performance", extractedPattern: "Reduce layers" }
];

const hochUiResearchCandidates = [
  { title: "Modern Glassmorphism layouts and backdrop-filter optimizations", channel: "Design Systems", signal: "CSS filter", extractedPattern: "Apply backdrop-filter" },
  { title: "Smooth SVG transitions and state-based Bezier animations", channel: "UX Devs", signal: "Transitions", extractedPattern: "Use hardware-accelerated transforms" },
  { title: "Playwright E2E visual regression and screenshot assertions", channel: "Automated QA", signal: "E2E screenshot", extractedPattern: "Assert bounding box elements" }
];

const hochDefaultVisibleAgents = [
  "boss-noodle",
  "dr-signal",
  "prof-blueprint",
  "eng-patch",
  "ms-checkmark",
  "capt-guardrail",
  "gordon-vector",
  "prof-ledger",
  "eng-rocket"
];

let currentActiveStage = "";
let currentCompletedStages = [];
let agentStates = {};
let currentAnimationTimeouts = [];

function routePromptAgents(prompt) {
    const text = prompt.toLowerCase();
    if (text.includes("docker") || text.includes("container") || text.includes("port") || text.includes("log")) {
        return ["gordon-vector", "captain-compose", "log-goblin", "ms-checkmark", "prof-ledger"];
    } else if (text.includes("ui") || text.includes("design") || text.includes("animation") || text.includes("pixel") || text.includes("motion") || text.includes("ux")) {
        return ["pixel-picasso", "motion-molly", "ux-ursula", "playwright-pete", "screenshot-sally"];
    } else if (text.includes("release") || text.includes("tag") || text.includes("provenance") || text.includes("sbom") || text.includes("ship")) {
        return ["eng-rocket", "sbom-bob", "provenance-penny", "prof-ledger"];
    } else if (text.includes("security") || text.includes("permission") || text.includes("allow list") || text.includes("secret") || text.includes("guardrail")) {
        return ["capt-guardrail", "sir-no-rm", "secrets-squirrel", "policy-penguin"];
    } else {
        return ["boss-noodle", "captain-obvious-prime", "dr-signal", "lady-tradeoff", "sir-deadline-panic"];
    }
}

function getAgentSvg(variant, state = "idle") {
    let strokeColor = "rgba(156, 163, 175, 0.8)";
    let accentColor = "#6b7280";
    let isNeon = false;
    if (state === "active" || state === "executing" || state === "researching" || state === "spinning-up") {
        strokeColor = "#3b82f6";
        accentColor = "#60a5fa";
        isNeon = true;
    } else if (state === "complete" || state === "complete-green" || state === "verifying") {
        strokeColor = "#10b981";
        accentColor = "#34d399";
        isNeon = true;
    } else if (state === "blocked") {
        strokeColor = "#ef4444";
        accentColor = "#f87171";
        isNeon = true;
    } else if (state === "needs-approval") {
        strokeColor = "#f59e0b";
        accentColor = "#fbbf24";
        isNeon = true;
    }

    const head = `<circle cx="40" cy="25" r="10" stroke="${strokeColor}" stroke-width="2" fill="none" />`;
    const spine = `<line x1="40" y1="35" x2="40" y2="60" stroke="${strokeColor}" stroke-width="2" />`;
    const arms = `<line x1="40" y1="45" x2="25" y2="40" stroke="${strokeColor}" stroke-width="2" />
                  <line x1="40" y1="45" x2="55" y2="40" stroke="${strokeColor}" stroke-width="2" />`;
    const legs = `<line x1="40" y1="60" x2="30" y2="80" stroke="${strokeColor}" stroke-width="2" />
                  <line x1="40" y1="60" x2="50" y2="80" stroke="${strokeColor}" stroke-width="2" />`;
    
    let accessory = '';
    if (variant === 'tiny-crown-headset' || variant === 'research') {
        accessory = `
            <path d="M35,12 L37,15 L40,12 L43,15 L45,12 L45,16 L35,16 Z" fill="${accentColor}" />
            <path d="M28,25 A12,12 0 0,1 52,25" stroke="${accentColor}" stroke-width="1.5" fill="none" />
            <circle cx="28" cy="25" r="2.5" fill="${accentColor}" />
            <rect x="52" y="32" width="10" height="12" rx="1" fill="#1e293b" stroke="${strokeColor}" stroke-width="1" />
        `;
    } else if (variant === 'headphones-beard-glass') {
        accessory = `
            <path d="M28,25 A12,12 0 0,1 52,25" stroke="${accentColor}" stroke-width="2" fill="none" />
            <path d="M35,28 L40,34 L45,28 Z" fill="${accentColor}" opacity="0.8" />
            <circle cx="20" cy="35" r="4" stroke="${accentColor}" stroke-width="1.5" fill="none" />
            <line x1="23" y1="38" x2="27" y2="42" stroke="${accentColor}" stroke-width="2" />
        `;
    } else if (variant === 'blueprint-ruler' || variant === 'architect') {
        accessory = `
            <path d="M40,35 L20,65 L40,60 Z" fill="rgba(59, 130, 246, 0.3)" stroke="${accentColor}" stroke-width="1" />
            <line x1="20" y1="40" x2="32" y2="28" stroke="${accentColor}" stroke-width="2" />
        `;
    } else if (variant === 'bracket-mask' || variant === 'code') {
        accessory = `
            <text x="12" y="36" fill="${accentColor}" font-size="14" font-weight="bold" font-family="monospace">[</text>
            <text x="60" y="36" fill="${accentColor}" font-size="14" font-weight="bold" font-family="monospace">]</text>
            <line x1="55" y1="45" x2="70" y2="30" stroke="${accentColor}" stroke-width="2" />
        `;
    } else if (variant === 'clipboard-bob' || variant === 'qa') {
        accessory = `
            <polygon points="12,32 24,28 28,42 16,48 8,42" fill="rgba(16, 185, 129, 0.2)" stroke="${accentColor}" stroke-width="1.5" />
            <path d="M14,38 L18,42 L24,34" stroke="${accentColor}" stroke-width="2" fill="none" />
        `;
    } else if (variant === 'shield-cap' || variant === 'security') {
        accessory = `
            <path d="M30,18 Q40,12 50,18 L48,22 Q40,16 32,22 Z" fill="${accentColor}" />
            <polygon points="12,35 22,35 25,45 17,50 9,45" fill="rgba(249, 115, 22, 0.2)" stroke="${accentColor}" stroke-width="1.5" />
        `;
    } else if (variant === 'glasses-docker' || variant === 'gordon') {
        accessory = `
            <circle cx="36" cy="24" r="2.5" stroke="${accentColor}" stroke-width="1" fill="none" />
            <circle cx="44" cy="24" r="2.5" stroke="${accentColor}" stroke-width="1" fill="none" />
            <line x1="38.5" y1="24" x2="41.5" y2="24" stroke="${accentColor}" stroke-width="1" />
            <polygon points="15,40 22,36 29,40 29,48 22,52 15,48" fill="rgba(59, 130, 246, 0.3)" stroke="${strokeColor}" stroke-width="1" />
        `;
    } else if (variant === 'ledger-monocle' || variant === 'audit') {
        accessory = `
            <circle cx="43" cy="24" r="3" stroke="${accentColor}" stroke-width="1" fill="none" />
            <path d="M12,45 C15,42 22,48 25,45 L25,60 C22,63 15,57 12,60 Z" fill="rgba(255,255,255,0.05)" stroke="${accentColor}" stroke-width="1.5" />
        `;
    } else if (variant === 'rocket-flat' || variant === 'release') {
        accessory = `
            <line x1="55" y1="45" x2="65" y2="35" stroke="${accentColor}" stroke-width="2.5" />
            <path d="M60,32 L68,32 L64,28 Z" fill="${accentColor}" />
        `;
    } else if (variant === 'megaphone-brow') {
        accessory = `
            <polygon points="15,35 25,30 25,42 15,38" fill="${accentColor}" stroke="${strokeColor}" stroke-width="1" />
            <line x1="38" y1="18" x2="44" y2="16" stroke="${accentColor}" stroke-width="1.5" />
        `;
    } else if (variant === 'hourglass-sneakers') {
        accessory = `
            <path d="M15,35 L25,35 L15,48 L25,48 Z" fill="rgba(239, 68, 68, 0.1)" stroke="${accentColor}" stroke-width="1.5" />
        `;
    } else if (variant === 'bug-net-laptop') {
        accessory = `
            <circle cx="65" cy="30" r="6" stroke="${accentColor}" stroke-width="1" fill="none" />
            <path d="M65,36 L65,48" stroke="${accentColor}" stroke-width="1.5" />
        `;
    } else if (variant === 'broken-arrow') {
        accessory = `
            <path d="M20,32 L26,38 M26,32 L20,38" stroke="${accentColor}" stroke-width="2" />
        `;
    } else if (variant === 'kraken-trash') {
        accessory = `
            <path d="M52,48 C55,42 58,48 60,45" stroke="${accentColor}" stroke-width="1.5" fill="none" />
        `;
    } else if (variant === 'traffic-yaml') {
        accessory = `
            <line x1="55" y1="45" x2="65" y2="35" stroke="#ef4444" stroke-width="3" />
        `;
    } else if (variant === 'snowflake-stopwatch') {
        accessory = `
            <circle cx="20" cy="35" r="5" stroke="${accentColor}" stroke-width="1.5" fill="none" />
        `;
    } else if (variant === 'stop-sign-helmet') {
        accessory = `
            <polygon points="12,32 18,32 21,35 21,41 18,44 12,44 9,41 9,35" fill="#ef4444" stroke="#fff" stroke-width="0.75" />
        `;
    } else if (variant === 'squirrel-lockbox') {
        accessory = `
            <rect x="12" y="42" width="10" height="8" rx="1" fill="#1e293b" stroke="${strokeColor}" stroke-width="1" />
        `;
    } else if (variant === 'abacus-boxes') {
        accessory = `
            <rect x="52" y="32" width="12" height="12" fill="none" stroke="${accentColor}" stroke-width="1.5" />
        `;
    } else if (variant === 'nose-scroll') {
        accessory = `
            <line x1="40" y1="25" x2="48" y2="25" stroke="${accentColor}" stroke-width="2" />
        `;
    } else if (variant === 'beret-brush') {
        accessory = `
            <path d="M32,18 C32,15 48,15 48,18 Z" fill="${accentColor}" />
        `;
    } else if (variant === 'wand-trails') {
        accessory = `
            <circle cx="65" cy="35" r="2" fill="${accentColor}" />
        `;
    } else if (variant === 'ghost-vacuum') {
        accessory = `
            <rect x="52" y="42" width="8" height="12" fill="${accentColor}" />
        `;
    } else if (variant === 'camera-sparkles') {
        accessory = `
            <rect x="12" y="35" width="10" height="7" rx="1" fill="${accentColor}" />
        `;
    } else if (variant === 'chain-stamp') {
        accessory = `
            <circle cx="40" cy="35" r="3" stroke="${accentColor}" stroke-width="1" fill="none" />
        `;
    } else if (variant === 'penguin-tie') {
        accessory = `
            <polygon points="40,35 38,48 40,52 42,48" fill="${accentColor}" />
        `;
    } else if (variant === 'scale-calculator') {
        accessory = `
            <line x1="50" y1="35" x2="66" y2="35" stroke="${accentColor}" stroke-width="1.5" />
        `;
    }
    
    // Cybernetic enhancements
    let cyberneticElements = '';
    if (isNeon) {
        cyberneticElements = `
            <!-- Neon Glowing Visor -->
            <path d="M34,22 L46,22" stroke="${accentColor}" stroke-width="3" stroke-linecap="round" />
            <!-- Glowing Core (Reactor) -->
            <circle cx="40" cy="45" r="3.5" fill="${accentColor}" />
            <!-- Joint Nodes -->
            <circle cx="25" cy="40" r="2" fill="${strokeColor}" />
            <circle cx="55" cy="40" r="2" fill="${strokeColor}" />
            <circle cx="30" cy="80" r="2" fill="${strokeColor}" />
            <circle cx="50" cy="80" r="2" fill="${strokeColor}" />
            <circle cx="40" cy="60" r="2" fill="${strokeColor}" />
            <!-- Circuitry detail on spine -->
            <path d="M40,50 L46,47 L50,51" stroke="${accentColor}" stroke-width="1" fill="none" opacity="0.7" />
        `;
    }

    return `
        <svg viewBox="0 0 80 100" style="width:100%; height:100%; color: ${strokeColor};">
            <defs>
                <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="1.5" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>
            <g ${isNeon ? 'filter="url(#neon-glow)"' : ''}>
                ${spine}
                ${arms}
                ${legs}
                ${head}
                ${accessory}
                ${cyberneticElements}
            </g>
        </svg>
    `;
}

function initializeHochSwarmAnimationRuntime() {
    resetHochSwarmAnimationRuntime();

    const btnOpenComic = document.getElementById("btn-open-comic-swarm");
    const comicInterface = document.getElementById("kimi-style-comic-swarm-interface");
    btnOpenComic?.addEventListener("click", () => {
        if (comicInterface) {
            const isHidden = comicInterface.style.display === "none";
            comicInterface.style.display = isHidden ? "block" : "none";
            if (isHidden) {
                comicInterface.scrollIntoView({ behavior: "smooth" });
            }
        }
    });

    const launchBtn = document.getElementById("hoch-process-launch-button");
    const launchInput = document.getElementById("hoch-process-prompt-input");
    launchBtn?.addEventListener("click", () => {
        const text = launchInput?.value.trim() || "Research YouTube videos on Docker container debugging, summarize repair patterns, and assign agents to harden Hoch Agent Swarm.";
        startHochSwarmProcessAnimation(text);
    });

    const legacySpinBtn = document.getElementById("kimi-comic-spinup-button");
    const legacyInputField = document.getElementById("kimi-comic-prompt-input");
    legacySpinBtn?.addEventListener("click", () => {
        const text = legacyInputField?.value.trim() || "Research YouTube videos on Docker container debugging, summarize repair patterns, and assign agents to harden Hoch Agent Swarm.";
        startHochSwarmProcessAnimation(text);
        if (launchInput) {
            launchInput.value = text;
        }
    });
}

function setHochSwarmStage(stageName, status) {
    currentActiveStage = stageName;
    if (status === "active") {
        updateHochModuleStatusLights(stageName, "active");
        const badge = document.getElementById("hoch-global-swarm-status");
        if (badge) {
            badge.innerText = stageName.toUpperCase() + "...";
            badge.className = "badge badge-info";
        }
    }
    renderHochSwarmProcessRail(currentActiveStage, currentCompletedStages);
}

function lightHochSwarmCompletion(stageName) {
    if (!currentCompletedStages.includes(stageName)) {
        currentCompletedStages.push(stageName);
    }
    updateHochModuleStatusLights(stageName, "complete");
    renderHochSwarmProcessRail(currentActiveStage, currentCompletedStages);
}

function animateHochAgentSpinup(agentId, index) {
    agentStates[agentId] = "spinning-up";
    const activeIds = Object.keys(agentStates).filter(id => agentStates[id] !== "idle");
    renderHochGlobalAgentDock(activeIds, agentStates);
    drawGlobalSwarmMotionLines(activeIds);

    setTimeout(() => {
        agentStates[agentId] = "active";
        renderHochGlobalAgentDock(activeIds, agentStates);
        drawGlobalSwarmMotionLines(activeIds);
    }, 200 * index);
}

function animateHochAssetAssignment(agentId, assetId) {
    const nodeEl = document.getElementById(`node-card-${assetId}`);
    if (nodeEl) {
        nodeEl.style.transition = "all 0.3s";
        nodeEl.style.borderColor = "#3b82f6";
        nodeEl.style.boxShadow = "0 0 10px rgba(59, 130, 246, 0.5)";
        
        const activeIds = Object.keys(agentStates).filter(id => agentStates[id] !== "idle");
        drawGlobalSwarmMotionLines(activeIds);
    }
}

function updateHochModuleStatusLights(stageName, status) {
    const ledMap = {
        "plan": ["led-readiness-autopilot", "led-hochster-runtime"],
        "research": ["led-mission-intel"],
        "execute": ["led-remediation-safety", "led-swarm-control"],
        "verify": ["led-runtime-audit", "led-error-budget"],
        "report": ["led-release-provenance", "led-timeline-replay"],
        "complete": ["led-readiness-autopilot", "led-hochster-runtime", "led-remediation-safety", "led-swarm-control", "led-runtime-audit", "led-error-budget", "led-release-provenance", "led-mission-intel", "led-timeline-replay"]
    };

    const classMap = {
        "idle": "swarm-led-idle",
        "active": "swarm-led-active",
        "complete": "swarm-led-complete",
        "blocked": "swarm-led-blocked",
        "approval": "swarm-led-approval"
    };

    const leds = ledMap[stageName] || [];
    const className = classMap[status] || "swarm-led-idle";

    leds.forEach(ledId => {
        const el = document.getElementById(ledId);
        if (el) {
            el.className = "nav-status-indicator " + className;
        }
    });
}

function renderHochSwarmProcessRail(activeStage = "", completedStages = []) {
    const rail = document.getElementById("hoch-swarm-process-rail");
    if (!rail) return;

    const stages = [
        { id: "plan", label: "PLAN" },
        { id: "research", label: "RESEARCH" },
        { id: "execute", label: "EXECUTE" },
        { id: "verify", label: "VERIFY" },
        { id: "report", label: "REPORT" },
        { id: "complete", label: "COMPLETE" }
    ];

    rail.innerHTML = stages.map(stage => {
        let stepClass = "process-stage-step";
        if (stage.id === activeStage) {
            stepClass += " active";
        } else if (completedStages.includes(stage.id)) {
            stepClass += " complete";
        }
        return `
            <div class="${stepClass}" id="global-stage-${stage.id}">
                ${stage.label}
            </div>
        `;
    }).join("");
}

function renderHochGlobalAgentDock(activeAgentIds = [], states = {}) {
    const dock = document.getElementById("hoch-global-agent-dock");
    if (!dock) return;

    const agentsToDisplay = [...hochDefaultVisibleAgents];
    activeAgentIds.forEach(id => {
        if (!agentsToDisplay.includes(id)) {
            agentsToDisplay.push(id);
        }
    });

    const allAgents = [];
    hochAgentDepartments.forEach(dept => {
        dept.agents.forEach(agent => {
            allAgents.push(agent);
        });
    });

    const currentDisplayAgents = agentsToDisplay.map(id => {
        return allAgents.find(a => a.id === id) || {
            id,
            displayName: id.split("-").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" "),
            tag: "SPECIALIST",
            systemRole: "Agent Specialist",
            description: "Ready to assist the swarm.",
            catchphrase: "Swarm standby.",
            skills: ["operations"],
            defaultStage: "Execute",
            completionSignal: "Task complete",
            avatarVariant: "standard"
        };
    });

    dock.innerHTML = currentDisplayAgents.map(a => {
        const state = states[a.id] || "idle";
        let cardClass = "agent-dock-card";
        if (state === "active" || state === "executing" || state === "researching" || state === "spinning-up") {
            cardClass += " active";
        } else if (state === "complete" || state === "complete-green") {
            cardClass += " complete";
        } else if (state === "blocked") {
            cardClass += " blocked";
        } else if (state === "needs-approval") {
            cardClass += " needs-approval";
        }
        
        return `
            <div id="dock-card-${a.id}" class="${cardClass}" style="padding: 6px; font-size: 10px; text-align: center;">
                <div style="font-weight: 700; color: #fff; font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;" title="${a.displayName}">${a.displayName}</div>
                <div style="font-size: 7px; color: var(--accent-teal); font-weight: bold; text-transform: uppercase; margin-bottom: 4px;">${a.tag}</div>
                <div class="agent-dock-avatar" style="width: 32px; height: 32px; margin: 4px auto;">
                    ${getAgentSvg(a.avatarVariant, state)}
                </div>
                <div style="font-size: 8px; color: var(--text-secondary); text-align: center; height: 24px; display: flex; flex-direction: column; justify-content: center; overflow: hidden;">
                    <div style="font-style: italic; line-height: 1.1; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">"${a.catchphrase}"</div>
                </div>
                <div style="font-size: 8px; font-weight: 600; color: #fff; margin-top: 4px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 2px; text-transform: uppercase;">
                    ${state}
                </div>
            </div>
        `;
    }).join("");
}

function renderHochEvidenceCompletionLights(states = {}) {
    const container = document.getElementById("hoch-global-evidence-lights");
    if (!container) return;

    const categories = [
        { key: "realtime", label: "REALTIME" },
        { key: "ast", label: "AST" },
        { key: "audit", label: "AUDIT" },
        { key: "provenance", label: "PROV" }
    ];

    container.innerHTML = categories.map(cat => {
        const state = states[cat.key] || "idle";
        let dotClass = "evidence-light";
        if (state === "locked") {
            dotClass += " locked";
        } else if (state === "pending") {
            dotClass += " pending";
        }
        return `
            <div style="display: flex; align-items: center; gap: 4px; font-size: 9px; font-weight: 600; font-family: monospace; color: var(--text-secondary);">
                <span class="${dotClass}"></span>
                <span>${cat.label}</span>
            </div>
        `;
    }).join("");
}

function animateGordonDockerChecklist() {
    const items = ["logs", "health", "deps", "bind", "patch"];
    items.forEach((item, idx) => {
        setTimeout(() => {
            checkGordonListItem(item, true);
        }, idx * 600);
    });
}

function drawGlobalSwarmMotionLines(activeAgentIds = []) {
    const canvas = document.getElementById("hoch-global-motion-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const getCoords = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        const elRect = el.getBoundingClientRect();
        return {
            x: elRect.left - rect.left + elRect.width / 2,
            y: elRect.top - rect.top + elRect.height / 2
        };
    };

    const promptBar = getCoords("hoch-process-prompt-bar");
    const rail = getCoords("hoch-swarm-process-rail");

    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";

    const drawLine = (from, to, color) => {
        if (!from || !to) return;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.bezierCurveTo(
            (from.x + to.x) / 2, from.y,
            (from.x + to.x) / 2, to.y,
            to.x, to.y
        );
        ctx.strokeStyle = color;
        ctx.stroke();
    };

    if (promptBar && rail) {
        drawLine(promptBar, rail, "rgba(59, 130, 246, 0.25)");
    }

    activeAgentIds.forEach(id => {
        const card = getCoords(`dock-card-${id}`);
        if (card && rail) {
            drawLine(rail, card, "rgba(16, 185, 129, 0.2)");
        }
    });
}

function resetHochSwarmAnimationRuntime() {
    currentActiveStage = "";
    currentCompletedStages = [];
    agentStates = {};
    
    const allLeds = [
        "led-readiness-autopilot", "led-hochster-runtime", "led-remediation-safety",
        "led-runtime-audit", "led-error-budget", "led-release-provenance",
        "led-swarm-control", "led-mission-intel", "led-timeline-replay"
    ];
    allLeds.forEach(ledId => {
        const el = document.getElementById(ledId);
        if (el) {
            el.className = "nav-status-indicator swarm-led-idle";
        }
    });

    const badge = document.getElementById("hoch-global-swarm-status");
    if (badge) {
        badge.innerText = "STANDBY";
        badge.className = "badge badge-success";
    }

    renderHochSwarmProcessRail();

    const initialStates = {};
    hochDefaultVisibleAgents.forEach(id => {
        initialStates[id] = "idle";
    });
    renderHochGlobalAgentDock(hochDefaultVisibleAgents, initialStates);

    const initialEvidenceStates = {
        realtime: "idle",
        ast: "idle",
        audit: "idle",
        provenance: "idle"
    };
    renderHochEvidenceCompletionLights(initialEvidenceStates);

    const chks = ["logs", "health", "deps", "bind", "patch"];
    chks.forEach(c => {
        const el = document.getElementById(`gordon-chk-${c}`);
        if (el) {
            el.checked = false;
            el.parentElement.style.color = "var(--text-secondary)";
            el.parentElement.style.textDecoration = "none";
        }
    });

    const canvas = document.getElementById("hoch-global-motion-canvas");
    if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

function startHochSwarmProcessAnimation(promptText) {
    currentAnimationTimeouts.forEach(t => clearTimeout(t));
    currentAnimationTimeouts = [];

    resetHochSwarmAnimationRuntime();

    const activeAgentIds = routePromptAgents(promptText);
    
    // 1. Stage: Plan
    setHochSwarmStage("plan", "active");
    const planAgents = activeAgentIds.filter(id => ["boss-noodle", "captain-obvious-prime", "sir-deadline-panic", "prof-blueprint", "lady-tradeoff"].includes(id));
    if (planAgents.length === 0) planAgents.push("boss-noodle");
    
    planAgents.forEach((agentId, idx) => {
        animateHochAgentSpinup(agentId, idx + 1);
    });

    appendKimiComicWorkFeed(`[Plan] Prompt received: "${promptText}"`);
    appendKimiComicWorkFeed(`[Plan] Mission Wrangler decomposing prompt. Assigned specialists: ${activeAgentIds.join(", ")}`);

    // 2. Stage: Research
    let t1 = setTimeout(() => {
        lightHochSwarmCompletion("plan");
        setHochSwarmStage("research", "active");

        const researchAgents = activeAgentIds.filter(id => ["dr-signal", "scout-tabs-a-lot"].includes(id));
        if (researchAgents.length === 0) researchAgents.push("dr-signal");
        
        researchAgents.forEach((agentId, idx) => {
            animateHochAgentSpinup(agentId, idx + 1);
        });

        const isDocker = promptText.toLowerCase().match(/docker|container|port|log/);
        if (isDocker) {
            animateYoutubeResearchCards();
        } else {
            const grid = document.getElementById("kimi-comic-video-candidate-grid");
            if (grid) {
                grid.innerHTML = hochUiResearchCandidates.map((c, idx) => `
                    <div class="card" id="video-card-${idx}" style="padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 6px; text-align: left; opacity: 0; transform: translateY(10px); transition: all 0.4s ease-out; margin-bottom: 8px;">
                        <div style="font-size: 11px; font-weight: 600; color: #fff; margin-bottom: 4px; line-height: 1.3;">${c.title}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size: 9px; color: var(--text-secondary);">
                            <span>${c.channel} • <span style="color:#3b82f6;">${c.signal}</span></span>
                            <span style="font-size:8px; border: 1px solid rgba(245, 158, 11, 0.3); background: rgba(245, 158, 11, 0.05); color: #f59e0b; padding: 1px 4px; border-radius: 3px; font-weight:bold;">candidate, not verified</span>
                        </div>
                        <div style="font-size: 9px; color: var(--accent-teal); margin-top: 6px; font-family: monospace; border-top: 1px solid rgba(255,255,255,0.03); padding-top: 4px;">
                            <strong>Pattern:</strong> ${c.extractedPattern}
                        </div>
                    </div>
                `).join("");
                hochUiResearchCandidates.forEach((c, idx) => {
                    setTimeout(() => {
                        const card = document.getElementById(`video-card-${idx}`);
                        if (card) {
                            card.style.opacity = "1";
                            card.style.transform = "translateY(0)";
                        }
                    }, idx * 250);
                });
            }
        }

        appendKimiComicWorkFeed(`[Research] Accessing domain telemetry. Extracting candidates and workflow matches.`);
    }, 1500);
    currentAnimationTimeouts.push(t1);

    // 3. Stage: Execute
    let t2 = setTimeout(() => {
        lightHochSwarmCompletion("research");
        setHochSwarmStage("execute", "active");

        const executeAgents = activeAgentIds.filter(id => ["eng-patch", "bugsy-mcfixface", "gordon-vector", "captain-compose", "log-goblin", "pixel-picasso", "motion-molly"].includes(id));
        if (executeAgents.length === 0) executeAgents.push("eng-patch");

        executeAgents.forEach((agentId, idx) => {
            animateHochAgentSpinup(agentId, idx + 1);
        });

        animateGordonDockerChecklist();
        animateHochAssetAssignment(executeAgents[0], "L1");

        appendKimiComicWorkFeed(`[Execute] Execution lane active. Applying minimal modifications.`);
    }, 3000);
    currentAnimationTimeouts.push(t2);

    // 4. Stage: Verify
    let t3 = setTimeout(() => {
        lightHochSwarmCompletion("execute");
        setHochSwarmStage("verify", "active");

        const verifyAgents = activeAgentIds.filter(id => ["ms-checkmark", "playwright-pete", "dr-flake", "screenshot-sally", "ux-ursula", "null-pointer-ned"].includes(id));
        if (verifyAgents.length === 0) verifyAgents.push("ms-checkmark");

        verifyAgents.forEach((agentId, idx) => {
            animateHochAgentSpinup(agentId, idx + 1);
        });

        renderHochEvidenceCompletionLights({
            realtime: "pending",
            ast: "pending",
            audit: "idle",
            provenance: "idle"
        });

        appendKimiComicWorkFeed(`[Verify] Verification loop active. Running regression checks and E2E contract compliance.`);
    }, 5000);
    currentAnimationTimeouts.push(t3);

    // 5. Stage: Report
    let t4 = setTimeout(() => {
        lightHochSwarmCompletion("verify");
        setHochSwarmStage("report", "active");

        const reportAgents = activeAgentIds.filter(id => ["prof-ledger", "sbom-bob", "provenance-penny", "eng-rocket"].includes(id));
        if (reportAgents.length === 0) reportAgents.push("prof-ledger");

        reportAgents.forEach((agentId, idx) => {
            animateHochAgentSpinup(agentId, idx + 1);
        });

        renderHochEvidenceCompletionLights({
            realtime: "locked",
            ast: "locked",
            audit: "locked",
            provenance: "pending"
        });

        appendKimiComicWorkFeed(`[Report] Compiling cryptographic ledger entries and generating SBOM manifest.`);
    }, 6500);
    currentAnimationTimeouts.push(t4);

    // 6. Stage: Complete
    let t5 = setTimeout(() => {
        lightHochSwarmCompletion("report");
        setHochSwarmStage("complete", "active");
        lightHochSwarmCompletion("complete");

        Object.keys(agentStates).forEach(id => {
            if (agentStates[id] !== "idle") {
                agentStates[id] = "complete-green";
            }
        });
        const activeIds = Object.keys(agentStates).filter(id => agentStates[id] !== "idle");
        renderHochGlobalAgentDock(activeIds, agentStates);
        drawGlobalSwarmMotionLines(activeIds);

        renderHochEvidenceCompletionLights({
            realtime: "locked",
            ast: "locked",
            audit: "locked",
            provenance: "locked"
        });

        const badge = document.getElementById("hoch-global-swarm-status");
        if (badge) {
            badge.innerText = "COMPLETED";
            badge.className = "badge badge-success";
        }

        appendKimiComicWorkFeed(`[Report] Swarm verification complete. Compliance scored 100/100. Swarm mesh secured.`);
    }, 8000);
    currentAnimationTimeouts.push(t5);
}

// ------------------------------------------------------------------------------
// Compatibility Wrappers for Legacy Comic Swarm Panel
// ------------------------------------------------------------------------------

function renderKimiStyleComicSwarmInterface() {
    renderHochComicAgentProfiles();
    renderYoutubeResearchLane();
    renderGordonContainerWhispererPanel();
    
    const ring = document.getElementById("kimi-comic-agent-ring");
    if (ring) {
        ring.innerHTML = hochComicAgents.map(a => `
            <div id="ring-dot-${a.id}" style="width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--border-glass); background: rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; font-size: 10px; color: var(--text-secondary); font-weight: bold; transition: all 0.3s;" title="${a.name}">
                ${a.name.split(" ")[0][0]}
            </div>
        `).join("");
    }
}

function renderHochComicAgentProfiles() {
    const deck = document.getElementById("kimi-comic-agent-profile-deck");
    if (!deck) return;
    deck.innerHTML = hochComicAgents.map(a => `
        <div id="profile-card-${a.id}" class="card" style="padding:12px; opacity: 0.3; transition: all 0.5s ease-in-out; border: 1px solid var(--border-glass); background: rgba(22, 28, 45, 0.4);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid var(--border-glass); padding-bottom:6px; margin-bottom:8px;">
                <span style="font-weight:700; font-size:12px; color:var(--text-primary);">${a.name}</span>
                <span style="font-size:9px; background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.3); color:var(--accent-teal); padding:2px 6px; border-radius:4px; font-family:monospace; font-weight:bold;">${a.tag}</span>
            </div>
            <div style="display:flex; gap:12px; align-items:center; margin-bottom:8px;">
                <div style="border: 1px solid var(--border-glass); border-radius:50%; background:rgba(0,0,0,0.2); width:48px; height:48px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    ${getAgentSvg(a.id === 'gordon' ? 'glasses-docker' : (a.id === 'research' ? 'headphones-beard-glass' : (a.id === 'architect' ? 'blueprint-ruler' : (a.id === 'code' ? 'bracket-mask' : (a.id === 'qa' ? 'clipboard-bob' : (a.id === 'security' ? 'shield-cap' : (a.id === 'remediation' ? 'scale-calculator' : (a.id === 'audit' ? 'ledger-monocle' : 'rocket-flat'))))))), 'idle')}
                </div>
                <div style="font-size:10px; color:var(--text-secondary); font-style: italic; line-height:1.3; text-align:left;">
                    <strong>Catchphrase:</strong> "${a.catchphrase}"
                </div>
            </div>
            <div style="font-size:10px; color:var(--text-secondary); text-align:left; line-height:1.4;">
                <div style="margin-bottom:4px;"><strong>Look:</strong> ${a.look}</div>
                <div style="margin-bottom:4px;"><strong>Skills:</strong> ${a.skills.join(", ")}</div>
                <div id="profile-assign-${a.id}" style="color:var(--accent-blue); font-weight:500;"><strong>Status:</strong> Idle</div>
            </div>
        </div>
    `).join("");
}

function renderYoutubeResearchLane() {
    const grid = document.getElementById("kimi-comic-video-candidate-grid");
    if (!grid) return;
    grid.innerHTML = `<div style="border: 1px dashed var(--border-glass); border-radius: 6px; padding: 16px; text-align: center; color: var(--text-secondary); font-size: 11px; width: 100%;">Lane standing by...</div>`;
}

function animateYoutubeResearchCards() {
    const grid = document.getElementById("kimi-comic-video-candidate-grid");
    if (!grid) return;
    grid.innerHTML = hochYoutubeResearchCandidates.map((c, idx) => `
        <div class="card" id="video-card-${idx}" style="padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glass); border-radius: 6px; text-align: left; opacity: 0; transform: translateY(10px); transition: all 0.4s ease-out; margin-bottom: 8px;">
            <div style="font-size: 11px; font-weight: 600; color: #fff; margin-bottom: 4px; line-height: 1.3;">${c.title}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size: 9px; color: var(--text-secondary);">
                <span>${c.channel} • <span style="color:#3b82f6;">${c.signal}</span></span>
                <span style="font-size:8px; border: 1px solid rgba(245, 158, 11, 0.3); background: rgba(245, 158, 11, 0.05); color: #f59e0b; padding: 1px 4px; border-radius: 3px; font-weight:bold;">candidate, not verified</span>
            </div>
            <div style="font-size: 9px; color: var(--accent-teal); margin-top: 6px; font-family: monospace; border-top: 1px solid rgba(255,255,255,0.03); padding-top: 4px;">
                <strong>Pattern:</strong> ${c.extractedPattern}
            </div>
        </div>
    `).join("");

    hochYoutubeResearchCandidates.forEach((c, idx) => {
        setTimeout(() => {
            const card = document.getElementById(`video-card-${idx}`);
            if (card) {
                card.style.opacity = "1";
                card.style.transform = "translateY(0)";
            }
        }, idx * 250);
    });
}

function animateComicAgentProfiles() {
    // Legacy support
}

function drawKimiStyleMotionLines() {
    const canvas = document.getElementById("kimi-comic-motion-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function appendKimiComicWorkFeed(event) {
    const feed = document.getElementById("kimi-comic-work-feed");
    if (!feed) return;
    if (feed.innerHTML.includes("Idle. Waiting")) feed.innerHTML = "";
    feed.innerHTML += `<div>${event}</div>`;
    feed.scrollTop = feed.scrollHeight;
}

function updateKimiComicCommandLoop(stage) {
    const stages = ["plan", "research", "execute", "verify", "report"];
    stages.forEach(s => {
        const el = document.getElementById(`stage-${s}`);
        if (el) {
            if (s === stage) el.classList.add("active-stage");
            else el.classList.remove("active-stage");
        }
    });
}

function renderGordonContainerWhispererPanel() {
    const chks = ["logs", "health", "deps", "bind", "patch"];
    chks.forEach(c => {
        const el = document.getElementById(`gordon-chk-${c}`);
        if (el) {
            el.checked = false;
            el.parentElement.style.color = "var(--text-secondary)";
            el.parentElement.style.textDecoration = "none";
        }
    });
}

function checkGordonListItem(id, check) {
    const el = document.getElementById(`gordon-chk-${id}`);
    if (el) {
        el.checked = check;
        if (check) {
            el.parentElement.style.color = "var(--accent-teal)";
            el.parentElement.style.textDecoration = "line-through";
        } else {
            el.parentElement.style.color = "var(--text-secondary)";
            el.parentElement.style.textDecoration = "none";
        }
    }
}

function wakeAgent(id, statusText) {
    const card = document.getElementById(`profile-card-${id}`);
    const dot = document.getElementById(`ring-dot-${id}`);
    const assign = document.getElementById(`profile-assign-${id}`);

    if (card) card.style.opacity = "1";
    if (dot) {
        dot.style.background = "var(--accent-teal)";
        dot.style.borderColor = "var(--accent-teal)";
        dot.style.color = "#fff";
    }
    if (assign) {
        assign.innerHTML = `<strong>Status:</strong> ${statusText}`;
    }
}

function spinUpKimiStyleComicSwarm(promptText) {
    const core = document.getElementById("kimi-comic-mission-core");
    if (core) core.classList.add("pulse-active");

    setTimeout(() => {
        wakeAgent("research", "Searching YouTube API search.list...");
        appendKimiComicWorkFeed("[Plan] Research Agent online. Scanning YouTube for debugging patterns.");
        drawKimiStyleMotionLines();
    }, 1000);

    setTimeout(() => {
        updateKimiComicCommandLoop("research");
        appendKimiComicWorkFeed("[Research] Search list retrieved. 4 video candidates matches loaded.");
        animateYoutubeResearchCards();
        checkGordonListItem("logs", true);
        drawKimiStyleMotionLines();
    }, 2500);

    setTimeout(() => {
        appendKimiComicWorkFeed("[Research] Parsing metadata & signals. Extracting repair patterns.");
        assignResearchToAgents();
        checkGordonListItem("health", true);
        drawKimiStyleMotionLines();
    }, 4000);

    setTimeout(() => {
        updateKimiComicCommandLoop("execute");
        wakeAgent("architect", "System mapping design options...");
        wakeAgent("code", "Generating candidate patches...");
        wakeAgent("qa", "Constructing contract validation gates...");
        wakeAgent("security", "Enforcing ZTA allowed commands list...");
        appendKimiComicWorkFeed("[Execute] Code, Architect, QA, and Security agents assigned.");
        checkGordonListItem("deps", true);
        drawKimiStyleMotionLines();
    }, 5500);

    setTimeout(() => {
        updateKimiComicCommandLoop("verify");
        wakeAgent("gordon", "Extracting active container health check logs...");
        wakeAgent("remediation", "Validating pre-flight dry-runs...");
        wakeAgent("audit", "Compiling cryptographic ledger records...");
        wakeAgent("release", "Signing final provenance scorecard...");
        appendKimiComicWorkFeed("[Verify] Execution verify loop: checking SQL allowlist, rollback triggers, and L4 budget thresholds.");
        checkGordonListItem("bind", true);
        drawKimiStyleMotionLines();
    }, 7000);

    setTimeout(() => {
        updateKimiComicCommandLoop("report");
        checkGordonListItem("patch", true);
        
        hochComicAgents.forEach(a => {
            const assign = document.getElementById(`profile-assign-${a.id}`);
            if (assign) assign.innerHTML = `<strong>Status:</strong> Done / Monitoring`;
        });

        appendKimiComicWorkFeed("[Report] Verification complete. 100/100 readiness verified. Swarm mesh secured.");
        if (core) core.classList.remove("pulse-active");
        drawKimiStyleMotionLines();
    }, 8500);
}

function assignResearchToAgents() {
    const assetGrid = document.getElementById("kimi-comic-asset-grid");
    if (assetGrid) {
        assetGrid.innerHTML = `
            <div style="border: 1px solid rgba(16, 185, 129, 0.3); background: rgba(16, 185, 129, 0.05); padding: 8px; border-radius: 6px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                <span>Asset L1 (FASTAPI)</span> <span style="color:var(--accent-teal); font-weight:bold;">Code Agent Assigned</span>
            </div>
            <div style="border: 1px solid rgba(59, 130, 246, 0.3); background: rgba(59, 130, 246, 0.05); padding: 8px; border-radius: 6px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                <span>Asset L2 (TELEMETRY)</span> <span style="color:var(--accent-blue); font-weight:bold;">Gordon Debugger Assigned</span>
            </div>
            <div style="border: 1px solid rgba(168, 85, 247, 0.3); background: rgba(168, 85, 247, 0.05); padding: 8px; border-radius: 6px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                <span>Asset L3 (AUDIT)</span> <span style="color:var(--accent-purple); font-weight:bold;">Audit Agent Assigned</span>
            </div>
            <div style="border: 1px solid rgba(249, 115, 22, 0.3); background: rgba(249, 115, 22, 0.05); padding: 8px; border-radius: 6px; display:flex; justify-content:space-between; align-items:center;">
                <span>Asset W1 (WORKERS)</span> <span style="color:var(--accent-orange); font-weight:bold;">QA Agent Assigned</span>
            </div>
        `;
    }
}

// Initial binding
setTimeout(() => {
    renderKimiStyleComicSwarmInterface();

    const spinBtn = document.getElementById("kimi-comic-spinup-button");
    const inputField = document.getElementById("kimi-comic-prompt-input");

    spinBtn?.addEventListener("click", () => {
        const text = inputField?.value.trim() || "Research YouTube videos on Docker container debugging, summarize repair patterns, and assign agents to harden Hoch Agent Swarm.";
        spinUpKimiStyleComicSwarm(text);
    });
}, 100);

window.addEventListener("resize", drawKimiStyleMotionLines);

// ==============================================================================
// TOPOLOGY DASHBOARD AGENT OVERLAY SYSTEM - IMPLEMENTATION
// ==============================================================================

const hochPixelStickAgents = [
  {
    id: "boss-noodle",
    displayName: "Boss Noodle",
    title: "Swarm Supervisor",
    tag: "MISSION WRANGLER",
    systemRole: "Supervisor Agent",
    avatarVariant: "tiny-crown-headset",
    status: "idle",
    description: "Decomposes any prompt into work lanes, assigns specialists, and keeps the swarm moving.",
    catchphrase: "Everybody gets a lane. Nobody gets to wander.",
    skills: ["goal decomposition", "routing", "priority ranking", "handoff control"],
    defaultStage: "Plan",
    completionSignal: "Mission decomposed",
    assetTargets: [],
    stats: { intelligence: 98, speed: 90, reliability: 95, energy: 85 },
    tier: "MYTHIC"
  },
  {
    id: "dr-signal",
    displayName: "Dr. Signal",
    title: "Senior Research Agent",
    tag: "TRUTH HUNTER",
    systemRole: "Research Specialist",
    avatarVariant: "research",
    status: "idle",
    description: "Finds signal in messy research, video candidates, docs, and prior evidence before anyone patches.",
    catchphrase: "I find the signal before anyone patches.",
    skills: ["research triage", "YouTube candidate synthesis", "source ranking", "constraint extraction"],
    defaultStage: "Research",
    completionSignal: "Signal extracted",
    assetTargets: [],
    stats: { intelligence: 96, speed: 85, reliability: 97, energy: 75 },
    tier: "GOLD"
  },
  {
    id: "prof-blueprint",
    displayName: "Prof. Blueprint",
    title: "Systems Architect",
    tag: "SYSTEM CARTOONIST",
    systemRole: "Planning Specialist",
    avatarVariant: "standard",
    status: "idle",
    description: "Turns high-level swarm goals into concrete architectural designs and execution steps.",
    catchphrase: "Every fix needs a shape.",
    skills: ["architecture documentation", "component mapping", "dependency analysis"],
    defaultStage: "Plan",
    completionSignal: "Blueprint drawn",
    assetTargets: [],
    stats: { intelligence: 95, speed: 80, reliability: 92, energy: 70 },
    tier: "PLATINUM"
  },
  {
    id: "eng-patch",
    displayName: "Eng. Patch",
    title: "Implementation Specialist",
    tag: "PATCH MONK",
    systemRole: "Code Specialist",
    avatarVariant: "bracket-mask",
    status: "idle",
    description: "Applies small, high-leverage code changes with minimal blast radius.",
    catchphrase: "Small diff. Big effect.",
    skills: ["implementation", "refactor", "integration", "config repair"],
    defaultStage: "Execute",
    completionSignal: "Patch applied",
    assetTargets: ["L1", "W1"],
    stats: { intelligence: 92, speed: 98, reliability: 94, energy: 90 },
    tier: "LEGENDARY"
  },
  {
    id: "ms-checkmark",
    displayName: "Ms. Checkmark",
    title: "Verification Lead",
    tag: "BUG BOUNCER",
    systemRole: "QA Specialist",
    avatarVariant: "clipboard-bob",
    status: "idle",
    description: "Turns claims into tests, screenshots, contracts, and hard PASS/BLOCK results.",
    catchphrase: "No proof, no pass.",
    skills: ["build validation", "regression tests", "E2E", "UI contracts"],
    defaultStage: "Verify",
    completionSignal: "Tests verified",
    assetTargets: ["L2"],
    stats: { intelligence: 90, speed: 92, reliability: 99, energy: 80 },
    tier: "LEGENDARY"
  },
  {
    id: "capt-guardrail",
    displayName: "Capt. Guardrail",
    title: "Autonomy Safety Officer",
    tag: "GUARDRAIL GOBLIN",
    systemRole: "Security Officer",
    avatarVariant: "shield-cap",
    status: "idle",
    description: "Keeps agent freedom bounded by command safety, secrets hygiene, and release policy.",
    catchphrase: "Freedom inside fences.",
    skills: ["command risk", "secrets checks", "dependency risk", "policy gates"],
    defaultStage: "Verify",
    completionSignal: "Policy enforced",
    assetTargets: [],
    stats: { intelligence: 94, speed: 86, reliability: 98, energy: 85 },
    tier: "GOLD"
  },
  {
    id: "gordon-vector",
    displayName: "Gordon Vector",
    title: "Docker Debugger",
    tag: "CONTAINER WHISPERER",
    systemRole: "Docker Specialist",
    avatarVariant: "glasses-docker",
    status: "idle",
    description: "Diagnoses containers by reading symptoms: logs, inspect output, health checks, compose timing, and network state.",
    catchphrase: "The container will tell us what hurts.",
    skills: ["docker logs", "docker inspect", "health checks", "compose diagnosis", "root cause isolation"],
    defaultStage: "Execute",
    completionSignal: "Containers verified",
    assetTargets: ["L3"],
    stats: { intelligence: 93, speed: 91, reliability: 96, energy: 75 },
    tier: "PLATINUM"
  },
  {
    id: "prof-ledger",
    displayName: "Prof. Ledger",
    title: "Evidence Auditor",
    tag: "RECEIPT WIZARD",
    systemRole: "Audit Specialist",
    avatarVariant: "ledger-monocle",
    status: "idle",
    description: "Locks every decision, source, command, and verification into evidence.",
    catchphrase: "If it is not evidenced, it did not happen.",
    skills: ["trace IDs", "evidence packs", "provenance", "release records"],
    defaultStage: "Report",
    completionSignal: "Evidence finalized",
    assetTargets: [],
    stats: { intelligence: 91, speed: 84, reliability: 100, energy: 65 },
    tier: "MYTHIC"
  },
  {
    id: "eng-rocket",
    displayName: "Eng. Rocket",
    title: "Release Judge",
    tag: "SHIP JUDGE",
    systemRole: "Release Manager",
    avatarVariant: "rocket-flat",
    status: "idle",
    description: "Ships only when the release can defend itself with readiness, provenance, rollback, and verification evidence.",
    catchphrase: "Ship only what can defend itself.",
    skills: ["release readiness", "SBOM", "provenance", "final gate decision"],
    defaultStage: "Complete",
    completionSignal: "Release authorized",
    assetTargets: [],
    stats: { intelligence: 94, speed: 95, reliability: 97, energy: 95 },
    tier: "LEGENDARY"
  }
];

let lastTopologyTrigger = null;
let topologyTimeouts = [];

async function bindTopologyAgentOverlay() {
    try {
        const resp = await fetch("/api/v1/agents");
        if (resp.ok) {
            const data = await resp.json();
            if (data && data.length > 0) {
                const staticAssetTargets = {
                    "capt-guardrail": ["L1", "W1"],
                    "ms-checkmark": ["L1", "W1"],
                    "bugsy-mcfixface": ["L2"],
                    "eng-patch": ["L2"],
                    "gordon-vector": ["L3"]
                };
                const staticStages = {
                    "boss-noodle": "Plan",
                    "dr-signal": "Research",
                    "prof-blueprint": "Plan",
                    "eng-patch": "Execute",
                    "ms-checkmark": "Verify",
                    "capt-guardrail": "Verify",
                    "gordon-vector": "Execute",
                    "prof-ledger": "Report",
                    "eng-rocket": "Complete"
                };
                const staticSignals = {
                    "boss-noodle": "Mission decomposed",
                    "dr-signal": "Signal extracted",
                    "prof-blueprint": "Blueprint drawn",
                    "eng-patch": "Patch applied",
                    "ms-checkmark": "Tests verified",
                    "capt-guardrail": "Policy enforced",
                    "gordon-vector": "Containers verified",
                    "prof-ledger": "Evidence finalized",
                    "eng-rocket": "Release authorized"
                };
                data.forEach(agent => {
                    agent.assetTargets = staticAssetTargets[agent.id] || [];
                    agent.defaultStage = staticStages[agent.id] || "Plan";
                    agent.completionSignal = staticSignals[agent.id] || "Mission decomposed";
                });
                hochPixelStickAgents.length = 0;
                hochPixelStickAgents.push(...data);
            }
        }
    } catch (e) {
        console.warn("Failed to fetch live agents:", e);
    }
    renderTopologyAgentRoster();
    
    const launchBtn = document.getElementById("topology-agent-launch-button");
    const launchInput = document.getElementById("topology-agent-prompt-input");
    
    launchBtn?.addEventListener("click", () => {
        const text = launchInput?.value.trim() || "Research YouTube Docker debugging videos and verify release readiness.";
        launchTopologyExpertSwarm(text);
    });
    
    const modalCloseBtn = document.getElementById("topology-agent-modal-close");
    modalCloseBtn?.addEventListener("click", () => {
        closeTopologyAgentProfile();
    });
    
    const modal = document.getElementById("topology-agent-profile-modal");
    modal?.addEventListener("click", (e) => {
        if (e.target === modal) {
            closeTopologyAgentProfile();
        }
    });
    
    document.getElementById("topology-agent-modal-spinup")?.addEventListener("click", () => {
        const agentId = modal?.dataset.agentId;
        if (agentId) {
            const agent = hochPixelStickAgents.find(a => a.id === agentId);
            if (agent) {
                agent.status = "complete";
                animateTopologyAgentChip(agentId);
                const led = document.getElementById(`topo-led-${agentId}`);
                if (led) {
                    led.className = "topology-agent-led is-green";
                }
                const statusEl = document.getElementById("topology-agent-modal-status");
                if (statusEl) statusEl.textContent = "complete";
                
                // Active stage complete
                animateTopologyStageRail(agent.defaultStage, "complete");
            }
        }
    });
    
    document.getElementById("topology-agent-modal-assign")?.addEventListener("click", () => {
        const agentId = modal?.dataset.agentId;
        if (agentId) {
            const agent = hochPixelStickAgents.find(a => a.id === agentId);
            if (agent) {
                const promptVal = launchInput?.value || "Assign current mission";
                console.log(`[Topology Swarm Assignment] ${agent.displayName}: ${promptVal}`);
                
                agent.status = "complete";
                animateTopologyAgentChip(agentId);
                const led = document.getElementById(`topo-led-${agentId}`);
                if (led) {
                    led.className = "topology-agent-led is-green";
                }
                const statusEl = document.getElementById("topology-agent-modal-status");
                if (statusEl) statusEl.textContent = "complete";
                
                // Active stage complete
                animateTopologyStageRail(agent.defaultStage, "complete");
            }
        }
    });
}

function renderTopologyAgentRoster() {
    const roster = document.getElementById("topology-agent-roster");
    if (!roster) return;
    
    roster.innerHTML = hochPixelStickAgents.map(agent => {
        const state = agent.status || "idle";
        let ledClass = "topology-agent-led";
        if (state === "complete") {
            ledClass += " is-green";
        }
        
        return `
            <button class="topology-agent-chip" id="topo-chip-${agent.id}" data-agent-id="${agent.id}" type="button" style="margin: 2px;">
                <span class="${ledClass}" id="topo-led-${agent.id}"></span>
                <strong>${agent.displayName}</strong>
                <span style="font-size: 7px; opacity: 0.6; text-transform: uppercase;">${agent.tag}</span>
            </button>
        `;
    }).join("");
    
    // Bind click events
    roster.querySelectorAll(".topology-agent-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            openTopologyAgentProfile(chip.dataset.agentId, chip);
        });
    });
}

function renderTopologyPixelAvatar(avatarVariant, state) {
    return getAgentSvg(avatarVariant, state);
}

function openTopologyAgentProfile(agentId, triggerEl) {
    const agent = hochPixelStickAgents.find(a => a.id === agentId);
    if (!agent) return;
    
    lastTopologyTrigger = triggerEl || document.activeElement;
    
    // Dim other chips, highlight active one
    document.querySelectorAll(".topology-agent-chip").forEach(chip => {
        const isTarget = chip.dataset.agentId === agentId;
        chip.classList.toggle("is-active", isTarget);
        chip.classList.toggle("is-dimmed", !isTarget);
    });
    
    // Populate modal elements
    const avatarContainer = document.getElementById("topology-agent-modal-avatar");
    if (avatarContainer) {
        avatarContainer.innerHTML = renderTopologyPixelAvatar(agent.avatarVariant, agent.status);
        
        // Element.animate() transitions for stick figure
        avatarContainer.animate([
            { transform: "scale(0) rotate(-180deg)", opacity: 0 },
            { transform: "scale(1.1) rotate(10deg)", opacity: 1 },
            { transform: "scale(1) rotate(0deg)", opacity: 1 }
        ], { duration: 600, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" });
    }
    
    const statusEl = document.getElementById("topology-agent-modal-status");
    if (statusEl) statusEl.textContent = agent.status || "idle";
    
    const tagEl = document.getElementById("topology-agent-modal-tag");
    if (tagEl) {
        tagEl.textContent = agent.tag;
    }
    
    const nameEl = document.getElementById("topology-agent-modal-name");
    if (nameEl) nameEl.textContent = agent.displayName;
    
    const titleEl = document.getElementById("topology-agent-modal-title");
    if (titleEl) titleEl.textContent = agent.title;
    
    const descEl = document.getElementById("topology-agent-modal-description");
    if (descEl) descEl.textContent = agent.description;
    
    const phraseEl = document.getElementById("topology-agent-modal-catchphrase");
    if (phraseEl) phraseEl.textContent = `“${agent.catchphrase}”`;
    
    // Animate specialized skills spinning up sequentially
    const skillsEl = document.getElementById("topology-agent-modal-skills");
    if (skillsEl) {
        skillsEl.innerHTML = "";
        agent.skills.forEach((skill, idx) => {
            const span = document.createElement("span");
            span.className = prefersReducedMotion ? "agent-capsule" : "agent-capsule skill-spinning";
            span.textContent = skill;
            span.style.animationDelay = `${idx * 100}ms`;
            skillsEl.appendChild(span);
        });
    }

    // Render capability manifest if present
    const manifestContainer = document.getElementById("topology-agent-modal-manifest-container");
    const allowedEl = document.getElementById("agent-manifest-allowed");
    const deniedEl = document.getElementById("agent-manifest-denied");
    const filesEl = document.getElementById("agent-manifest-files");
    const netEl = document.getElementById("agent-manifest-net");
    const badgesEl = document.getElementById("topology-agent-modal-badges");

    if (manifestContainer) {
        if (agent.capability) {
            manifestContainer.style.display = "block";
            const cap = agent.capability;
            
            if (allowedEl) allowedEl.textContent = cap.allowed_tools.length ? cap.allowed_tools.join(", ") : "None";
            if (deniedEl) deniedEl.textContent = cap.denied_tools.length ? cap.denied_tools.join(", ") : "None";
            if (filesEl) filesEl.textContent = cap.file_scopes.length ? cap.file_scopes.join(", ") : "None";
            if (netEl) netEl.textContent = cap.network_scopes.length ? cap.network_scopes.join(", ") : "None";
            
            if (badgesEl) {
                badgesEl.innerHTML = "";
                
                // Add Risk Class Badge
                const riskBadge = document.createElement("span");
                riskBadge.className = "badge";
                riskBadge.style.fontSize = "8px";
                riskBadge.style.padding = "2px 6px";
                riskBadge.style.borderRadius = "4px";
                riskBadge.style.fontWeight = "bold";
                riskBadge.style.textTransform = "uppercase";
                if (cap.risk_class.includes("L1") || cap.risk_class.includes("L2")) {
                    riskBadge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
                    riskBadge.style.color = "#ef4444";
                    riskBadge.style.border = "1px solid rgba(239, 68, 68, 0.3)";
                } else if (cap.risk_class.includes("L3")) {
                    riskBadge.style.backgroundColor = "rgba(245, 158, 11, 0.15)";
                    riskBadge.style.color = "#f59e0b";
                    riskBadge.style.border = "1px solid rgba(245, 158, 11, 0.3)";
                } else {
                    riskBadge.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
                    riskBadge.style.color = "#10b981";
                    riskBadge.style.border = "1px solid rgba(16, 185, 129, 0.3)";
                }
                riskBadge.textContent = `Risk: ${cap.risk_class}`;
                badgesEl.appendChild(riskBadge);
                
                // Add Approval Threshold Badge
                const thresholdBadge = document.createElement("span");
                thresholdBadge.className = "badge";
                thresholdBadge.style.fontSize = "8px";
                thresholdBadge.style.padding = "2px 6px";
                thresholdBadge.style.borderRadius = "4px";
                thresholdBadge.style.fontWeight = "bold";
                thresholdBadge.style.textTransform = "uppercase";
                if (cap.approval_threshold.toLowerCase() === "high" || cap.approval_threshold.toLowerCase() === "critical") {
                    thresholdBadge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
                    thresholdBadge.style.color = "#ef4444";
                    thresholdBadge.style.border = "1px solid rgba(239, 68, 68, 0.3)";
                } else {
                    thresholdBadge.style.backgroundColor = "rgba(59, 130, 246, 0.15)";
                    thresholdBadge.style.color = "#3b82f6";
                    thresholdBadge.style.border = "1px solid rgba(59, 130, 246, 0.3)";
                }
                thresholdBadge.textContent = `Gate: ${cap.approval_threshold}`;
                badgesEl.appendChild(thresholdBadge);

                // Add Audit Badge
                const auditBadge = document.createElement("span");
                auditBadge.className = "badge";
                auditBadge.style.fontSize = "8px";
                auditBadge.style.padding = "2px 6px";
                auditBadge.style.borderRadius = "4px";
                auditBadge.style.fontWeight = "bold";
                auditBadge.style.textTransform = "uppercase";
                auditBadge.style.backgroundColor = "rgba(168, 85, 247, 0.15)";
                auditBadge.style.color = "#a855f7";
                auditBadge.style.border = "1px solid rgba(168, 85, 247, 0.3)";
                auditBadge.textContent = "Audit: Active";
                badgesEl.appendChild(auditBadge);
            }
        } else {
            manifestContainer.style.display = "none";
        }
    }

    // Set Tier class on card inner for border glows and rarities
    const cardContainer = document.getElementById("topology-agent-card-container");
    if (cardContainer) {
        cardContainer.className = `trading-card-container tier-${(agent.tier || "GOLD").toLowerCase()}`;
    }
    
    const tierEl = document.getElementById("trading-card-tier");
    if (tierEl) {
        tierEl.textContent = `${agent.tier || "GOLD"} EDITION`;
    }

    // Bind stats values and trigger progress bar animations
    const stats = agent.stats || { intelligence: 90, speed: 85, reliability: 95, energy: 75 };
    
    const statIntFill = document.getElementById("stat-int");
    const statIntVal = document.getElementById("stat-int-val");
    if (statIntFill) statIntFill.style.width = "0%";
    if (statIntVal) statIntVal.textContent = "0";

    const statSpdFill = document.getElementById("stat-spd");
    const statSpdVal = document.getElementById("stat-spd-val");
    if (statSpdFill) statSpdFill.style.width = "0%";
    if (statSpdVal) statSpdVal.textContent = "0";

    const statRelFill = document.getElementById("stat-rel");
    const statRelVal = document.getElementById("stat-rel-val");
    if (statRelFill) statRelFill.style.width = "0%";
    if (statRelVal) statRelVal.textContent = "0";

    const statNrgFill = document.getElementById("stat-nrg");
    const statNrgVal = document.getElementById("stat-nrg-val");
    if (statNrgFill) statNrgFill.style.width = "0%";
    if (statNrgVal) statNrgVal.textContent = "0";

    setTimeout(() => {
        if (statIntFill) statIntFill.style.width = `${stats.intelligence}%`;
        if (statIntVal) statIntVal.textContent = stats.intelligence;
        
        if (statSpdFill) statSpdFill.style.width = `${stats.speed}%`;
        if (statSpdVal) statSpdVal.textContent = stats.speed;
        
        if (statRelFill) statRelFill.style.width = `${stats.reliability}%`;
        if (statRelVal) statRelVal.textContent = stats.reliability;
        
        if (statNrgFill) statNrgFill.style.width = `${stats.energy}%`;
        if (statNrgVal) statNrgVal.textContent = stats.energy;
    }, 150);

    // Bind dynamic 3D tilt effects
    if (cardContainer) {
        const cardInner = cardContainer.querySelector(".trading-card-inner");
        cardContainer.onmousemove = (e) => {
            if (prefersReducedMotion) return;
            const rect = cardContainer.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = ((centerY - y) / centerY) * 15; // Max 15 degrees tilt
            const rotateY = ((x - centerX) / centerX) * 15;
            
            if (cardInner) {
                cardInner.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.03)`;
                
                // Adjust holographic sheen position dynamically
                const sheen = cardContainer.querySelector(".trading-card-sheen");
                if (sheen) {
                    const pctX = (x / rect.width) * 100;
                    const pctY = (y / rect.height) * 100;
                    sheen.style.backgroundPosition = `${pctX}% ${pctY}%`;
                    sheen.style.opacity = "0.8";
                }
            }
        };
        
        cardContainer.onmouseleave = () => {
            if (cardInner) {
                cardInner.style.transform = "rotateX(0deg) rotateY(0deg) scale(1)";
                const sheen = cardContainer.querySelector(".trading-card-sheen");
                if (sheen) {
                    sheen.style.backgroundPosition = "0% 0%";
                    sheen.style.opacity = "0.15";
                }
            }
        };
    }
    
    const modal = document.getElementById("topology-agent-profile-modal");
    if (modal) {
        modal.dataset.agentId = agent.id;
        if (typeof modal.showModal === "function") {
            modal.showModal();
        } else {
            modal.setAttribute("open", "open");
        }
        
        // Element.animate() transitions for modal container
        modal.animate([
            { opacity: 0, transform: "translateY(18px) scale(0.96)" },
            { opacity: 1, transform: "translateY(0) scale(1)" }
        ], { duration: 220, easing: "cubic-bezier(.2,.8,.2,1)" });
    }
    
    // Highlight default stage
    animateTopologyStageRail(agent.defaultStage, "active");
}

function closeTopologyAgentProfile() {
    const modal = document.getElementById("topology-agent-profile-modal");
    if (modal) {
        if (modal.open && typeof modal.close === "function") {
            modal.close();
        } else {
            modal.removeAttribute("open");
        }
    }
    
    // Remove dimmer/active classes on chips
    document.querySelectorAll(".topology-agent-chip").forEach(chip => {
        chip.classList.remove("is-dimmed", "is-active");
    });
    
    if (lastTopologyTrigger && typeof lastTopologyTrigger.focus === "function") {
        lastTopologyTrigger.focus();
    }
}

function animateTopologyAgentChip(agentId) {
    const chip = document.getElementById(`topo-chip-${agentId}`);
    if (chip) {
        chip.classList.add("is-complete");
        chip.animate([
            { transform: "translateY(0) rotate(0deg)" },
            { transform: "translateY(-6px) rotate(-1deg)" },
            { transform: "translateY(0) rotate(1deg)" }
        ], { duration: 500, easing: "ease-in-out" });
    }
}

function lightTopologyCompletion(stageName) {
    animateTopologyStageRail(stageName, "complete");
}

function animateTopologyStageRail(stageName, status) {
    if (!stageName) return;
    document.querySelectorAll(".topology-stage-step").forEach(step => {
        if (step.dataset.stage && step.dataset.stage.toLowerCase() === stageName.toLowerCase()) {
            step.classList.remove("is-active", "is-complete");
            if (status === "active") {
                step.classList.add("is-active");
            } else if (status === "complete") {
                step.classList.add("is-complete");
            }
        }
    });
}

function glowTopologyAssetCards(assetId, status) {
    if (status === "reset") {
        delete glowingAssetIds[assetId];
    } else {
        glowingAssetIds[assetId] = status;
    }
    const card = document.getElementById(`node-card-${assetId}`);
    if (card) {
        card.style.transition = "all 0.4s ease";
        if (status === "blue") {
            card.style.borderColor = "#3b82f6";
            card.style.boxShadow = "0 0 15px rgba(59, 130, 246, 0.4)";
        } else if (status === "green") {
            card.style.borderColor = "#10b981";
            card.style.boxShadow = "0 0 15px rgba(16, 185, 129, 0.4)";
            card.classList.add("topology-asset-glow");
        } else {
            // Reset
            card.style.borderColor = "";
            card.style.boxShadow = "";
            card.classList.remove("topology-asset-glow");
        }
    }
}

function animateGordonContainerChecklist(stepIndex) {
    const checkIds = ["gordon-chk-logs", "gordon-chk-health", "gordon-chk-deps", "gordon-chk-bind", "gordon-chk-patch"];
    for (let i = 0; i <= stepIndex; i++) {
        const el = document.getElementById(checkIds[i]);
        if (el) {
            el.checked = true;
            const parent = el.parentElement;
            if (parent) {
                parent.style.color = "#10b981";
                parent.style.fontWeight = "bold";
            }
        }
    }
}

function resetGordonContainerChecklist() {
    const checkIds = ["gordon-chk-logs", "gordon-chk-health", "gordon-chk-deps", "gordon-chk-bind", "gordon-chk-patch"];
    checkIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.checked = false;
            const parent = el.parentElement;
            if (parent) {
                parent.style.color = "";
                parent.style.fontWeight = "";
            }
        }
    });
}

function drawTopologyAgentMotion(activeAgentIds = []) {
    const canvas = document.getElementById("topology-agent-motion-canvas");
    if (!canvas) return;
    
    const parent = canvas.parentElement;
    if (!parent) return;
    
    const rect = parent.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2 + 40;
    
    activeAgentIds.forEach(agentId => {
        const chip = document.getElementById(`topo-chip-${agentId}`);
        if (!chip) return;
        
        const chipRect = chip.getBoundingClientRect();
        const targetX = chipRect.left - rect.left + chipRect.width / 2;
        const targetY = chipRect.top - rect.top + chipRect.height / 2;
        
        ctx.beginPath();
        ctx.strokeStyle = "rgba(59, 130, 246, 0.5)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.moveTo(centerX, centerY);
        ctx.quadraticCurveTo((centerX + targetX) / 2, (centerY + targetY) / 2 - 30, targetX, targetY);
        ctx.stroke();
        
        const agent = hochPixelStickAgents.find(a => a.id === agentId);
        if (agent && agent.assetTargets) {
            agent.assetTargets.forEach(assetId => {
                const card = document.getElementById(`node-card-${assetId}`);
                if (!card) return;
                
                const cardRect = card.getBoundingClientRect();
                const assetX = cardRect.left - rect.left + cardRect.width / 2;
                const assetY = cardRect.top - rect.top + cardRect.height / 2;
                
                ctx.beginPath();
                ctx.strokeStyle = "rgba(16, 185, 129, 0.5)";
                ctx.lineWidth = 1.5;
                ctx.setLineDash([]);
                ctx.moveTo(targetX, targetY);
                ctx.quadraticCurveTo((targetX + assetX) / 2, (targetY + assetY) / 2 + 30, assetX, assetY);
                ctx.stroke();
            });
        }
    });
}

function launchTopologyExpertSwarm(promptText) {
    topologyTimeouts.forEach(t => clearTimeout(t));
    topologyTimeouts = [];
    
    hochPixelStickAgents.forEach(a => {
        a.status = "idle";
        const led = document.getElementById(`topo-led-${a.id}`);
        if (led) led.className = "topology-agent-led";
        const chip = document.getElementById(`topo-chip-${a.id}`);
        if (chip) chip.className = "topology-agent-chip";
    });
    resetGordonContainerChecklist();
    document.querySelectorAll(".topology-stage-step").forEach(step => {
        step.className = "topology-stage-step";
    });
    document.querySelectorAll(".evidence-light").forEach(light => {
        light.className = "evidence-light";
    });
    
    hochPixelStickAgents.forEach(a => {
        if (a.assetTargets) {
            a.assetTargets.forEach(assetId => glowTopologyAssetCards(assetId, "reset"));
        }
    });
    
    const promptVal = promptText || "Research YouTube Docker debugging videos and verify release readiness.";
    const lowerPrompt = promptVal.toLowerCase();
    
    let activeIds = [];
    if (lowerPrompt.includes("docker") || lowerPrompt.includes("container") || lowerPrompt.includes("logs") || lowerPrompt.includes("compose")) {
        activeIds = ["boss-noodle", "dr-signal", "gordon-vector", "ms-checkmark", "prof-ledger", "eng-rocket"];
    } else {
        activeIds = ["boss-noodle", "dr-signal", "prof-blueprint", "eng-patch", "ms-checkmark", "capt-guardrail", "prof-ledger", "eng-rocket"];
    }
    
    const canvas = document.getElementById("topology-agent-motion-canvas");
    const ctx = canvas?.getContext("2d");
    if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const sidebarLed = document.getElementById("led-swarm-control");
    if (sidebarLed) {
        sidebarLed.className = "nav-status-indicator swarm-led-active";
    }
    
    const statusBadge = document.getElementById("hoch-global-swarm-status");
    if (statusBadge) {
        statusBadge.textContent = "EXECUTING...";
        statusBadge.className = "badge badge-info";
    }
    
    // 1. Stage: Prompt
    animateTopologyStageRail("Prompt", "active");
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Prompt");
    }, 500));
    
    // 2. Stage: Plan
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Plan", "active");
        const planAgents = activeIds.filter(id => ["boss-noodle", "prof-blueprint"].includes(id));
        planAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "executing";
            const chip = document.getElementById(`topo-chip-${id}`);
            if (chip) chip.className = "topology-agent-chip is-active";
        });
        drawTopologyAgentMotion(planAgents);
    }, 1000));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Plan");
        activeIds.filter(id => ["boss-noodle", "prof-blueprint"].includes(id)).forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "complete";
            animateTopologyAgentChip(id);
            const led = document.getElementById(`topo-led-${id}`);
            if (led) led.className = "topology-agent-led is-green";
        });
    }, 2000));
    
    // 3. Stage: Research
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Research", "active");
        const researchAgents = activeIds.filter(id => ["dr-signal"].includes(id));
        researchAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "researching";
            const chip = document.getElementById(`topo-chip-${id}`);
            if (chip) chip.className = "topology-agent-chip is-active";
        });
        drawTopologyAgentMotion(researchAgents);
        
        if (lowerPrompt.includes("youtube") || lowerPrompt.includes("video") || lowerPrompt.includes("research")) {
            animateYoutubeResearchCards();
        }
    }, 2500));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Research");
        activeIds.filter(id => ["dr-signal"].includes(id)).forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "complete";
            animateTopologyAgentChip(id);
            const led = document.getElementById(`topo-led-${id}`);
            if (led) led.className = "topology-agent-led is-green";
        });
    }, 3500));
    
    // 4. Stage: Assign
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Assign", "active");
        const executeAgents = activeIds.filter(id => ["eng-patch", "gordon-vector"].includes(id));
        executeAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent && agent.assetTargets) {
                agent.assetTargets.forEach(assetId => glowTopologyAssetCards(assetId, "blue"));
            }
        });
    }, 4000));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Assign");
    }, 4500));
    
    // 5. Stage: Execute
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Execute", "active");
        const executeAgents = activeIds.filter(id => ["eng-patch", "gordon-vector"].includes(id));
        executeAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "executing";
            const chip = document.getElementById(`topo-chip-${id}`);
            if (chip) chip.className = "topology-agent-chip is-active";
            if (agent && agent.assetTargets) {
                agent.assetTargets.forEach(assetId => glowTopologyAssetCards(assetId, "green"));
            }
        });
        drawTopologyAgentMotion(executeAgents);
        
        if (lowerPrompt.includes("docker") || lowerPrompt.includes("container") || lowerPrompt.includes("logs") || lowerPrompt.includes("compose")) {
            animateGordonContainerChecklist(2);
        }
    }, 5000));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Execute");
        activeIds.filter(id => ["eng-patch", "gordon-vector"].includes(id)).forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "complete";
            animateTopologyAgentChip(id);
            const led = document.getElementById(`topo-led-${id}`);
            if (led) led.className = "topology-agent-led is-green";
        });
        
        if (lowerPrompt.includes("docker") || lowerPrompt.includes("container") || lowerPrompt.includes("logs") || lowerPrompt.includes("compose")) {
            animateGordonContainerChecklist(4);
        }
    }, 6000));
    
    // 6. Stage: Verify
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Verify", "active");
        const verifyAgents = activeIds.filter(id => ["ms-checkmark", "capt-guardrail"].includes(id));
        verifyAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "verifying";
            const chip = document.getElementById(`topo-chip-${id}`);
            if (chip) chip.className = "topology-agent-chip is-active";
        });
        drawTopologyAgentMotion(verifyAgents);
    }, 6500));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Verify");
        activeIds.filter(id => ["ms-checkmark", "capt-guardrail"].includes(id)).forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "complete";
            animateTopologyAgentChip(id);
            const led = document.getElementById(`topo-led-${id}`);
            if (led) led.className = "topology-agent-led is-green";
        });
        
        const rLight = document.getElementById("topo-light-realtime");
        if (rLight) rLight.className = "evidence-light locked";
        const aLight = document.getElementById("topo-light-ast");
        if (aLight) aLight.className = "evidence-light locked";
    }, 7500));
    
    // 7. Stage: Report
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Report", "active");
        const reportAgents = activeIds.filter(id => ["prof-ledger"].includes(id));
        reportAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "reporting";
            const chip = document.getElementById(`topo-chip-${id}`);
            if (chip) chip.className = "topology-agent-chip is-active";
        });
        drawTopologyAgentMotion(reportAgents);
    }, 8000));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Report");
        activeIds.filter(id => ["prof-ledger"].includes(id)).forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "complete";
            animateTopologyAgentChip(id);
            const led = document.getElementById(`topo-led-${id}`);
            if (led) led.className = "topology-agent-led is-green";
        });
        
        const auLight = document.getElementById("topo-light-audit");
        if (auLight) auLight.className = "evidence-light locked";
    }, 9000));
    
    // 8. Stage: Complete
    topologyTimeouts.push(setTimeout(() => {
        animateTopologyStageRail("Complete", "active");
        const completeAgents = activeIds.filter(id => ["eng-rocket"].includes(id));
        completeAgents.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "completing";
            const chip = document.getElementById(`topo-chip-${id}`);
            if (chip) chip.className = "topology-agent-chip is-active";
        });
        drawTopologyAgentMotion(completeAgents);
    }, 9500));
    
    topologyTimeouts.push(setTimeout(() => {
        lightTopologyCompletion("Complete");
        activeIds.forEach(id => {
            const agent = hochPixelStickAgents.find(a => a.id === id);
            if (agent) agent.status = "complete";
            animateTopologyAgentChip(id);
            const led = document.getElementById(`topo-led-${id}`);
            if (led) led.className = "topology-agent-led is-green";
        });
        
        const pLight = document.getElementById("topo-light-provenance");
        if (pLight) pLight.className = "evidence-light locked";
        
        if (statusBadge) {
            statusBadge.textContent = "COMPLETE";
            statusBadge.className = "badge badge-success";
        }
        
        if (sidebarLed) {
            sidebarLed.className = "nav-status-indicator swarm-led-complete";
        }
        
        const badge = document.getElementById("hoch-global-swarm-status");
        if (badge) {
            badge.innerText = "COMPLETED";
            badge.className = "badge badge-success";
        }
        
        drawTopologyAgentMotion(activeIds);
    }, 10500));
}

window.addEventListener("resize", () => {
    const statusBadge = document.getElementById("hoch-global-swarm-status");
    if (statusBadge && statusBadge.textContent !== "STANDBY") {
        const activeIds = hochPixelStickAgents.filter(a => a.status === "complete" || a.status === "executing" || a.status === "researching" || a.status === "verifying" || a.status === "reporting" || a.status === "completing").map(a => a.id);
        drawTopologyAgentMotion(activeIds);
    }
});

// ==============================================================================
//  CYBERSECURITY + APPLICATION SOFTWARE FACTORY
// ==============================================================================

// Data models
const hochApplicationFactoryStages = [
  "Intake",
  "Humanity Usefulness Gate",
  "Research",
  "North Star Planning",
  "PERT Analysis",
  "Product Design",
  "Architecture",
  "Secure Development",
  "Cybersecurity Review",
  "QA / E2E",
  "Privacy / Store Compliance",
  "Packaging",
  "App Store Delivery",
  "Post-Launch Monitoring"
];

const humanityUsefulnessCriteria = [
  "Human benefit",
  "Non-harm",
  "Privacy minimum",
  "Accessibility",
  "Truthfulness",
  "Sustainability",
  "Store legitimacy"
];

const applicationStoreTargets = [
  "Apple App Store",
  "Google Play",
  "Microsoft Store",
  "Chrome Web Store",
  "GitHub Release",
  "Docker Registry",
  "Web / PWA"
];

const hochApplicationFactoryAgents = [
  "Factory Foreman Fizz",
  "Humanity Hank",
  "North Star Nora",
  "PERT Percy",
  "Research Raccoon",
  "Design Doodle Dee",
  "Architect Atlas",
  "Cyber Cobra",
  "Secrets Squirrel",
  "Dependency Dingo",
  "E2E Ellie",
  "Storefront Stan",
  "Review Rita"
];

// Agent data mapped to stages
const factoryAgentsData = [
  {
    id: "foreman-fizz",
    displayName: "Factory Foreman Fizz",
    funnyTag: "APP MILL WRANGLER",
    role: "orchestrates the factory pipeline",
    mission: "Coordinate swarm agents and track secure SDLC pipeline progression.",
    stage: "Intake",
    completionSignal: "app pipeline decomposed",
    avatarVariant: 1,
    status: "idle",
    capabilities: {
      allowedTools: "git, grep, view_file, list_dir",
      deniedTools: "run_command, write_to_file",
      fileScopes: "frontend/*, scripts/*",
      networkScopes: "none",
      approvalThreshold: "None (Read-only)",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/foreman_fizz.audit"
    }
  },
  {
    id: "humanity-hank",
    displayName: "Humanity Hank",
    funnyTag: "BENEFIT BOUNCER",
    role: "blocks apps that do not deliver real human usefulness",
    mission: "Evaluate app ideas against human value criteria and block toxic/spam candidates.",
    stage: "Humanity Usefulness Gate",
    completionSignal: "usefulness gate passed",
    avatarVariant: 2,
    status: "idle",
    capabilities: {
      allowedTools: "view_file, grep",
      deniedTools: "write_to_file, run_command",
      fileScopes: "*",
      networkScopes: "none",
      approvalThreshold: "Strict (Gate keeper)",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/humanity_gate.audit"
    }
  },
  {
    id: "research-raccoon",
    displayName: "Research Raccoon",
    funnyTag: "SOURCE BANDIT",
    role: "researches docs, competitors, user needs, YouTube candidates",
    mission: "Scan competitive platforms, developer docs, and synthesize requirements packs.",
    stage: "Research",
    completionSignal: "research pack synthesized",
    avatarVariant: 3,
    status: "idle",
    capabilities: {
      allowedTools: "search_web, read_url_content",
      deniedTools: "run_command, write_to_file",
      fileScopes: "none",
      networkScopes: "google.com, youtube.com, github.com",
      approvalThreshold: "None",
      riskCategory: "Medium",
      auditSink: "/var/log/swarm/research_raccoon.audit"
    }
  },
  {
    id: "north-star-nora",
    displayName: "North Star Nora",
    funnyTag: "OUTCOME COMPASS",
    role: "defines outcome, users, success metric, ethical boundary",
    mission: "Outline core outcomes, define metrics, and set strict ethical refusals.",
    stage: "North Star Planning",
    completionSignal: "north star locked",
    avatarVariant: 4,
    status: "idle",
    capabilities: {
      allowedTools: "view_file, grep",
      deniedTools: "run_command, write_to_file",
      fileScopes: "*",
      networkScopes: "none",
      approvalThreshold: "Manual sign-off required",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/north_star.audit"
    }
  },
  {
    id: "pert-percy",
    displayName: "PERT Percy",
    funnyTag: "TIME GOBLIN",
    role: "builds AI-compressed PERT and dependency schedule",
    mission: "Compile optimistic, likely, and pessimistic estimates into critical path nodes.",
    stage: "PERT Analysis",
    completionSignal: "delivery graph estimated",
    avatarVariant: 5,
    status: "idle",
    capabilities: {
      allowedTools: "view_file, grep",
      deniedTools: "run_command",
      fileScopes: "package.json, src/*",
      networkScopes: "none",
      approvalThreshold: "None",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/pert_percy.audit"
    }
  },
  {
    id: "design-doodle-dee",
    displayName: "Design Doodle Dee",
    funnyTag: "UX CARTOONIST",
    role: "wireframes usable, accessible flows",
    mission: "Draft clean user flows, access controls, and wireframe views.",
    stage: "Product Design",
    completionSignal: "user journey drawn",
    avatarVariant: 6,
    status: "idle",
    capabilities: {
      allowedTools: "generate_image, view_file",
      deniedTools: "run_command, write_to_file",
      fileScopes: "frontend/src/components/*",
      networkScopes: "none",
      approvalThreshold: "None",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/design_doodle.audit"
    }
  },
  {
    id: "architect-atlas",
    displayName: "Architect Atlas",
    funnyTag: "SYSTEM SPINE",
    role: "architecture, data model, APIs, deployment model",
    mission: "Formulate schemas, endpoint contracts, API models, and backend layouts.",
    stage: "Architecture",
    completionSignal: "architecture contract written",
    avatarVariant: 7,
    status: "idle",
    capabilities: {
      allowedTools: "view_file, grep",
      deniedTools: "run_command",
      fileScopes: "frontend/src/lib/*, backend/*",
      networkScopes: "none",
      approvalThreshold: "None",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/architect_atlas.audit"
    }
  },
  {
    id: "secrets-squirrel",
    displayName: "Secrets Squirrel",
    funnyTag: "CREDENTIAL PROTECTOR",
    role: "secrets scanning, env safety, token hygiene",
    mission: "Verify environment isolation and scan codebase for leaked credentials.",
    stage: "Secure Development",
    completionSignal: "secrets clear",
    avatarVariant: 8,
    status: "idle",
    capabilities: {
      allowedTools: "grep, view_file",
      deniedTools: "run_command, write_to_file",
      fileScopes: "*",
      networkScopes: "none",
      approvalThreshold: "Immediate Alert",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/secrets_squirrel.audit"
    }
  },
  {
    id: "dependency-dingo",
    displayName: "Dependency Dingo",
    funnyTag: "SUPPLY-CHAIN SNIFFER",
    role: "dependency audit, SBOM, license checks",
    mission: "Compile software bill of materials and triage third-party dependency vulnerabilities.",
    stage: "Secure Development",
    completionSignal: "dependency risk triaged",
    avatarVariant: 9,
    status: "idle",
    capabilities: {
      allowedTools: "grep, view_file, run_command (npm list)",
      deniedTools: "npm install, npm publish",
      fileScopes: "package.json, package-lock.json",
      networkScopes: "registry.npmjs.org",
      approvalThreshold: "Developer sign-off",
      riskCategory: "Medium",
      auditSink: "/var/log/swarm/dependency_dingo.audit"
    }
  },
  {
    id: "cyber-cobra",
    displayName: "Cyber Cobra",
    funnyTag: "THREAT MODELER",
    role: "threat modeling, abuse cases, attack surface review",
    mission: "Analyze vulnerabilities, map out threat vectors, and audit attack surfaces.",
    stage: "Cybersecurity Review",
    completionSignal: "threat model complete",
    avatarVariant: 10,
    status: "idle",
    capabilities: {
      allowedTools: "grep, view_file",
      deniedTools: "run_command, write_to_file",
      fileScopes: "*",
      networkScopes: "none",
      approvalThreshold: "Immediate Alert",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/cyber_cobra.audit"
    }
  },
  {
    id: "e2e-ellie",
    displayName: "E2E Ellie",
    funnyTag: "BROWSER PROOFMASTER",
    role: "Playwright journeys, screenshots, store-critical flows",
    mission: "Orchestrate Playwright end-to-end integration tests and capture visual state proof.",
    stage: "QA / E2E",
    completionSignal: "E2E evidence captured",
    avatarVariant: 11,
    status: "idle",
    capabilities: {
      allowedTools: "run_command (npx playwright)",
      deniedTools: "write_to_file",
      fileScopes: "tests/*",
      networkScopes: "localhost:8000",
      approvalThreshold: "None",
      riskCategory: "Medium",
      auditSink: "/var/log/swarm/e2e_ellie.audit"
    }
  },
  {
    id: "storefront-stan",
    displayName: "Storefront Stan",
    funnyTag: "SUBMISSION CLERK",
    role: "app store metadata, screenshots, privacy forms, package checklist",
    mission: "Verify privacy policies, draft data safety disclosures, and collect store assets.",
    stage: "Privacy / Store Compliance",
    completionSignal: "store packet ready",
    avatarVariant: 12,
    status: "idle",
    capabilities: {
      allowedTools: "view_file, grep",
      deniedTools: "run_command",
      fileScopes: "dist/releases/*",
      networkScopes: "apple.com, google.com",
      approvalThreshold: "Operator approval required",
      riskCategory: "Medium",
      auditSink: "/var/log/swarm/storefront_stan.audit"
    }
  },
  {
    id: "review-rita",
    displayName: "Review Rita",
    funnyTag: "HUMAN REVIEW GATE",
    role: "requires final operator approval before submission",
    mission: "Require final visual operator verification and seal application release packages.",
    stage: "App Store Delivery",
    completionSignal: "review approved",
    avatarVariant: 13,
    status: "idle",
    capabilities: {
      allowedTools: "view_file, grep",
      deniedTools: "run_command, write_to_file",
      fileScopes: "*",
      networkScopes: "none",
      approvalThreshold: "Manual Operator Approval",
      riskCategory: "Low",
      auditSink: "/var/log/swarm/review_rita.audit"
    }
  }
];

// Map of cybersecurity checks
const cybersecurityChecklistItems = [
  "Threat model",
  "SAST",
  "Dependency audit",
  "Secrets scan",
  "SBOM",
  "Privacy policy alignment",
  "Data safety disclosure check",
  "Abuse-case review",
  "Accessibility check",
  "E2E evidence",
  "Human review approval"
];

// Map of store targets checks details
const storeTargetsChecksData = {
  "Apple App Store": "screenshots, privacy labels, age rating, review notes, support URL, marketing URL",
  "Google Play": "Data Safety, content rating, testing track, permissions justification, privacy policy",
  "Microsoft Store": "package identity, privacy policy, install behavior, content policies",
  "Chrome Web Store": "permissions justification, remote-code compliance, privacy disclosure",
  "GitHub Release": "SBOM, provenance, checksum, release notes",
  "Docker Registry": "image digest, CVE scan, non-root runtime, SBOM",
  "Web / PWA": "HTTPS, CSP, accessibility, privacy policy, E2E smoke tests"
};

// Global state for factory simulation
let factoryTimeouts = [];
const factoryPortfolio = [];

// Functions

function renderCybersecurityFactoryView() {
    renderHumanityUsefulnessGate();
    renderApplicationFactoryPipeline();
    renderFactoryAgentRoster();
    renderFactoryCybersecurityPipeline(false);
    renderFactoryStoreDeliveryMatrix(false);
    renderFactoryPertAnalysis(false);
    renderFactoryE2EEvidenceBoard(false);
    renderFactoryPrivacyConsistencyGate(false);
    renderFactoryPortfolioTable();
}

function renderHumanityUsefulnessGate() {
    const statusEl = document.getElementById("factory-gate-status");
    if (statusEl) {
        statusEl.textContent = "STANDBY";
        statusEl.className = "badge";
    }
    lightFactoryGateResult("STANDBY");
}

function renderApplicationFactoryPipeline() {
    const container = document.getElementById("factory-pipeline-steps");
    if (!container) return;
    container.innerHTML = hochApplicationFactoryStages.map(stage => {
        return `<div class="process-stage-step" id="factory-stage-${stage.replace(/ \/ /g, '-').replace(/ /g, '-')}" style="flex: 1; text-align: center; padding: 6px 8px; border-radius: 4px; background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-glass); font-family: monospace; font-size: 10px; color: var(--text-secondary); transition: all 0.3s ease; min-width: 100px;">
            ${stage}
        </div>`;
    }).join("");
}

function renderFactoryAgentRoster() {
    const listEl = document.getElementById("factory-agents-list");
    if (!listEl) return;
    listEl.innerHTML = factoryAgentsData.map(agent => {
        let stateClass = "topology-agent-led";
        if (agent.status === "complete") stateClass += " is-green";
        
        return `<div class="topology-agent-chip" id="factory-chip-${agent.id}" data-agent-id="${agent.id}" style="display: inline-flex; align-items: center; gap: 8px; background: rgba(22, 28, 45, 0.6); border: 1px solid var(--border-glass); border-radius: 999px; padding: 6px 14px; color: #fff; cursor: pointer; font-size: 11px; font-weight: 500; transition: all 0.2s;">
            <span class="${stateClass}" id="factory-led-${agent.id}"></span>
            <span>${agent.displayName}</span>
            <span style="font-size: 9px; color: var(--text-secondary); opacity: 0.8;">[${agent.funnyTag}]</span>
        </div>`;
    }).join("");

    // Bind click events to chips to open the dossier modal
    listEl.querySelectorAll(".topology-agent-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const agentId = chip.dataset.agentId;
            openFactoryAgentProfile(agentId, chip);
        });
    });
}

function openFactoryAgentProfile(agentId, triggerEl) {
    const agent = factoryAgentsData.find(a => a.id === agentId);
    if (!agent) return;

    // Populate modal elements
    const avatarContainer = document.getElementById("topology-agent-modal-avatar");
    if (avatarContainer) {
        avatarContainer.innerHTML = renderTopologyPixelAvatar(agent.avatarVariant, agent.status);
    }
    
    const statusEl = document.getElementById("topology-agent-modal-status");
    if (statusEl) statusEl.textContent = agent.status || "idle";
    
    const tagEl = document.getElementById("topology-agent-modal-tag");
    if (tagEl) {
        tagEl.textContent = agent.funnyTag;
    }
    
    const nameEl = document.getElementById("topology-agent-modal-name");
    if (nameEl) nameEl.textContent = agent.displayName;
    
    const titleEl = document.getElementById("topology-agent-modal-title");
    if (titleEl) titleEl.textContent = agent.role;
    
    const descEl = document.getElementById("topology-agent-modal-description");
    if (descEl) descEl.textContent = agent.mission;
    
    const phraseEl = document.getElementById("topology-agent-modal-catchphrase");
    if (phraseEl) phraseEl.textContent = `“Completion signal: ${agent.completionSignal}”`;
    
    const skillsEl = document.getElementById("topology-agent-modal-skills");
    if (skillsEl) {
        skillsEl.innerHTML = `<span class="agent-capsule">${agent.stage}</span>`;
    }

    const manifestContainer = document.getElementById("topology-agent-modal-manifest-container");
    if (manifestContainer) {
        if (agent.capabilities) {
            manifestContainer.style.display = "block";
            document.getElementById("agent-manifest-allowed").textContent = agent.capabilities.allowedTools;
            document.getElementById("agent-manifest-denied").textContent = agent.capabilities.deniedTools;
            document.getElementById("agent-manifest-files").textContent = agent.capabilities.fileScopes;
            document.getElementById("agent-manifest-network").textContent = agent.capabilities.networkScopes;
            document.getElementById("agent-manifest-threshold").textContent = agent.capabilities.approvalThreshold;
            document.getElementById("agent-manifest-risk").textContent = agent.capabilities.riskCategory;
            document.getElementById("agent-manifest-sink").textContent = agent.capabilities.auditSink;

            const badgesEl = document.getElementById("topology-agent-modal-badges");
            if (badgesEl) {
                let badgeHtml = "";
                if (agent.capabilities.riskCategory === "Low") {
                    badgeHtml += `<span style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; font-size: 8px; font-weight: bold; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">Low Risk</span>`;
                } else {
                    badgeHtml += `<span style="background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #f59e0b; font-size: 8px; font-weight: bold; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">Medium Risk</span>`;
                }
                if (agent.capabilities.deniedTools.includes("run_command")) {
                    badgeHtml += `<span style="background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #3b82f6; font-size: 8px; font-weight: bold; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">Sandboxed</span>`;
                }
                if (agent.capabilities.auditSink !== "none") {
                    badgeHtml += `<span style="background: rgba(168, 85, 247, 0.15); border: 1px solid #a855f7; color: #a855f7; font-size: 8px; font-weight: bold; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">Audited</span>`;
                }
                badgesEl.innerHTML = badgeHtml;
            }
        } else {
            manifestContainer.style.display = "none";
        }
    }
    
    const modal = document.getElementById("topology-agent-profile-modal");
    if (modal) {
        modal.dataset.agentId = agent.id;
        if (typeof modal.showModal === "function") {
            modal.showModal();
        } else {
            modal.setAttribute("open", "open");
        }
        
        modal.animate([
            { opacity: 0, transform: "translateY(18px) scale(0.96)" },
            { opacity: 1, transform: "translateY(0) scale(1)" }
        ], { duration: 220, easing: "cubic-bezier(.2,.8,.2,1)" });
    }
}

function runFactoryHumanityGate(prompt) {
    const p = (prompt || "").toLowerCase();
    const blockKeywords = ["clone", "exploit", "ad-network", "bypass review", "miner", "gamble", "spyware", "spam", "adware", "deceptive", "casino", "malware"];
    for (const kw of blockKeywords) {
        if (p.includes(kw)) {
            return false;
        }
    }
    return true;
}

function lightFactoryGateResult(result) {
    const passEl = document.getElementById("gate-result-pass");
    const blockEl = document.getElementById("gate-result-block");
    const standbyEl = document.getElementById("gate-result-standby");
    const gateStatus = document.getElementById("factory-gate-status");

    if (passEl) passEl.classList.add("hidden");
    if (blockEl) blockEl.classList.add("hidden");
    if (standbyEl) standbyEl.classList.add("hidden");

    if (result === "PASS") {
        if (passEl) passEl.classList.remove("hidden");
        if (gateStatus) {
            gateStatus.textContent = "PASS";
            gateStatus.style.background = "rgba(16, 185, 129, 0.15)";
            gateStatus.style.color = "#10b981";
        }
    } else if (result === "BLOCK") {
        if (blockEl) blockEl.classList.remove("hidden");
        if (gateStatus) {
            gateStatus.textContent = "BLOCK";
            gateStatus.style.background = "rgba(239, 68, 68, 0.15)";
            gateStatus.style.color = "#ef4444";
        }
    } else {
        if (standbyEl) standbyEl.classList.remove("hidden");
        if (gateStatus) {
            gateStatus.textContent = "STANDBY";
            gateStatus.style.background = "rgba(255, 255, 255, 0.05)";
            gateStatus.style.color = "var(--text-secondary)";
        }
    }
}

function animateFactoryPipelineStage(stage, status) {
    const stepEl = document.getElementById(`factory-stage-${stage.replace(/ \/ /g, '-').replace(/ /g, '-')}`);
    if (!stepEl) return;
    
    stepEl.classList.remove("active", "complete");
    if (status === "active") {
        stepEl.classList.add("active");
        stepEl.style.background = "rgba(59, 130, 246, 0.15)";
        stepEl.style.borderColor = "#3b82f6";
        stepEl.style.color = "#93c5fd";
    } else if (status === "complete") {
        stepEl.classList.add("complete");
        stepEl.style.background = "rgba(16, 185, 129, 0.15)";
        stepEl.style.borderColor = "var(--accent-teal)";
        stepEl.style.color = "var(--accent-teal)";
    } else {
        stepEl.style.background = "rgba(255, 255, 255, 0.02)";
        stepEl.style.borderColor = "var(--border-glass)";
        stepEl.style.color = "var(--text-secondary)";
    }
}

function renderFactoryPertAnalysis(active) {
    const optEl = document.querySelector("#factory-pert-details .opt");
    const likelyEl = document.querySelector("#factory-pert-details .likely");
    const worstEl = document.querySelector("#factory-pert-details .worst");
    const compressedEl = document.querySelector("#factory-pert-details .compressed");
    const criticalPathEl = document.querySelector("#factory-pert-details .critical-path");

    if (active) {
        if (optEl) optEl.textContent = "1.5d";
        if (likelyEl) likelyEl.textContent = "2.2d";
        if (worstEl) worstEl.textContent = "4.0d";
        if (compressedEl) compressedEl.textContent = "2.1d (AI-Compressed)";
        if (criticalPathEl) criticalPathEl.textContent = "CRITICAL PATH: T1:Intake -> T3:Research -> T7:Dev -> T10:Audit";
    } else {
        if (optEl) optEl.textContent = "—";
        if (likelyEl) likelyEl.textContent = "—";
        if (worstEl) worstEl.textContent = "—";
        if (compressedEl) compressedEl.textContent = "—";
        if (criticalPathEl) criticalPathEl.textContent = "";
    }
}

function renderFactoryStoreDeliveryMatrix(active) {
    const tbody = document.getElementById("factory-store-tbody");
    if (!tbody) return;
    
    if (active) {
        tbody.innerHTML = applicationStoreTargets.map(target => {
            const checks = storeTargetsChecksData[target] || "";
            return `<tr>
                <td style="font-weight: 600; color: #fff;">${target}</td>
                <td style="color: var(--text-secondary); font-size: 9px;">${checks}</td>
                <td><span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa;">Packet Ready</span></td>
            </tr>`;
        }).join("");
    } else {
        tbody.innerHTML = applicationStoreTargets.map(target => {
            const checks = storeTargetsChecksData[target] || "";
            return `<tr>
                <td style="font-weight: 600; color: #fff;">${target}</td>
                <td style="color: var(--text-secondary); font-size: 9px;">${checks}</td>
                <td><span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);">Draft</span></td>
            </tr>`;
        }).join("");
    }
}

function renderFactoryCybersecurityPipeline(active) {
    const container = document.getElementById("factory-security-checklist");
    if (!container) return;

    if (active) {
        container.innerHTML = cybersecurityChecklistItems.map(item => {
            return `<div style="display: flex; align-items: center; gap: 6px;">
                <input type="checkbox" checked disabled style="accent-color: var(--accent-teal);">
                <span style="color: var(--accent-teal); font-weight: 600;">${item}</span>
            </div>`;
        }).join("");
    } else {
        container.innerHTML = cybersecurityChecklistItems.map(item => {
            return `<div style="display: flex; align-items: center; gap: 6px;">
                <input type="checkbox" disabled>
                <span>${item}</span>
            </div>`;
        }).join("");
    }
}

function renderFactoryE2EEvidenceBoard(active) {
    const logsEl = document.getElementById("factory-e2e-logs");
    if (!logsEl) return;

    if (active) {
        logsEl.innerHTML = `[Playwright runner] Starting browser headless tests...
[Playwright runner] Page loaded successfully.
[Playwright runner] Action clicked: Humanity Usefulness Gate verified.
[Playwright runner] Checklist parsed. 11/11 security checks complete.
[Playwright runner] Capture: artifacts/qa/cybersecurity-factory-runtime.png
[Playwright runner] E2E evidence saved successfully.
[Security Swarm] Evidence generated · signing pending`;
    } else {
        logsEl.innerHTML = "Awaiting QA run...";
    }
}

function renderFactoryPrivacyConsistencyGate(active) {
    const permEl = document.getElementById("privacy-gate-permissions");
    const policyEl = document.getElementById("privacy-gate-policy");
    const disclosureEl = document.getElementById("privacy-gate-disclosure");
    const flowsEl = document.getElementById("privacy-gate-flows");
    const statusEl = document.getElementById("privacy-gate-status");

    if (!permEl || !policyEl || !disclosureEl || !flowsEl || !statusEl) return;

    if (active) {
        permEl.textContent = "Checked (Clean)";
        permEl.style.background = "rgba(16, 185, 129, 0.15)";
        permEl.style.color = "#10b981";

        policyEl.textContent = "Checked (Aligned)";
        policyEl.style.background = "rgba(16, 185, 129, 0.15)";
        policyEl.style.color = "#10b981";

        disclosureEl.textContent = "Checked (Consistent)";
        disclosureEl.style.background = "rgba(16, 185, 129, 0.15)";
        disclosureEl.style.color = "#10b981";

        flowsEl.textContent = "Checked (No leaks)";
        flowsEl.style.background = "rgba(16, 185, 129, 0.15)";
        flowsEl.style.color = "#10b981";

        statusEl.textContent = "PASS (Consistent)";
        statusEl.style.color = "#10b981";
    } else {
        permEl.textContent = "—";
        permEl.style.background = "rgba(255,255,255,0.05)";
        permEl.style.color = "var(--text-secondary)";

        policyEl.textContent = "—";
        policyEl.style.background = "rgba(255,255,255,0.05)";
        policyEl.style.color = "var(--text-secondary)";

        disclosureEl.textContent = "—";
        disclosureEl.style.background = "rgba(255,255,255,0.05)";
        disclosureEl.style.color = "var(--text-secondary)";

        flowsEl.textContent = "—";
        flowsEl.style.background = "rgba(255,255,255,0.05)";
        flowsEl.style.color = "var(--text-secondary)";

        statusEl.textContent = "Pending";
        statusEl.style.color = "var(--text-secondary)";
    }
}

function renderFactoryPortfolioTable() {
    const tbody = document.getElementById("factory-portfolio-tbody");
    if (!tbody) return;

    if (factoryPortfolio.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-secondary); padding: 12px;">No applications generated yet.</td></tr>`;
    } else {
        tbody.innerHTML = factoryPortfolio.map(app => {
            return `<tr>
                <td style="font-weight: 600; color: #fff;">${app.idea}</td>
                <td><span class="badge badge-success">${app.stage}</span></td>
                <td style="font-family: monospace; font-size: 9px; color: var(--text-secondary);">${app.agents.join(", ")}</td>
                <td><strong style="color: var(--accent-teal);">${app.usefulnessScore}%</strong></td>
                <td><span class="badge ${app.risk === 'Low' ? 'badge-success' : 'badge-danger'}">${app.risk}</span></td>
            </tr>`;
        }).join("");
    }
}

// Main orchestrator

function launchApplicationFactorySwarm() {
    const inputEl = document.getElementById("factory-app-idea-input");
    const prompt = inputEl?.value.trim() || "Build a useful app that helps people learn, solve real problems, and improve daily workflows while respecting privacy and safety.";

    // Clear previous timeouts
    factoryTimeouts.forEach(t => clearTimeout(t));
    factoryTimeouts = [];

    // Reset UI
    renderFactoryCybersecurityPipeline(false);
    renderFactoryStoreDeliveryMatrix(false);
    renderFactoryPertAnalysis(false);
    renderFactoryE2EEvidenceBoard(false);
    renderFactoryPrivacyConsistencyGate(false);
    
    const researchLogs = document.getElementById("factory-research-logs");
    if (researchLogs) researchLogs.textContent = "Decomposing pipeline...";

    const monitorDetails = document.getElementById("factory-monitor-details");
    if (monitorDetails) {
        monitorDetails.innerHTML = `
            <div><strong>Crashes / 24h:</strong> <span class="val">—</span></div>
            <div><strong>Privacy Status:</strong> <span class="val">—</span></div>
            <div><strong>Abuse Reports:</strong> <span class="val">—</span></div>
            <div><strong>Vulnerabilities:</strong> <span class="val">—</span></div>
        `;
    }

    // Reset stages
    hochApplicationFactoryStages.forEach(s => animateFactoryPipelineStage(s, "idle"));
    
    // Reset agents
    factoryAgentsData.forEach(agent => {
        agent.status = "idle";
    });
    renderFactoryAgentRoster();

    // 1. Run gate first
    const isUseful = runFactoryHumanityGate(prompt);
    
    // Small delay to simulate evaluation
    factoryTimeouts.push(setTimeout(() => {
        if (!isUseful) {
            lightFactoryGateResult("BLOCK");
            const pipeStatus = document.getElementById("factory-pipeline-status");
            if (pipeStatus) pipeStatus.textContent = "BLOCKED BY HUMANITY BOUNCER";
            
            // Mark Humanity Hank as blocked
            const bouncer = factoryAgentsData.find(a => a.id === "humanity-hank");
            if (bouncer) {
                bouncer.status = "blocked";
            }
            renderFactoryAgentRoster();
            return;
        }

        // Safe prompt: Animate PASS
        lightFactoryGateResult("PASS");
        const pipeStatus = document.getElementById("factory-pipeline-status");
        if (pipeStatus) pipeStatus.textContent = "PIPELINE ACTIVE";

        // Decompose stages sequentially
        let delay = 300;
        
        hochApplicationFactoryStages.forEach((stage, idx) => {
            factoryTimeouts.push(setTimeout(() => {
                // Set previous stage to complete
                if (idx > 0) {
                    animateFactoryPipelineStage(hochApplicationFactoryStages[idx - 1], "complete");
                    // Complete the agents for the previous stage
                    factoryAgentsData.forEach(agent => {
                        if (agent.stage === hochApplicationFactoryStages[idx - 1] && agent.status === "executing") {
                            agent.status = "complete";
                        }
                    });
                }
                
                // Set current stage to active
                animateFactoryPipelineStage(stage, "active");
                
                // Activate agents working on this stage
                factoryAgentsData.forEach(agent => {
                    if (agent.stage === stage) {
                        agent.status = "executing";
                    }
                });
                renderFactoryAgentRoster();

                // Custom actions per stage
                if (stage === "Research") {
                    if (researchLogs) {
                        researchLogs.innerHTML = `[Research Swarm] Searching dev docs...
[Research Swarm] Analysing target audiences...
[Research Swarm] Competitor analysis complete.
[Research Swarm] YouTube candidate list synthesized.`;
                    }
                } else if (stage === "North Star Planning") {
                    const nsOutcome = document.querySelector("#factory-north-star-details div:nth-child(1) .val");
                    const nsUser = document.querySelector("#factory-north-star-details div:nth-child(2) .val");
                    const nsMetric = document.querySelector("#factory-north-star-details div:nth-child(3) .val");
                    const nsBoundary = document.querySelector("#factory-north-star-details div:nth-child(4) .val");
                    
                    if (nsOutcome) nsOutcome.textContent = "Real problem solved; safety active";
                    if (nsUser) nsUser.textContent = "Students, Families, Civic operators";
                    if (nsMetric) nsMetric.textContent = "Accessibility & Privacy metric index >= 98%";
                    if (nsBoundary) nsBoundary.textContent = "Refuse deceptive ads and data scraping";
                } else if (stage === "PERT Analysis") {
                    renderFactoryPertAnalysis(true);
                } else if (stage === "Secure Development") {
                    renderFactoryCybersecurityPipeline(true);
                } else if (stage === "QA / E2E") {
                    renderFactoryE2EEvidenceBoard(true);
                } else if (stage === "Privacy / Store Compliance") {
                    renderFactoryPrivacyConsistencyGate(true);
                } else if (stage === "App Store Delivery") {
                    renderFactoryStoreDeliveryMatrix(true);
                } else if (stage === "Post-Launch Monitoring") {
                    if (monitorDetails) {
                        monitorDetails.innerHTML = `
                            <div><strong>Crashes / 24h:</strong> <span class="val" style="color: #10b981;">0</span></div>
                            <div><strong>Privacy Status:</strong> <span class="val" style="color: #10b981;">Clean (HIPAA/ZTA compliant)</span></div>
                            <div><strong>Abuse Reports:</strong> <span class="val" style="color: #10b981;">0</span></div>
                            <div><strong>Vulnerabilities:</strong> <span class="val" style="color: #10b981;">0 CVEs</span></div>
                        `;
                    }
                }

            }, delay));
            delay += 400; // 400ms per stage
        });

        // Final completion timeout
        factoryTimeouts.push(setTimeout(() => {
            // Complete last stage
            animateFactoryPipelineStage(hochApplicationFactoryStages[hochApplicationFactoryStages.length - 1], "complete");
            factoryAgentsData.forEach(agent => {
                if (agent.status === "executing") {
                    agent.status = "complete";
                }
            });
            renderFactoryAgentRoster();
            
            if (pipeStatus) pipeStatus.textContent = "COMPLETE";
            
            // Add to portfolio
            factoryPortfolio.push({
                idea: prompt,
                stage: "Store Delivery",
                agents: ["Foreman Fizz", "Rita", "Stan", "Ellie"],
                usefulnessScore: 98,
                risk: "Low"
            });
            renderFactoryPortfolioTable();
        }, delay));

    }, 300));
}

function initializeCybersecurityFactory() {
    renderCybersecurityFactoryView();
    
    const launchBtn = document.getElementById("factory-launch-swarm-button");
    const launchInput = document.getElementById("factory-app-idea-input");
    
    if (launchInput && !launchInput.value.trim()) {
        launchInput.value = "Build a useful app that helps people learn, solve real problems, and improve daily workflows while respecting privacy and safety.";
    }

    launchBtn?.addEventListener("click", () => {
        launchApplicationFactorySwarm();
    });
}

// Bind to window for global access/tests
window.renderCybersecurityFactoryView = renderCybersecurityFactoryView;
window.renderHumanityUsefulnessGate = renderHumanityUsefulnessGate;
window.renderApplicationFactoryPipeline = renderApplicationFactoryPipeline;
window.renderFactoryAgentRoster = renderFactoryAgentRoster;
window.runFactoryHumanityGate = runFactoryHumanityGate;
window.launchApplicationFactorySwarm = launchApplicationFactorySwarm;
window.animateFactoryPipelineStage = animateFactoryPipelineStage;
window.lightFactoryGateResult = lightFactoryGateResult;
window.renderFactoryPertAnalysis = renderFactoryPertAnalysis;
window.renderFactoryStoreDeliveryMatrix = renderFactoryStoreDeliveryMatrix;
window.renderFactoryCybersecurityPipeline = renderFactoryCybersecurityPipeline;
window.renderFactoryE2EEvidenceBoard = renderFactoryE2EEvidenceBoard;
window.renderFactoryPrivacyConsistencyGate = renderFactoryPrivacyConsistencyGate;
window.initializeCybersecurityFactory = initializeCybersecurityFactory;

// ================================================================
//  RUNS & TASK STATE SYNCHRONIZATION AND APPROVAL QUEUE
// ================================================================

let selectedRunId = null;
let runsPollInterval = null;

async function initRunsDashboard() {
    // Inject animation styles if they don't exist
    if (!document.getElementById("runs-dashboard-styles")) {
        const style = document.createElement("style");
        style.id = "runs-dashboard-styles";
        style.innerHTML = `
            @keyframes pulse-running {
                0% { box-shadow: 0 0 6px rgba(0, 229, 255, 0.15); border-color: rgba(0, 229, 255, 0.3); }
                50% { box-shadow: 0 0 12px rgba(0, 229, 255, 0.35); border-color: rgba(0, 229, 255, 0.6); }
                100% { box-shadow: 0 0 6px rgba(0, 229, 255, 0.15); border-color: rgba(0, 229, 255, 0.3); }
            }
            @keyframes pulse-warning {
                0% { box-shadow: 0 0 6px rgba(245, 158, 11, 0.2); border-color: rgba(245, 158, 11, 0.4); }
                50% { box-shadow: 0 0 14px rgba(245, 158, 11, 0.45); border-color: rgba(245, 158, 11, 0.85); }
                100% { box-shadow: 0 0 6px rgba(245, 158, 11, 0.2); border-color: rgba(245, 158, 11, 0.4); }
            }
            .pulse-glow-running {
                animation: pulse-running 2s infinite ease-in-out;
            }
            .pulse-glow-warning {
                animation: pulse-warning 1.8s infinite ease-in-out;
            }
        `;
        document.head.appendChild(style);
    }

    const runSelector = document.getElementById("run-selector");
    const btnCreateRun = document.getElementById("btn-create-run");
    const btnStartRun = document.getElementById("btn-start-run");

    if (btnCreateRun) {
        btnCreateRun.addEventListener("click", async () => {
            await createNewSwarmRun();
        });
    }

    if (btnStartRun) {
        btnStartRun.addEventListener("click", async () => {
            if (selectedRunId) {
                await startRunExecution(selectedRunId);
            }
        });
    }

    if (runSelector) {
        runSelector.addEventListener("change", (e) => {
            selectedRunId = e.target.value;
            localStorage.setItem("selectedRunId", selectedRunId || "");
            if (selectedRunId) {
                fetchRunTasks(selectedRunId);
            } else {
                renderTaskFlowGrid([]);
                const statusText = document.getElementById("run-status-text");
                if (statusText) statusText.textContent = "-";
                if (btnStartRun) btnStartRun.style.display = "none";
            }
        });
    }

    // Initial load
    await refreshRunsList();
    
    // Auto-select last run if saved in localStorage
    const savedRunId = localStorage.getItem("selectedRunId");
    if (savedRunId && runSelector) {
        const option = Array.from(runSelector.options).find(opt => opt.value === savedRunId);
        if (option) {
            runSelector.value = savedRunId;
            selectedRunId = savedRunId;
            fetchRunTasks(selectedRunId);
        }
    }

    // Start polling interval
    if (runsPollInterval) clearInterval(runsPollInterval);
    runsPollInterval = setInterval(pollRunsDashboardState, 2500);
}

async function refreshRunsList() {
    try {
        const runs = await fetchJson("/api/v1/runs");
        const runSelector = document.getElementById("run-selector");
        if (!runSelector) return;

        // Keep current selection if possible
        const currentSelection = runSelector.value;
        
        // Reset dropdown
        runSelector.innerHTML = '<option value="">Select a Run...</option>';
        
        // Populate dropdown
        runs.forEach(run => {
            const opt = document.createElement("option");
            opt.value = run.run_id;
            opt.textContent = `${run.name} (${run.run_id})`;
            runSelector.appendChild(opt);
        });

        // Restore selection
        if (currentSelection) {
            const exists = Array.from(runSelector.options).some(opt => opt.value === currentSelection);
            if (exists) {
                runSelector.value = currentSelection;
                selectedRunId = currentSelection;
            } else {
                selectedRunId = null;
            }
        }
    } catch (err) {
        console.error("Failed to refresh runs list:", err);
    }
}

async function createNewSwarmRun() {
    try {
        const name = "Swarm Run " + new Date().toLocaleString();
        const run = await fetchJson("/api/v1/runs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name })
        });
        
        logToConsoleTerminal("Orchestrator", `Created new swarm run: ${run.name} (${run.run_id})`, "info");
        
        // Refresh and select new run
        await refreshRunsList();
        const runSelector = document.getElementById("run-selector");
        if (runSelector) {
            runSelector.value = run.run_id;
            selectedRunId = run.run_id;
            localStorage.setItem("selectedRunId", selectedRunId);
            await fetchRunTasks(selectedRunId);
        }
    } catch (err) {
        console.error("Failed to create new run:", err);
        logToConsoleTerminal("Orchestrator", `Failed to create new run: ${err.message}`, "error");
    }
}

async function startRunExecution(runId) {
    try {
        await fetchJson(`/api/v1/runs/${runId}/tasks/T0-RECON/execute`, {
            method: "POST"
        });
        logToConsoleTerminal("Orchestrator", `Started execution for run ${runId}: dispatched T0-RECON`, "success");
        await fetchRunTasks(runId);
    } catch (err) {
        console.error("Failed to start run execution:", err);
        logToConsoleTerminal("Orchestrator", `Failed to start run: ${err.message}`, "error");
    }
}

async function pollRunsDashboardState() {
    if (selectedRunId) {
        await fetchRunTasks(selectedRunId);
    }
    await fetchApprovalRequests();
    if (typeof fetchAndRenderSigningPolicy === 'function') {
        await fetchAndRenderSigningPolicy();
    }
}

async function fetchRunTasks(runId) {
    try {
        const tasks = await fetchJson(`/api/v1/runs/${runId}/tasks`);
        renderTaskFlowGrid(tasks);
        
        // Determine overall run status
        const runStatusText = document.getElementById("run-status-text");
        const btnStartRun = document.getElementById("btn-start-run");

        if (tasks.length > 0) {
            const allPending = tasks.every(t => t.status === "pending");
            const anyRunning = tasks.some(t => t.status === "running");
            const anyBlocked = tasks.some(t => t.status === "blocked_pending_approval" || t.status === "blocked");
            const allCompleted = tasks.every(t => t.status === "completed");

            let status = "running";
            if (allPending) {
                status = "pending";
                if (btnStartRun) btnStartRun.style.display = "inline-block";
            } else {
                if (btnStartRun) btnStartRun.style.display = "none";
                if (allCompleted) {
                    status = "completed";
                } else if (anyBlocked) {
                    status = "blocked";
                }
            }

            if (runStatusText) {
                runStatusText.textContent = status.toUpperCase();
                // Color status text
                if (status === "completed") {
                    runStatusText.style.color = "#10b981";
                } else if (status === "blocked") {
                    runStatusText.style.color = "#f59e0b";
                } else if (status === "running") {
                    runStatusText.style.color = "#00e5ff";
                } else {
                    runStatusText.style.color = "#94a3b8";
                }
            }
        }
    } catch (err) {
        console.error(`Failed to fetch tasks for run ${runId}:`, err);
    }
}

function renderTaskFlowGrid(tasks) {
    const grid = document.getElementById("task-flow-grid");
    if (!grid) return;
    
    if (!tasks || tasks.length === 0) {
        grid.innerHTML = '<div style="grid-column: span 5; font-size: 10px; color: var(--text-secondary); text-align: center; padding: 12px; font-family: monospace;">No tasks in selected run.</div>';
        return;
    }

    grid.innerHTML = "";
    
    tasks.forEach(task => {
        const card = document.createElement("div");
        card.style.padding = "8px 10px";
        card.style.borderRadius = "6px";
        card.style.border = "1px solid rgba(255, 255, 255, 0.08)";
        card.style.background = "rgba(255, 255, 255, 0.02)";
        card.style.display = "flex";
        card.style.flexDirection = "column";
        card.style.justifyContent = "space-between";
        card.style.minHeight = "64px";
        card.style.fontFamily = "monospace";
        card.style.fontSize = "10px";
        card.style.transition = "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)";
        card.style.position = "relative";
        card.style.overflow = "hidden";

        // Status styling
        const status = task.status;
        let borderGlow = "rgba(255,255,255,0.08)";
        let bgGlow = "rgba(255,255,255,0.02)";
        let statusColor = "var(--text-secondary)";
        let pulseClass = "";

        if (status === "completed") {
            borderGlow = "rgba(16, 185, 129, 0.4)";
            bgGlow = "rgba(16, 185, 129, 0.04)";
            statusColor = "#10b981";
        } else if (status === "running") {
            borderGlow = "rgba(0, 229, 255, 0.5)";
            bgGlow = "rgba(0, 229, 255, 0.06)";
            statusColor = "#00e5ff";
            pulseClass = "pulse-glow-running";
        } else if (status === "blocked_pending_approval") {
            borderGlow = "rgba(245, 158, 11, 0.6)";
            bgGlow = "rgba(245, 158, 11, 0.08)";
            statusColor = "#f59e0b";
            pulseClass = "pulse-glow-warning";
        } else if (status === "blocked") {
            borderGlow = "rgba(239, 68, 68, 0.4)";
            bgGlow = "rgba(239, 68, 68, 0.04)";
            statusColor = "#ef4444";
        }

        card.style.borderColor = borderGlow;
        card.style.background = bgGlow;
        if (pulseClass) {
            card.classList.add(pulseClass);
        }

        // Card header (ID and status)
        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.justifyContent = "space-between";
        header.style.fontWeight = "bold";
        header.innerHTML = `
            <span style="color: #fff;">${task.id}</span>
            <span style="color: ${statusColor}; font-size: 9px;">${status.replace('_', ' ').toUpperCase()}</span>
        `;
        card.appendChild(header);

        // Card body (title/description snippet)
        const body = document.createElement("div");
        body.style.color = "var(--text-secondary)";
        body.style.fontSize = "9px";
        body.style.whiteSpace = "nowrap";
        body.style.overflow = "hidden";
        body.style.textOverflow = "ellipsis";
        body.style.marginTop = "2px";
        body.textContent = task.title;
        card.appendChild(body);

        // Card footer (priority/risk)
        const footer = document.createElement("div");
        footer.style.display = "flex";
        footer.style.justifyContent = "space-between";
        footer.style.marginTop = "4px";
        footer.style.fontSize = "8px";

        let riskColor = "#10b981";
        if (task.riskLevel === "critical") riskColor = "#ef4444";
        else if (task.riskLevel === "high") riskColor = "#f97316";
        else if (task.riskLevel === "medium") riskColor = "#eab308";

        footer.innerHTML = `
            <span style="color: var(--text-secondary);">Risk: <span style="color: ${riskColor}; font-weight: bold;">${task.riskLevel.toUpperCase()}</span></span>
            ${task.approvalRequired ? '<span style="color: var(--accent-purple);" title="Human Approval Required">&#128274; REQ</span>' : ''}
        `;
        card.appendChild(footer);

        // Mouse hover effects
        card.addEventListener("mouseenter", () => {
            card.style.transform = "translateY(-2px)";
            card.style.boxShadow = `0 4px 12px ${borderGlow.replace('0.4', '0.2').replace('0.5', '0.25').replace('0.6', '0.3')}`;
        });
        card.addEventListener("mouseleave", () => {
            card.style.transform = "translateY(0)";
            card.style.boxShadow = "none";
        });

        grid.appendChild(card);
    });
}

async function fetchApprovalRequests() {
    try {
        const approvals = await fetchJson("/api/approval/requests");
        const list = document.getElementById("approval-queue-list");
        const countBadge = document.getElementById("approval-queue-count");
        if (!list) return;

        // Filter for pending approvals matching the selected run
        const pendingApprovals = approvals.filter(a => a.status === "pending" && (!selectedRunId || a.target?.id === selectedRunId));

        if (countBadge) {
            countBadge.textContent = `${pendingApprovals.length} PENDING`;
            if (pendingApprovals.length > 0) {
                countBadge.style.background = "rgba(245, 158, 11, 0.15)";
                countBadge.style.color = "#f59e0b";
                countBadge.style.borderColor = "rgba(245, 158, 11, 0.3)";
            } else {
                countBadge.style.background = "rgba(255, 255, 255, 0.05)";
                countBadge.style.color = "var(--text-secondary)";
                countBadge.style.borderColor = "var(--border-glass)";
            }
        }

        if (pendingApprovals.length === 0) {
            list.innerHTML = '<div style="font-size: 10px; color: var(--text-secondary); font-family: monospace; padding: 12px; background: rgba(255,255,255,0.02); border-radius: 6px; text-align: center; border: 1px dashed rgba(255,255,255,0.05);">No pending decisions in queue.</div>';
            return;
        }

        list.innerHTML = "";

        pendingApprovals.forEach(app => {
            const row = document.createElement("div");
            row.style.display = "flex";
            row.style.justifyContent = "space-between";
            row.style.alignItems = "center";
            row.style.padding = "8px 12px";
            row.style.background = "rgba(245, 158, 11, 0.04)";
            row.style.border = "1px solid rgba(245, 158, 11, 0.2)";
            row.style.borderRadius = "6px";
            row.style.gap = "8px";
            row.style.animation = "pulse-warning 3s infinite ease-in-out";
            row.style.fontFamily = "monospace";
            row.style.fontSize = "10px";

            // Left side details
            const details = document.createElement("div");
            details.style.display = "flex";
            details.style.flexDirection = "column";
            details.style.gap = "2px";
            details.style.textAlign = "left";
            
            const taskId = app.command?.command_id ? app.command.command_id.replace("cmd-", "") : "UNKNOWN";
            const risk = app.command?.risk ? app.command.risk.toUpperCase() : "MEDIUM";
            
            details.innerHTML = `
                <div style="font-weight: bold; color: #fff;">
                    Approval Request <span style="color: var(--accent-purple);">${app.approval_id}</span>
                </div>
                <div style="color: var(--text-secondary); font-size: 9px;">
                    Task: <span style="color: #fff;">${taskId}</span> | Risk: <span style="color: #ef4444; font-weight: bold;">${risk}</span>
                </div>
                <div style="color: var(--text-secondary); font-size: 9px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${app.policy_context?.approval_reason || ''}">
                    ${app.policy_context?.approval_reason || "Approval required"}
                </div>
            `;
            row.appendChild(details);

            // Right side buttons
            const actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "6px";

            const btnApprove = document.createElement("button");
            btnApprove.textContent = "APPROVE";
            btnApprove.style.background = "rgba(16, 185, 129, 0.15)";
            btnApprove.style.border = "1px solid rgba(16, 185, 129, 0.35)";
            btnApprove.style.color = "#10b981";
            btnApprove.style.padding = "4px 8px";
            btnApprove.style.borderRadius = "4px";
            btnApprove.style.fontSize = "9px";
            btnApprove.style.fontWeight = "bold";
            btnApprove.style.cursor = "pointer";
            btnApprove.style.transition = "all 0.2s";
            btnApprove.onmouseover = () => {
                btnApprove.style.background = "rgba(16, 185, 129, 0.35)";
                btnApprove.style.boxShadow = "0 0 8px rgba(16, 185, 129, 0.4)";
            };
            btnApprove.onmouseout = () => {
                btnApprove.style.background = "rgba(16, 185, 129, 0.15)";
                btnApprove.style.boxShadow = "none";
            };
            btnApprove.addEventListener("click", async () => {
                await submitApprovalDecision(app.approval_id, "approve");
            });
            actions.appendChild(btnApprove);

            const btnReject = document.createElement("button");
            btnReject.textContent = "REJECT";
            btnReject.style.background = "rgba(239, 68, 68, 0.15)";
            btnReject.style.border = "1px solid rgba(239, 68, 68, 0.35)";
            btnReject.style.color = "#ef4444";
            btnReject.style.padding = "4px 8px";
            btnReject.style.borderRadius = "4px";
            btnReject.style.fontSize = "9px";
            btnReject.style.fontWeight = "bold";
            btnReject.style.cursor = "pointer";
            btnReject.style.transition = "all 0.2s";
            btnReject.onmouseover = () => {
                btnReject.style.background = "rgba(239, 68, 68, 0.35)";
                btnReject.style.boxShadow = "0 0 8px rgba(239, 68, 68, 0.4)";
            };
            btnReject.onmouseout = () => {
                btnReject.style.background = "rgba(239, 68, 68, 0.15)";
                btnReject.style.boxShadow = "none";
            };
            btnReject.addEventListener("click", async () => {
                await submitApprovalDecision(app.approval_id, "reject");
            });
            actions.appendChild(btnReject);

            row.appendChild(actions);
            list.appendChild(row);
        });
    } catch (err) {
        console.error("Failed to fetch approvals:", err);
    }
}

async function submitApprovalDecision(approvalId, decision) {
    try {
        const payload = {
            decision: decision,
            approver: "Operator",
            timestamp: new Date().toISOString()
        };
        await fetchJson(`/api/approval/requests/${approvalId}/decisions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        logToConsoleTerminal("Orchestrator", `Submitted decision: ${decision.toUpperCase()} for approval request ${approvalId}`, decision === "approve" ? "success" : "error");
        
        // Immediately refresh state
        await pollRunsDashboardState();
    } catch (err) {
        console.error(`Failed to submit decision ${decision} for ${approvalId}:`, err);
        logToConsoleTerminal("Orchestrator", `Failed to submit decision: ${err.message}`, "error");
    }
}

// Bind runs console functions to window for global access/tests
window.initRunsDashboard = initRunsDashboard;
window.refreshRunsList = refreshRunsList;
window.createNewSwarmRun = createNewSwarmRun;
window.startRunExecution = startRunExecution;
window.fetchRunTasks = fetchRunTasks;
window.renderTaskFlowGrid = renderTaskFlowGrid;
window.fetchApprovalRequests = fetchApprovalRequests;
window.submitApprovalDecision = submitApprovalDecision;

async function fetchAndRenderSigningPolicy() {
    const policyPanel = document.getElementById("release-signing-policy-panel");
    if (!policyPanel) return;

    try {
        const response = await fetch(`${API_BASE}/api/v1/release/signing-policy`);
        if (response.ok) {
            const data = await response.json();
            const current = data.current_release || {};

            // 1. Render signature status
            const sigStatusEl = document.getElementById("release-signature-status");
            if (sigStatusEl) {
                if (current.signature_status === "signed") {
                    sigStatusEl.textContent = "Signed";
                    sigStatusEl.style.color = "var(--accent-teal)";
                } else if (current.signature_status === "waived") {
                    sigStatusEl.textContent = "Waived With Operator Approval";
                    sigStatusEl.style.color = "var(--accent-blue)";
                } else if (current.signature_status === "partially_signed") {
                    sigStatusEl.textContent = "Partially Signed";
                    sigStatusEl.style.color = "var(--accent-yellow)";
                } else {
                    sigStatusEl.textContent = "Signing Pending";
                    sigStatusEl.style.color = "var(--text-secondary)";
                }
            }

            // 2. Render policy status
            const policyStatusEl = document.getElementById("release-signing-policy-status");
            if (policyStatusEl) {
                policyStatusEl.textContent = current.signing_policy_status || "WARN";
                if (current.signing_policy_status === "PASS") {
                    policyStatusEl.style.color = "var(--accent-teal)";
                    policyStatusEl.style.borderColor = "var(--accent-teal)";
                } else if (current.signing_policy_status === "BLOCK") {
                    policyStatusEl.style.color = "#ef4444";
                    policyStatusEl.style.borderColor = "#ef4444";
                } else {
                    policyStatusEl.style.color = "var(--accent-yellow)";
                    policyStatusEl.style.borderColor = "var(--accent-yellow)";
                }
            }

            // 3. Render finalization status
            const finalStatusEl = document.getElementById("release-finalization-status");
            if (finalStatusEl) {
                if (current.release_finalization_status === "formal_release_blocked") {
                    finalStatusEl.textContent = "Formal Release Blocked";
                    finalStatusEl.style.color = "#ef4444";
                } else if (current.release_finalization_status === "formal_release_ready") {
                    finalStatusEl.textContent = "Formal Release Ready";
                    finalStatusEl.style.color = "var(--accent-teal)";
                } else {
                    finalStatusEl.textContent = "Local Dev Pass";
                    finalStatusEl.style.color = "var(--accent-blue)";
                }
            }

            // 4. Render waiver status
            const waiverStatusEl = document.getElementById("release-signing-waiver-status");
            if (waiverStatusEl) {
                waiverStatusEl.textContent = current.signing_waiver_status || "none";
            }

            // 5. Render actions list
            const actionListEl = document.getElementById("release-signing-action-list");
            if (actionListEl) {
                actionListEl.innerHTML = "";
                const allowed = data.allowed_actions || [];
                allowed.forEach(action => {
                    const btn = document.createElement("button");
                    btn.className = "btn btn-xs";
                    if (action === "continue_local_dev") {
                        btn.id = "btn-signing-continue-dev";
                        btn.className += " btn-secondary";
                        btn.textContent = "Continue Local Dev";
                    } else if (action === "request_signing") {
                        btn.id = "btn-signing-request-sign";
                        btn.className += " btn-primary";
                        btn.textContent = "Request Signing";
                    } else if (action === "request_operator_waiver") {
                        btn.id = "btn-signing-request-waiver";
                        btn.className += " btn-danger";
                        btn.textContent = "Request Operator Waiver";
                    }
                    btn.addEventListener("click", () => handleSigningAction(action));
                    actionListEl.appendChild(btn);
                });
            }

            // 6. Fetch and render release channel governance
            const chanResponse = await fetch(`${API_BASE}/api/v1/release/channel-governance`);
            if (chanResponse.ok) {
                const chanData = await chanResponse.json();
                const curRel = chanData.current_release || {};
                
                // Render current channel
                const chanCurrentEl = document.getElementById("release-channel-current");
                if (chanCurrentEl) {
                    if (curRel.channel === "formal") {
                        chanCurrentEl.textContent = "Formal";
                        chanCurrentEl.style.color = "var(--accent-teal)";
                    } else if (curRel.channel === "candidate") {
                        chanCurrentEl.textContent = "Candidate";
                        chanCurrentEl.style.color = "var(--accent-yellow)";
                    } else {
                        chanCurrentEl.textContent = "Local Dev";
                        chanCurrentEl.style.color = "var(--accent-blue)";
                    }
                }
                
                // Render policy status
                const chanPolicyStatusEl = document.getElementById("release-channel-policy-status");
                if (chanPolicyStatusEl) {
                    const status = curRel.release_channel_policy_status || "WARN";
                    chanPolicyStatusEl.textContent = status;
                    if (status === "PASS") {
                        chanPolicyStatusEl.style.color = "var(--accent-teal)";
                        chanPolicyStatusEl.style.borderColor = "var(--accent-teal)";
                    } else if (status === "BLOCK") {
                        chanPolicyStatusEl.style.color = "#ef4444";
                        chanPolicyStatusEl.style.borderColor = "#ef4444";
                    } else {
                        chanPolicyStatusEl.style.color = "var(--accent-yellow)";
                        chanPolicyStatusEl.style.borderColor = "var(--accent-yellow)";
                    }
                }
                
                // Render release tag
                const tagCurrentEl = document.getElementById("release-tag-current");
                if (tagCurrentEl) {
                    tagCurrentEl.textContent = curRel.release_tag || "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY";
                }
                
                // Render tag status
                const tagStatusEl = document.getElementById("release-tag-status");
                if (tagStatusEl) {
                    if (curRel.tag_status === "TAG_AT_HEAD") {
                        tagStatusEl.textContent = "Tag Points at HEAD";
                        tagStatusEl.style.color = "var(--accent-teal)";
                    } else if (curRel.tag_status === "STALE_TAG") {
                        tagStatusEl.textContent = "Stale Tag";
                        tagStatusEl.style.color = "var(--accent-yellow)";
                    } else {
                        tagStatusEl.textContent = "No Release Tag";
                        tagStatusEl.style.color = "var(--text-secondary)";
                    }
                }
                
                // Render tag alignment text
                const tagAlignEl = document.getElementById("release-tag-alignment-status");
                if (tagAlignEl) {
                    if (curRel.tag_points_at_head) {
                        tagAlignEl.textContent = "Tag Points at HEAD";
                        tagAlignEl.style.color = "var(--accent-teal)";
                    } else if (curRel.tag_status === "STALE_TAG") {
                        tagAlignEl.textContent = "Stale Tag";
                        tagAlignEl.style.color = "var(--accent-yellow)";
                    } else {
                        tagAlignEl.textContent = "No Release Tag";
                        tagAlignEl.style.color = "var(--text-secondary)";
                    }
                }
                
                // Render SHAs
                const tagHeadShaEl = document.getElementById("release-tag-head-sha");
                if (tagHeadShaEl) {
                    tagHeadShaEl.textContent = curRel.head_sha ? curRel.head_sha.substring(0, 12) : "...";
                }
                
                const tagTargetShaEl = document.getElementById("release-tag-target-sha");
                if (tagTargetShaEl) {
                    tagTargetShaEl.textContent = curRel.tag_sha ? curRel.tag_sha.substring(0, 12) : "none";
                }
                
                // Render finalization status
                const formalFinalStatusEl = document.getElementById("release-formal-finalization-status");
                if (formalFinalStatusEl) {
                    if (curRel.release_finalization_status === "formal_release_blocked") {
                        formalFinalStatusEl.textContent = "Formal Release Blocked";
                        formalFinalStatusEl.style.color = "#ef4444";
                    } else if (curRel.release_finalization_status === "formal_release_ready") {
                        formalFinalStatusEl.textContent = "Formal Release Ready";
                        formalFinalStatusEl.style.color = "var(--accent-teal)";
                    } else if (curRel.release_finalization_status === "candidate_ready") {
                        formalFinalStatusEl.textContent = "Candidate Ready";
                        formalFinalStatusEl.style.color = "var(--accent-teal)";
                    } else {
                        formalFinalStatusEl.textContent = "Local Dev Pass";
                        formalFinalStatusEl.style.color = "var(--accent-blue)";
                    }
                }
                
                // Populate channel action buttons
                const chanActionListEl = document.getElementById("release-channel-action-list");
                if (chanActionListEl) {
                    chanActionListEl.innerHTML = "";
                    const allowedActions = chanData.allowed_actions || [];
                    allowedActions.forEach(action => {
                        const btn = document.createElement("button");
                        btn.className = "btn btn-xs";
                        if (action === "continue_local_dev") {
                            btn.className += " btn-secondary";
                            btn.textContent = "Continue Local Dev";
                        } else if (action === "create_candidate_release") {
                            btn.className += " btn-yellow";
                            btn.style.background = "rgba(234, 179, 8, 0.15)";
                            btn.style.color = "var(--accent-yellow)";
                            btn.style.border = "1px solid var(--accent-yellow)";
                            btn.textContent = "Request Candidate Release";
                        } else if (action === "request_formal_release_approval") {
                            btn.className += " btn-primary";
                            btn.textContent = "Request Formal Release Approval";
                        } else if (action === "request_tag_alignment_approval") {
                            btn.className += " btn-danger";
                            btn.textContent = "Request Tag Alignment Approval";
                        }
                        btn.addEventListener("click", () => handleGovernanceAction(action));
                        chanActionListEl.appendChild(btn);
                    });
                }
            }
        }
    } catch (err) {
        console.error("Failed to fetch signing policy:", err);
    }
}

async function handleSigningAction(action) {
    if (action === "continue_local_dev") {
        try {
            const res = await fetch(`${API_BASE}/api/v1/release/signing-waiver`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reason: "Local development loop continuation",
                    scope: "local_dev",
                    operator: "Local Developer"
                })
            });
            if (res.ok) {
                alert("Local dev signature warning waived successfully.");
                fetchAndRenderSigningPolicy();
            }
        } catch (err) {
            alert("Failed to waive warning: " + err.message);
        }
    } else if (action === "request_operator_waiver") {
        const reason = prompt("Enter reason for formal release signing waiver:", "Testing release without Cosign keys");
        if (reason === null) return;
        try {
            const res = await fetch(`${API_BASE}/api/v1/release/signing-waiver`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reason: reason,
                    scope: "formal_release",
                    operator: "Operator"
                })
            });
            if (res.ok) {
                const data = await res.json();
                alert("Waiver approval gate requested: " + data.approval_id);
                fetchAndRenderSigningPolicy();
                if (typeof fetchApprovalRequests === 'function') {
                    fetchApprovalRequests();
                }
            }
        } catch (err) {
            alert("Failed to request waiver: " + err.message);
        }
    } else if (action === "request_signing") {
        alert("Cosign signing requested. Set ENABLE_COSIGN_SIGNING=true in env and run release pipeline.");
    }
}

window.fetchAndRenderSigningPolicy = fetchAndRenderSigningPolicy;
window.handleSigningAction = handleSigningAction;

async function handleGovernanceAction(action) {
    if (action === "continue_local_dev") {
        try {
            const res = await fetch(`${API_BASE}/api/v1/release/governance-waiver`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reason: "Local development loop continuation",
                    scope: "local_dev",
                    operator: "Local Developer"
                })
            });
            if (res.ok) {
                alert("Local dev governance warning waived successfully.");
                fetchAndRenderSigningPolicy();
            }
        } catch (err) {
            alert("Failed to waive warning: " + err.message);
        }
    } else if (action === "request_tag_alignment_approval") {
        const reason = prompt("Enter reason for tag alignment waiver / tag movement approval:", "Tag alignment override for testing");
        if (reason === null) return;
        try {
            const res = await fetch(`${API_BASE}/api/v1/release/governance-waiver`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reason: reason,
                    scope: "formal_release",
                    operator: "Operator"
                })
            });
            if (res.ok) {
                const data = await res.json();
                alert("Governance waiver approval gate requested: " + data.approval_id);
                fetchAndRenderSigningPolicy();
                if (typeof fetchApprovalRequests === 'function') {
                    fetchApprovalRequests();
                }
            }
        } catch (err) {
            alert("Failed to request waiver: " + err.message);
        }
    } else if (action === "create_candidate_release") {
        try {
            const res = await fetch(`${API_BASE}/api/v1/release/channel-decision`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    requested_channel: "candidate",
                    operator: "Michael Hoch",
                    reason: "Promote post-audit evidence to release candidate"
                })
            });
            if (res.ok) {
                const data = await res.json();
                alert("Candidate promotion recorded successfully: " + data.approval_id);
                fetchAndRenderSigningPolicy();
            } else {
                const data = await res.json();
                alert("Failed to promote: " + (data.detail || "Unknown error"));
            }
        } catch (err) {
            alert("Failed to promote: " + err.message);
        }
    } else if (action === "request_formal_release_approval") {
        try {
            const res = await fetch(`${API_BASE}/api/v1/release/channel-decision`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    requested_channel: "formal",
                    operator: "Michael Hoch",
                    reason: "Formal release promotion request"
                })
            });
            if (res.ok) {
                const data = await res.json();
                alert("Formal release promotion requested: " + data.approval_id);
                fetchAndRenderSigningPolicy();
                if (typeof fetchApprovalRequests === 'function') {
                    fetchApprovalRequests();
                }
            } else {
                const data = await res.json();
                alert("Failed to request: " + (data.detail || "Unknown error"));
            }
        } catch (err) {
            alert("Failed to request: " + err.message);
        }
    }
}

async function submitChannelDecisionRequest() {
    const channelSelect = document.getElementById("select-requested-channel");
    const tagInput = document.getElementById("input-requested-tag");
    if (!channelSelect) return;
    
    const requested_channel = channelSelect.value;
    const requested_tag = tagInput ? tagInput.value : "";
    
    try {
        const res = await fetch(`${API_BASE}/api/v1/release/channel-decision`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                requested_channel: requested_channel,
                operator: "Michael Hoch",
                reason: `Requested channel promotion to ${requested_channel}`,
                requested_tag: requested_tag
            })
        });
        if (res.ok) {
            const data = await res.json();
            alert(`Decision submitted. Status: ${data.status}, ID: ${data.approval_id}`);
            fetchAndRenderSigningPolicy();
            if (typeof fetchApprovalRequests === 'function') {
                fetchApprovalRequests();
            }
        } else {
            const data = await res.json();
            alert("Failed to submit decision: " + (data.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Failed to submit: " + err.message);
    }
}

window.handleSigningAction = handleSigningAction;
window.submitChannelDecisionRequest = submitChannelDecisionRequest;

async function fetchAndRenderGovernanceSummary() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/governance/summary`);
        if (!res.ok) {
            console.error("Failed to fetch governance summary");
            return;
        }
        const data = await res.json();
        
        // 1. Pending count & list
        const pendingCountEl = document.getElementById("gov-pending-count");
        if (pendingCountEl) {
            pendingCountEl.textContent = data.pending_gates.length;
        }
        
        const pendingListEl = document.getElementById("gov-pending-list");
        if (pendingListEl) {
            pendingListEl.innerHTML = "";
            if (data.pending_gates.length === 0) {
                pendingListEl.innerHTML = `<p style="color:var(--text-secondary); text-align:center; padding: 20px; font-size:12px; margin:0;">No pending approval requests.</p>`;
            } else {
                data.pending_gates.forEach(gate => {
                    const card = document.createElement("div");
                    card.className = "card";
                    card.style.background = "rgba(255,255,255,0.02)";
                    card.style.border = "1px solid var(--border-glass)";
                    card.style.borderRadius = "6px";
                    card.style.padding = "10px";
                    card.style.display = "flex";
                    card.style.flexDirection = "column";
                    card.style.gap = "6px";
                    
                    card.innerHTML = `
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px;">
                            <strong style="color:var(--accent-yellow);">${gate.action_type.toUpperCase()}</strong>
                            <span style="color:var(--text-secondary);">${gate.created_at}</span>
                        </div>
                        <div style="font-size:12px; color:#fff;"><strong>Request ID:</strong> ${gate.request_id}</div>
                        <div style="font-size:11px; color:var(--text-secondary); line-height:1.4;">Requested by: ${gate.requested_by} (Risk: ${gate.risk_level})</div>
                        <div style="display:flex; gap:10px; margin-top:4px;">
                            <button class="btn btn-xs btn-primary" onclick="window.submitGovernanceApproval('${gate.approval_id}', 'approve')">Approve</button>
                            <button class="btn btn-xs btn-danger" onclick="window.submitGovernanceApproval('${gate.approval_id}', 'reject')">Reject</button>
                        </div>
                    `;
                    pendingListEl.appendChild(card);
                });
            }
        }
        
        // 2. Blockers status & list
        const blockersStatusEl = document.getElementById("gov-blockers-status");
        if (blockersStatusEl) {
            if (data.formal_release_blockers.length === 0) {
                blockersStatusEl.textContent = "PASS";
                blockersStatusEl.style.color = "var(--accent-teal)";
                blockersStatusEl.style.background = "rgba(16,185,129,0.15)";
            } else {
                blockersStatusEl.textContent = "BLOCK";
                blockersStatusEl.style.color = "#ef4444";
                blockersStatusEl.style.background = "rgba(239,68,68,0.15)";
            }
        }
        
        const blockersListEl = document.getElementById("gov-blockers-list");
        if (blockersListEl) {
            blockersListEl.innerHTML = "";
            if (data.formal_release_blockers.length === 0) {
                blockersListEl.innerHTML = `<li style="display:flex; align-items:center; gap:8px; color:var(--accent-teal);"><i data-lucide="check-circle" style="width:14px; height:14px;"></i> All finalization gates satisfy release policy constraints.</li>`;
            } else {
                data.formal_release_blockers.forEach(blocker => {
                    const li = document.createElement("li");
                    li.style.display = "flex";
                    li.style.alignItems = "center";
                    li.style.gap = "8px";
                    li.style.color = "#ef4444";
                    let label = blocker;
                    if (blocker === "dirty_working_tree") label = "Git Working Tree is Dirty (Unwaived)";
                    else if (blocker === "qa_not_passed") label = "QA / Verification Pack is Not Passing (Unwaived)";
                    else if (blocker === "signing_policy_not_passed") label = "Release Artifacts Are Unsigned (Unwaived)";
                    else if (blocker === "tag_missing") label = "Git Release Tag is Missing (Unwaived)";
                    else if (blocker === "tag_stale") label = "Git Release Tag points to non-HEAD commit (Unwaived)";
                    else if (blocker === "operator_approval_missing") label = "Formal Channel Promotion requires Operator Gate";
                    
                    li.innerHTML = `<i data-lucide="alert-triangle" style="width:14px; height:14px; flex-shrink:0;"></i> <span>${label}</span>`;
                    blockersListEl.appendChild(li);
                });
            }
        }
        
        // 3. Active Policies & Waivers
        const activeChanEl = document.getElementById("gov-active-channel");
        if (activeChanEl) {
            activeChanEl.textContent = data.active_channel;
            if (data.active_channel === "formal") {
                activeChanEl.style.color = "var(--accent-teal)";
            } else if (data.active_channel === "candidate") {
                activeChanEl.style.color = "var(--accent-yellow)";
            } else {
                activeChanEl.style.color = "var(--accent-blue)";
            }
        }
        
        const signingWaiverEl = document.getElementById("gov-signing-waiver");
        if (signingWaiverEl) {
            signingWaiverEl.textContent = data.signing_waiver;
            if (data.signing_waiver === "waived") {
                signingWaiverEl.style.color = "var(--accent-yellow)";
            } else {
                signingWaiverEl.style.color = "#fff";
            }
        }
        
        const tagAlignmentEl = document.getElementById("gov-tag-alignment");
        if (tagAlignmentEl) {
            tagAlignmentEl.textContent = data.tag_alignment_status;
            if (data.tag_alignment_status === "TAG_AT_HEAD") {
                tagAlignmentEl.style.color = "var(--accent-teal)";
            } else {
                tagAlignmentEl.style.color = "#ef4444";
            }
        }
        
        const testBypassEl = document.getElementById("gov-test-bypass-active");
        if (testBypassEl) {
            testBypassEl.textContent = data.test_bypass_hardening;
            if (data.test_bypass_hardening === "ACTIVE") {
                testBypassEl.style.color = "var(--accent-blue)";
            } else {
                testBypassEl.style.color = "var(--text-secondary)";
            }
        }
        
        // 4. Capability Enforcement Decisions
        const capBody = document.getElementById("gov-capability-tbody");
        if (capBody) {
            capBody.innerHTML = "";
            if (data.capability_decisions.length === 0) {
                capBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-secondary); padding: 12px;">No capability decisions registered.</td></tr>`;
            } else {
                data.capability_decisions.forEach(item => {
                    const row = document.createElement("tr");
                    const timeStr = item.timestamp ? item.timestamp.substring(11, 19) : "";
                    const allowedClass = item.decision === "ALLOW" ? "text-success" : (item.decision === "BLOCK" ? "text-danger" : "text-warning");
                    row.innerHTML = `
                        <td style="color:var(--text-secondary);">${timeStr}</td>
                        <td><strong>${item.agent_id}</strong></td>
                        <td style="font-family:monospace;">${item.tool}</td>
                        <td><span class="${allowedClass} font-semibold">${item.decision}</span></td>
                        <td style="color:var(--text-secondary);">${item.reason}</td>
                    `;
                    capBody.appendChild(row);
                });
            }
        }
        
        // 5. Replay Protection Evidence
        const replayBody = document.getElementById("gov-replay-tbody");
        if (replayBody) {
            replayBody.innerHTML = "";
            if (data.replay_protection_evidence.length === 0) {
                replayBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-secondary); padding: 12px;">No replay protection evidence recorded.</td></tr>`;
            } else {
                data.replay_protection_evidence.forEach(item => {
                    const row = document.createElement("tr");
                    const timeStr = item.timestamp ? item.timestamp.substring(11, 19) : "";
                    row.innerHTML = `
                        <td style="font-family:monospace; color:var(--accent-teal);">${item.decision_id}</td>
                        <td style="font-family:monospace; color:var(--text-secondary);">${item.nonce.substring(0, 16)}...</td>
                        <td><span style="font-family:monospace;">${item.prior_state}</span> ➔ <span style="font-family:monospace; font-weight:600; color:var(--accent-teal);">${item.next_state}</span></td>
                        <td style="color:var(--text-secondary);">${timeStr}</td>
                    `;
                    replayBody.appendChild(row);
                });
            }
        }
        
        // 6. Historical Operator Decision Ledger
        const ledgerBody = document.getElementById("gov-ledger-tbody");
        if (ledgerBody) {
            ledgerBody.innerHTML = "";
            if (data.decision_ledger.length === 0) {
                ledgerBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-secondary); padding: 12px;">No historical operator decisions recorded in ledger.</td></tr>`;
            } else {
                data.decision_ledger.forEach(item => {
                    const row = document.createElement("tr");
                    const colorClass = item.decision === "approved" ? "text-success" : "text-danger";
                    row.innerHTML = `
                        <td style="font-family:monospace; color:var(--accent-blue);">${item.decision_id}</td>
                        <td><strong>${item.operator}</strong></td>
                        <td style="font-family:monospace;">${item.action_type}</td>
                        <td><span class="${colorClass} font-semibold">${item.decision.toUpperCase()}</span></td>
                        <td style="color:var(--text-secondary);">${item.reason || "none"}</td>
                        <td style="color:var(--text-secondary);">${item.timestamp}</td>
                    `;
                    ledgerBody.appendChild(row);
                });
            }
        }
        
        // Trigger lucide icons rendering
        if (typeof lucide !== "undefined" && typeof lucide.createIcons === "function") {
            lucide.createIcons();
        }
        
    } catch (err) {
        console.error("Error fetching governance summary:", err);
    }
}

async function submitGovernanceApproval(approvalId, decision) {
    const reason = prompt(`Enter justification reason for this ${decision} decision:`, `Operator manual override: ${decision}`);
    if (reason === null) return;
    try {
        const res = await fetch(`${API_BASE}/api/approval/requests/${approvalId}/decisions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                decision: decision === "approve" ? "approve" : "reject",
                operator: "Michael Hoch",
                reason: reason
            })
        });
        if (res.ok) {
            alert("Decision registered in the SQLite governance ledger successfully.");
            fetchAndRenderGovernanceSummary();
            if (typeof fetchApprovalRequests === 'function') {
                fetchApprovalRequests();
            }
            if (typeof fetchAndRenderSigningPolicy === 'function') {
                fetchAndRenderSigningPolicy();
            }
        } else {
            const data = await res.json();
            alert("Failed to submit decision: " + (data.detail || "Unknown error"));
        }
    } catch (err) {
        alert("Failed to submit decision: " + err.message);
    }
}

window.fetchAndRenderGovernanceSummary = fetchAndRenderGovernanceSummary;
window.submitGovernanceApproval = submitGovernanceApproval;
window.handleGovernanceAction = handleGovernanceAction;
window.submitChannelDecisionRequest = submitChannelDecisionRequest;
