// Initialize Lucide Icons
lucide.createIcons();

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
    timelineReplay: { nav: document.getElementById("nav-timeline-replay"), view: document.getElementById("view-replay") }
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
        // Mission Intel bootstrap — load brief + start feed polling
        setTimeout(() => {
            loadIntelBrief("dash-intel-brief-text", "mission-brief-ts");
            startMissionPolling();
        }, 1200);
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

function setupWebsocket() {
    if (wsFallbackToPolling) return;

    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws/metrics`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUI(data);
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

// State variables for topology paths
let currentPaths = {};

// Render active deployments as premium tactical cards
function populateTable(nodes) {
    deploymentsTbody.innerHTML = "";
    nodes.forEach(node => {
        const card = document.createElement("div");
        card.className = "asset-console-card";
        
        let statusClass = "status-idle";
        if (node.status === "Active") statusClass = "status-active";
        else if (node.status === "Underutilized") statusClass = "status-underutilized";

        let osIcon = "monitor";
        if (node.os.toLowerCase().includes("mac")) osIcon = "apple";
        else if (node.os.toLowerCase().includes("win")) osIcon = "terminal";
        else if (node.os.toLowerCase().includes("ios")) osIcon = "smartphone";
        else if (node.os.toLowerCase().includes("ipad")) osIcon = "tablet";
        else if (node.os.toLowerCase().includes("linux")) osIcon = "server";

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
        const isCoder = !node.os.toLowerCase().includes("ios") && !node.os.toLowerCase().includes("ipad");

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
        if (node.os.toLowerCase().includes("mac")) osIcon = "apple";
        else if (node.os.toLowerCase().includes("win")) osIcon = "terminal";
        else if (node.os.toLowerCase().includes("ios")) osIcon = "smartphone";
        else if (node.os.toLowerCase().includes("ipad")) osIcon = "tablet";
        else if (node.os.toLowerCase().includes("linux")) osIcon = "server";

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
                if (targetNode.os.toLowerCase().includes("ios") || targetNode.os.toLowerCase().includes("ipad")) {
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
            } else if (key === "assets" || key === "swarmControl") {
                renderAssetsView(currentNodes);
            } else if (key === "tasks" || key === "remediationSafety") {
                fetchAndRenderTasks();
                if (window.onRemediationTabActive) window.onRemediationTabActive();
            } else if (key === "settings") {
                renderSettingsNodesList(currentNodes);
            } else if (key === "audit" || key === "runtimeAudit") {
                fetchAndRenderAuditLogs();
            } else if (key === "replay" || key === "timelineReplay") {
                if (window.onReplayTabActive) window.onReplayTabActive();
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

        globeAngleY += 0.004; // Rotate speed

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

        requestAnimationFrame(drawGlobe);
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
    const safetyOk = await checkEndpoint("/api/v1/policy/status");
    updateIndicator("nav-remediation-safety", safetyOk ? "live" : "error");

    // 4. Runtime Audit
    const auditOk = await checkEndpoint("/api/v1/audit/runtime/execution");
    updateIndicator("nav-runtime-audit", auditOk ? "live" : "error");

    // 5. Error Budget
    updateIndicator("nav-error-budget", "planned");

    // 6. Release Provenance
    updateIndicator("nav-release-provenance", readinessOk ? "live" : "error");

    // 7. Swarm Control
    const statusOk = await checkEndpoint("/api/status");
    updateIndicator("nav-swarm-control", statusOk ? "live" : "error");

    // 8. Mission Intel
    const missionOk = await checkEndpoint("/api/mission/brief");
    updateIndicator("nav-mission-intel", missionOk ? "live" : "error");

    // 9. Timeline Replay
    const ledgerOk = await checkEndpoint("/api/ledger/blocks");
    updateIndicator("nav-timeline-replay", ledgerOk ? "live" : "error");
}

